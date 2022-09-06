"""
    Experiment module for the entire usage sequence of the NanoCET 
"""
import os
from ssl import ALERT_DESCRIPTION_ACCESS_DENIED
import time
from datetime import datetime
from multiprocessing import Event
from serial import SerialException
import yaml

from skimage import data, filters, io
import numpy as np
from scipy import optimize
from . import model_utils as ut

from experimentor.models.action import Action
from experimentor import Q_
#from experimentor.models.devices.cameras.basler.basler import BaslerCamera as Camera
from .basler import BaslerNanoCET as Camera
from experimentor.models.devices.cameras.exceptions import CameraTimeout
from experimentor.models.experiments import Experiment
#from dispertech.models.electronics.arduino import ArduinoModel
from .arduino import ArduinoNanoCET
from experimentor.models.decorators import make_async_thread
from .movie_saver import WaterfallSaver
from experimentor.core.signal import Signal



class MainSetup(Experiment):
    """ This is a Experiment subclass to control the NanoCET in a sequential experiment consisting of focusing, alignment, and recording a waterfall

    :param str filename: yml file containing the configuration settings for the experiment

    >>> # First the experiment is instantiated with the corresponding filename
    >>> experiment = MainSetup('config.yml')
    >>> # Or 
    >>> experiment = MainSetup()
    >>> experiment.load_configuration('config.yml', yaml.UnsafeLoader)

    >>> # Then the experiment is initialized to load the connected device classes
    >>> experiment.initialize()
    """
    def __init__(self, filename=None):
        super(MainSetup, self).__init__(filename=filename)
        
        self.camera_fiber = None
        self.camera_microscope = None
        self.electronics = None
        self.display_camera = self.camera_microscope
        self.finalized = False
        self.saving_event = Event()
        self.saving = False
        self.saving_process = None
        self.aligned = False
        
        self.demo_image = data.colorwheel()
        self.waterfall_image = np.array([[0,2**12-1],[0,2**8-1]])
        self.display_image = self.demo_image
        self.active = True
        self.now = None

    @Action
    def initialize(self):
        """ Initializes the cameras and Arduino objects. 
        Runs in a loop until every device is connected and initialized.

        :return: None
        """
        #self.initialize_cameras()
        #self.initialize_electronics()

        #Instantiate Camera and Arduino objects
        self.logger.info('Instantiating Cameras and Arduino')
        config_fiber = self.config['camera_fiber']
        self.camera_fiber = Camera(config_fiber['init'], initial_config=config_fiber['config'])
        config_mic = self.config['camera_microscope']
        self.camera_microscope = Camera(config_mic['init'], initial_config=config_mic['config'])
        self.electronics = ArduinoNanoCET(**self.config['electronics']['arduino'])
        try:
            devices_loading_timeout = Q_(self.config['defaults']['devices_loading_timeout']).m_as('s')
        except:
            devices_loading_timeout = 30
            self.logger.info(f'default/devices_loading_timeout parameter not found in config: using {devices_loading_timeout}s')

        #Loop over instances until all are initialized
        t0 = time.time()
        loading_timed_out = False
        while self.active and not loading_timed_out:
            #self.logger.info('TEST init loop')
            initialized = [self.camera_fiber.initialized, self.camera_microscope.initialized, self.electronics.initialized]
            if all(initialized): return
            if not initialized[0]: 
                try:
                    self.camera_fiber.initialize()
                except:
                    self.logger.info('Init Exception camera_fiber:', exc_info=True)
            if not initialized[1]: 
                try:
                    self.camera_microscope.initialize()
                except:
                    self.logger.info('Init Exception camera_microscope:', exc_info=True)
            if not initialized[2]:
                try:
                    if not self.electronics.initializing: self.electronics.initialize()
                except:
                    self.electronics.initializing = False 
                    self.logger.info('Init Exception electronics:', exc_info=True)
            loading_timed_out = time.time() > t0 + devices_loading_timeout
        if loading_timed_out:
            self.logger.error('Loading devices timed out')
            self.parent.init_failed.emit()
            return
        self.logger.info('TEST init loop exit')

    def focus_start(self):
        self.set_live(self.camera_microscope, False)
        self.set_live(self.camera_fiber, False)
        while self.camera_microscope.free_run_running: time.sleep(.1)
        time.sleep(.1)
        self.camera_fiber.clear_ROI()
        self.camera_microscope.clear_ROI()
        self.set_live(self.camera_microscope, True)
        self.update_camera(self.camera_microscope, self.config['defaults']['microscope_focusing']['low'])
        self.electronics.top_led = 1

    def focus_stop(self):
        self.set_live(self.camera_microscope, False)
        self.electronics.top_led = 0
    
    @make_async_thread
    def start_alignment(self):
        """ Wraps the whole alignment procedure from focussing to aligning.
        Run in an async thread as it calls other Actions
        
        :return: None
        """
        self.logger.info('TEST Starting Laser Alignment')
        self.active = True
        self.now = datetime.now()
        self.saving_images = True

        if False: # TESTING
            time.sleep(5)
            self.aligned = True
            self.toggle_live(self.camera_microscope)
            self.set_laser_power(99)
            self.update_camera(self.camera_microscope, self.config['defaults']['microscope_focusing']['high'])
            return

        # Set camera mode
        self.set_live(self.camera_fiber, False)
        self.set_live(self.camera_microscope, False)
        self.camera_fiber.acquisition_mode = self.camera_fiber.MODE_SINGLE_SHOT
        self.camera_microscope.acquisition_mode = self.camera_microscope.MODE_SINGLE_SHOT
        # Set exposure and gain
        self.update_camera(self.camera_fiber, self.config['defaults']['laser_focusing']['low'])
        # Turn on Laser
        self.electronics.fiber_led = 0
        self.electronics.top_led = 0
        self.electronics.side_led = 0
        self.set_laser_power(3)
        # Find focus function
        self.find_focus()
        self.logger.info('TEST focus done')
        # Turn off laser
        self.set_laser_power(0)
        # Turn on fiber LED
        self.electronics.fiber_led = 1
        # Set exposure and gain
        self.update_camera(self.camera_fiber, self.config['defaults']['laser_focusing']['high'])

        # Find center
        self.camera_fiber.trigger_camera()
        img = self.camera_fiber.read_camera()[-1]
        
        #fiber = ut.image_convolution(img, kernel = np.ones((3,3)))
        #mask = ut.gaussian2d_array((int(fiber.shape[0]/2),int(fiber.shape[1]/2)),20000,fiber.shape)
        #fibermask = fiber * mask

        ksize = 15
        kernel = ut.circle2d_array((int(ksize/2), int(ksize/2)), 5, (ksize,ksize)) * 1.01 
        kernel = (kernel - np.mean(kernel)) / np.std(kernel)
        fiber = (img - np.mean(img)) / np.std(img)
        fibermask = ut.image_convolution(fiber, kernel=kernel)

        fiber_center = np.argwhere(fibermask==np.max(fibermask))[0]
        if self.saving_images: io.imsave('recorded/fiber'+self.now.strftime('_%M_%S')+'.tiff', img)
        self.logger.info(f'TEST fiber center is {fiber_center}')
        # Turn off LED
        self.electronics.fiber_led = 0
        # Set exposure and gain
        self.update_camera(self.camera_fiber, self.config['defaults']['laser_focusing']['low'])

        # Turn on Laser
        self.set_laser_power(3)
        time.sleep(.1)
        # Find alignment function
        self.align_laser_coarse(fiber_center)
        time.sleep(.1)
        self.set_laser_power(99)
        self.update_camera(self.camera_microscope, self.config['defaults']['microscope_focusing']['high'])
        time.sleep(1)
        self.align_laser_fine()
        self.set_live(self.camera_microscope, True)
        self.aligned = True

        self.logger.info('TEST Alignment done')

    def find_focus(self):
        """ Finding the focus with turned on laser by minimizing area of laser reflection.
        Idea: Laser beam and thus reflection have gaussian intensity profile. The lower the spread the less pixel values are above a certain arbitrary percentile
        Procedure: Check number of pixels above percentile and compare to previous measurement. If increasing, change direction and reduce speed. Stop at a certain minimum speed.
        
        :return: None
        """
        self.logger.info('TEST start finding focus')
        direction = 0
        speed = 50
        self.camera_fiber.trigger_camera()
        img = self.camera_fiber.read_camera()[-1]        
        val_new = np.sum(img > 0.8*np.max(img))
        while self.active:
            val_old = val_new
            self.logger.info(f'TEST moving with speed {speed} in direction {direction}')
            self.electronics.move_piezo(speed,direction,self.config['electronics']['focus_axis'])
            time.sleep(.1)
            self.camera_fiber.trigger_camera()
            img = self.camera_fiber.read_camera()[-1]
            val_new = np.sum(img > 0.8*np.max(img))
            if val_old < val_new: 
                direction = (direction + 1) % 2
                speed -= 5
            if speed == 20: return

    def align_laser_coarse(self, fiber_center):
        """ Aligns the focussed laser beam to the previously detected center of the fiber.
        
        :param fiber_center: coordinates of the center of the fiber 
        :type fiber_center: array or tuple of shape (2,)
        :returns: None
        
        .. todo:: consider more suitable ways to accurately detect laser beam center
        """
        assert len(fiber_center) == 2
        axis = self.config['electronics']['horizontal_axis']
        for idx, c in enumerate(fiber_center):
            self.logger.info(f'TEST start aligning axis {axis} at index {idx}')
            direction = 0
            speed = 5
            self.camera_fiber.trigger_camera()
            img = self.camera_fiber.read_camera()[-1]
            mask = ut.gaussian2d_array(fiber_center,19000,img.shape)
            mask = mask > 0.66*np.max(mask)
            img = img * mask
            img = 1*(img>0.8*np.max(img))
            lc = ut.centroid(img)
            val_new = lc[idx]-c
            while self.active:
                val_old = val_new
                if val_new > 0: direction = 0
                elif val_new < 0: direction = 1
                self.logger.info(f'TEST moving with speed {speed} in direction {direction}')
                self.electronics.move_piezo(speed,direction,axis)
                time.sleep(.1)
                self.camera_fiber.trigger_camera()
                img = self.camera_fiber.read_camera()[-1]
                img = img * mask
                img = 1*(img>0.8*np.max(img))
                lc = ut.centroid(img)
                val_new = lc[idx]-c
                self.logger.info(f'TEST last distances are {val_old}, {val_new} to centroid at {lc}')
                if np.sign(val_old) != np.sign(val_new): 
                    if speed == 1: break
                    speed = 1
            axis = self.config['electronics']['vertical_axis']
        
        if self.saving_images: io.imsave('recorded/laser'+self.now.strftime('_%M_%S')+'.tiff', img)

    def align_laser_fine(self):
        """ Maximises the fiber core scattering signal seen on the microscope cam by computing the median along axis 0.
        Idea: Median along axis 0 is highest for the position of fiber center even with bright dots from impurities in the image
        Procedure: Move until np.max(median)/np.min(median) gets smaller then change direction
        
        :return: None
            
        .. todo:: Test how robustly this detects the fiber core and not anything else
        """
        axis = self.config['electronics']['horizontal_axis']
        for i in range(2):
            self.logger.info(f'TEST start optimizing axis {axis}')
            check = False
            direction = 0
            self.camera_microscope.trigger_camera()
            img = self.camera_microscope.read_camera()[-1]
            median = np.median(img, axis=0)
            val_new = np.max(median)/np.min(median)
            axis = self.config['electronics']['vertical_axis']
            while self.active:
                val_old = val_new
                self.electronics.move_piezo(1,direction,axis)
                time.sleep(.1)
                self.camera_microscope.trigger_camera()
                img = self.camera_microscope.read_camera()[-1]
                median = np.median(img, axis=0)
                val_new = np.max(median)/np.min(median)
                if val_old > val_new:
                    direction = (direction + 1) % 2
                    if check: 
                        self.electronics.move_piezo(1,direction,axis)
                        break
                    check = True
            axis = self.config['electronics']['vertical_axis']
        
        if self.saving_images: io.imsave('recorded/line'+self.now.strftime('_%M_%S')+'.tiff', img)

    @make_async_thread
    def find_ROI(self, crop=False):
        """Assuming alignment, this function fits a gaussian to the microscope images cross section to compute an ROI
        """
        self.update_camera(self.camera_microscope, self.config['defaults']['microscope_focusing']['high'])
        self.set_laser_power(99)
        img = self.camera_microscope.temp_image
        self.set_live(self.camera_microscope, False)
        while self.camera_microscope.continuous_reads_running:
            time.sleep(.1)
        self.logger.info(f'TEST imgshape {img.shape}')
        measure = np.sum(img, axis=0)
        argmax_measure = np.argwhere(measure == np.max(measure))[0][0]
        if crop: 
            cx = argmax_measure
            measure = measure[cx-100:cx+101]
            argmax_measure = 101
        else: cx = int(measure.shape[0] / 2)
        measure = measure / np.max(measure)
        xvals = np.linspace(0,1,measure.shape[0]) - 0.5
        gaussian1d = lambda x, mean, var, A, bg: A * np.exp(-(x-mean)**2 / (2 *var)) + bg
        popt, pcov = optimize.curve_fit(
            gaussian1d, 
            xvals, 
            measure, 
            p0=[argmax_measure/measure.shape[0] - 0.5, 0.1, np.max(measure)-np.min(measure), np.min(measure)],
            bounds=([-0.5,0,0,0],[0.5,1,1,1]))
        self.logger.info(f'TEST {popt}')
        cx += int(popt[0] * measure.shape[0])
        width = 2 * int(2 * np.sqrt(popt[1] * measure.shape[0]))  
        self.logger.info(f'ROI optimized with width {width}')
        width = self.config['defaults']['core_width']  

        current_roi = self.camera_microscope.ROI
        new_roi = (current_roi[0], (current_roi[1][0]+cx-width, 2*width))
        self.camera_microscope.ROI = new_roi
        self.logger.info(f'ROI set up with width {width}')

        self.set_live(self.camera_microscope, True)

    @make_async_thread
    def save_waterfall(self):
        """Assuming a set ROI, this function calculates a waterfall slice per image frame and sends it to a MovieSaver instance
        """
        self.start_saving_images()
        img = self.camera_microscope.temp_image
        self.waterfall_image = np.zeros((img.shape[0],self.config['GUI']['length_waterfall'])) 
        refresh_time_s = self.config['GUI']['refresh_time'] / 1000
        while self.active:
            img = self.camera_microscope.temp_image
            new_slice = np.sum(img, axis=1)
            self.waterfall_image = np.roll(self.waterfall_image, -1, 1)
            self.waterfall_image[:,-1] = new_slice
            time.sleep(refresh_time_s - time.time() % refresh_time_s)
        self.stop_saving_images()
        
    def start_saving_images(self):
        if self.saving:
            self.logger.warning('Saving process still running: self.saving is true')
        if self.saving_process is not None and self.saving_process.is_alive():
            self.logger.warning('Saving process is alive, stop the saving process first')
            return

        self.saving = True
        base_filename = self.config['info']['files']['filename']
        file = self.get_filename(base_filename)
        self.saving_event.clear()
        self.saving_process = WaterfallSaver(
            file,
            self.config['info']['files']['max_memory'],
            self.camera_microscope.frame_rate,
            self.saving_event,
            self.camera_microscope.new_image.url,
            topic='new_image',
            metadata=self.camera_microscope.config.all(),
        )

    def stop_saving_images(self):
        self.camera_microscope.new_image.emit('stop')
        # self.emit('new_image', 'stop')

        # self.saving_event.set()
        time.sleep(.05)

        if self.saving_process is not None and self.saving_process.is_alive():
            self.logger.warning('Saving process still alive')
            time.sleep(.1)
        self.saving = False

    @Action
    def snap_image(self, camera):
        self.logger.info(f'Trying to snap image on {camera}')
        if camera.continuous_reads_running: 
            self.logger.warning('Continuous reads still running')
            return
        camera.acquisition_mode = camera.MODE_SINGLE_SHOT
        camera.trigger_camera()
        camera.read_camera()
        self.display_camera = camera
        self.logger.info('Snap Image complete')

    @Action    
    def set_live(self, camera, live):
        logstring = {True: "Turn on", False: "Turn off"}
        self.logger.info(f'{logstring[live]} live feed on {camera}')
        if camera.continuous_reads_running:
            if live: return
            camera.stop_continuous_reads()
            camera.stop_free_run()
            self.logger.info('Continuous reads ended')
            self.display_camera = None
        else:
            if not live: return
            camera.start_free_run()
            camera.continuous_reads()
            self.display_camera = camera
            self.logger.info('Continuous reads started')

    def update_camera(self, camera, new_config):
        """ Updates the properties of the camera.
        new_config should be dict with keys exposure_time and gain
        """
        self.logger.info('Updating parameters of the camera')
        camera.config.update({
                'exposure': Q_(new_config['exposure']),
                'gain': float(new_config['gain']),
        })
        camera.config.apply_all()

    def set_laser_power(self, power: int):
        """ Sets the laser power, taking into account closing the shutter if the power is 0
        """
        self.logger.info(f'Setting laser power to {power}')
        power = int(power)

        self.electronics.scattering_laser = power
        self.config['electronics']['laser']['power'] = power

    def get_latest_image(self):
        return self.camera_microscope.temp_image

    def get_waterfall_image(self):
        return self.waterfall_image

    def prepare_folder(self) -> str:
        """Creates the folder with the proper date, using the base directory given in the config file"""
        base_folder = self.config['info']['files']['folder']
        # To allow the use of environmental variables like %HOMEPATH%
        for key, val in os.environ:
            base_folder = base_folder.replace('%'+key+'%', val)
        today_folder = f'{datetime.today():%Y-%m-%d}'
        folder = os.path.join(base_folder, today_folder)
        if not os.path.isdir(folder):
            os.makedirs(folder)
        return folder

    def get_filename(self, base_filename: str) -> str:
        """Checks if the given filename exists in the given folder and increments a counter until the first non-used
        filename is available.

        :param base_filename: must have two placeholders {description} and {i}
        :returns: full path to the file where to save the data
        """
        folder = self.prepare_folder()
        i = 0
        description = self.config['info']['files']['description']
        while os.path.isfile(os.path.join(folder, base_filename.format(
                description=description,
                i=i))):
            i += 1

        return os.path.join(folder, base_filename.format(description=description, i=i))

    def finalize(self):
        if self.finalized:
           return
        self.logger.info('Finalizing calibration experiment')
        self.active = False
        
        if self.saving:
            self.logger.debug('Finalizing the saving images')
            self.stop_saving_images()
        self.saving_event.set()

        with open('config_user.yml', 'w') as f:
            yaml.dump(self.config, f, default_flow_style=False)

        if self.camera_microscope:
            self.camera_microscope.finalize()
        if self.electronics:
            self.set_laser_power(0)
            self.electronics.finalize()

        super(MainSetup, self).finalize()
        self.finalized = True