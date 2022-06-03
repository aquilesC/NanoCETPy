import os
from ssl import ALERT_DESCRIPTION_ACCESS_DENIED
import time
from datetime import datetime
from multiprocessing import Event

from skimage import data, filters, io
import numpy as np
from scipy import optimize
from . import model_utils as ut

from experimentor.models.action import Action
from experimentor import Q_
from experimentor.models.devices.cameras.basler.basler import BaslerCamera as Camera
from experimentor.models.devices.cameras.exceptions import CameraTimeout
from experimentor.models.experiments import Experiment
from dispertech.models.electronics.arduino import ArduinoModel
from experimentor.models.decorators import make_async_thread
from recording.models.movie_saver import WaterfallSaver
from experimentor.core.signal import Signal



class MainSetup(Experiment):
    """ Setup for recording Fiber core
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
        self.waterfall_image = self.demo_image
        self.display_image = self.demo_image
        self.active = True
        self.now = None

    @Action
    def initialize(self):
        self.initialize_cameras()
        self.initialize_electronics()

    def initialize_cameras(self):
        """Assume a specific setup working with baslers and initialize both cameras"""
        self.logger.info('Initializing cameras')
        config_fiber = self.config['camera_fiber']
        self.camera_fiber = Camera(config_fiber['init'], initial_config=config_fiber['config'])
        config_mic = self.config['camera_microscope']
        self.camera_microscope = Camera(config_mic['init'], initial_config=config_mic['config'])
        for cam in (self.camera_fiber, self.camera_microscope):
            self.logger.info(f'Initializing {cam}')
            cam.initialize()
            self.logger.debug(f'Configuring {cam}')

    def initialize_electronics(self):
        """ Initializes the electronics associated witht he experiment (but not the cameras).

        TODO:: We should be mindful about what happens once the program starts and what happens once the device is
            switched on.
        """
        self.electronics = ArduinoModel(**self.config['electronics']['arduino'])
        self.logger.info('Initializing electronics arduino')
        self.electronics.initialize()
    
    def toggle_active(self):
        self.active = not self.active

    def focus_start(self):
        self.set_fiber_ROI()
        self.toggle_live(self.camera_microscope)
        self.update_camera(self.camera_microscope, self.config['microscope_focusing']['low'])
        self.electronics.top_led = 1

    def focus_stop(self):
        if self.camera_microscope.continuous_reads_running:
            self.toggle_live(self.camera_microscope)
        self.electronics.top_led = 0
    
    @make_async_thread
    def start_alignment(self):
        """ Wraps the whole alignment procedure from focussing to aligning.
        Run in an async thread as it calls other Actions
        TODO: change to single shot acquisition

        Args:
            None
        Returns:
            None
        """
        if True: # TESTING
            time.sleep(5)
            self.aligned = True
            self.toggle_live(self.camera_microscope)
            self.set_laser_power(99)
            self.update_camera(self.camera_microscope, self.config['microscope_focusing']['high'])
            return
        self.logger.info('TEST Starting Laser Alignment')
        self.active = True
        # Toggle live
        self.toggle_live(self.camera_fiber)
        # Set exposure and gain
        self.update_camera(self.camera_fiber, self.config['laser_focusing']['low'])
        # Turn on Laser
        self.electronics.fiber_led = 0
        self.set_laser_power(1)
        # Find focus function
        time.sleep(.5)
        self.find_focus()
        self.logger.info('TEST focus done')
        # Turn off laser
        self.set_laser_power(0)
        # Turn on fiber LED
        self.electronics.fiber_led = 1
        # Set exposure and gain
        self.update_camera(self.camera_fiber, self.config['laser_focusing']['high'])
        # Find center function
        time.sleep(5)
        fiber = ut.image_convolution(self.camera_fiber.temp_image, kernel=np.ones((3,3)))
        mask = ut.gaussian2d_array((int(fiber.shape[0]/2),int(fiber.shape[1]/2)),10000,fiber.shape)
        fibermask = fiber * mask
        fiber_center = np.argwhere(fibermask==np.max(fibermask))[0]
        self.logger.info(f'TEST fiber center is {fiber_center}')
        # Turn off LED
        self.electronics.fiber_led = 0
        # Set exposure and gain
        self.update_camera(self.camera_fiber, self.config['laser_focusing']['low'])
        # Turn on Laser
        self.set_laser_power(1)
        time.sleep(.5)
        # Coarse alignment function
        self.align_laser_coarse(fiber_center)
        time.sleep(.5)
        # Switch camera
        self.toggle_live(self.camera_fiber)
        self.toggle_live(self.camera_microscope)
        self.set_laser_power(99)
        self.update_camera(self.camera_microscope, self.config['microscope_focusing']['high'])
        time.sleep(.5)
        # Fine alignment function
        self.align_laser_fine()
        self.logger.info('TEST Alignment done')

    def find_focus(self):
        """ Finding the focus with turned on laser by minimizing area of laser reflection.
        Idea: Laser beam and thus reflection have gaussian intensity profile. The lower the spread the less pixel values are above a certain arbitrary percentile
        Procedure: Check number of pixels above percentile and compare to previous measurement. If increasing, change direction and reduce speed. Stop at a certain minimum speed.
        
        Args: 
            None
        Returns: 
            None
        """
        self.logger.info('TEST start finding focus')
        direction = 0
        speed = 50
        img = self.camera_fiber.temp_image
        self.processed_image = img
        val_new = np.sum(img > 0.8*np.max(img))
        while self.active:
            val_old = val_new
            self.logger.info(f'TEST moving with speed {speed} in direction {direction}')
            self.electronics.move_piezo(speed,direction,3)
            time.sleep(.5)
            img = self.camera_fiber.temp_image
            val_new = np.sum(img > 0.8*np.max(img))
            if val_old < val_new: 
                direction = (direction + 1) % 2
                speed -= 5
            if speed == 20: return

    def align_laser_coarse(self, fiber_center):
        """ Aligns the focussed laser beam to the previously detected center of the fiber.
        TODO: find suitable way to detect laser beam center

        Args:
            fiber_center: array or tuple of shape (2,)
        Returns:
            None
        """
        assert len(fiber_center) == 2
        axis = self.config['electronics']['horizontal_axis']
        for idx, c in enumerate(fiber_center):
            self.logger.info(f'TEST start aligning axis {axis} at index {idx}')
            direction = 0
            speed = 5
            img = self.camera_fiber.temp_image
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
                img = self.camera_fiber.temp_image
                img = img * mask
                img = 1*(img>0.8*np.max(img))
                lc = ut.centroid(img)
                val_new = lc[idx]-c
                self.logger.info(f'TEST last distances are {val_old}, {val_new} to centroid at {lc}')
                if np.sign(val_old) != np.sign(val_new): 
                    if speed == 1: break
                    speed = 1
            axis = self.config['electronics']['vertical_axis']

    def align_laser_fine(self):
        """ Maximises the fiber core scattering signal seen on the microscope cam by computing the median along axis 0.
        Idea: Median along axis 0 is highest for the position of fiber center even with bright dots from impurities in the image
        Procedure: Move until np.max(median)/np.min(median) gets smaller then change direction
        TODO: Consider just using mean of image

        Args:
            None
        Returns:
            None
        """
        axis = self.config['electronics']['horizontal_axis']
        for i in range(2):
            self.logger.info(f'TEST start optimizing axis {axis}')
            check = False
            direction = 0
            img = self.camera_microscope.temp_image
            median = np.median(img, axis=0)
            val_new = np.max(median)/np.min(median)
            while self.active:
                val_old = val_new
                self.electronics.move_piezo(1,direction,axis)
                time.sleep(.5)
                img = self.camera_microscope.temp_image
                median = np.median(img, axis=0)
                val_new = np.max(median)/np.min(median)
                if val_old > val_new:
                    direction = (direction + 1) % 2
                    if check: 
                        self.electronics.move_piezo(1,direction,axis)
                        break
                    check = True
            axis = self.config['electronics']['vertical_axis']

    @Action
    def set_fiber_ROI(self):
        width = 220
        cx, cy = 520,480
        new_roi = ((cy-width, 2*width), (cx-width, 2*width))
        self.camera_fiber.ROI = new_roi
        self.logger.info('ROI set up')

    @make_async_thread
    def find_ROI(self):
        """Assuming alignment, this function fits a gaussian to the microscope images cross section to compute an ROI
        """
        #self.update_camera(self.camera_microscope, self.config['microscope_focusing']['high'])
        #self.set_laser_power(99)
        #time.sleep(1)
        #self.snap_image(self.camera_microscope)
        #time.sleep(1)
        img = self.camera_microscope.temp_image
        self.toggle_live(self.camera_microscope)
        while self.camera_microscope.continuous_reads_running:
            time.sleep(.1)
        self.logger.info(f'TEST imgshape {img.shape}')
        measure = np.sum(img, axis=0)
        cx = np.argwhere(measure == np.max(measure))[0][0]
        measure = measure[cx-100:cx+100]
        measure = measure / np.max(measure)
        xvals = np.linspace(0,1,measure.shape[0]) - 0.5
        gaussian1d = lambda x, mean, var, A, bg: A * np.exp(-(x-mean)**2 / (2 *var)) + bg
        popt, pcov = optimize.curve_fit(
            gaussian1d, 
            xvals, 
            measure, 
            p0=[0, 0.1, np.max(measure)-np.min(measure), np.min(measure)],
            bounds=([-0.5,0,0,0],[0.5,1,1,1]))
        self.logger.info(f'TEST {popt}')
        cx += int(popt[0] * measure.shape[0])
        width = 2 * int(2 * np.sqrt(popt[1] * measure.shape[0]))  
        self.logger.info('optimized')  

        current_roi = self.camera_microscope.ROI
        new_roi = (current_roi[0], (cx-width, 2*width))
        self.camera_microscope.ROI = new_roi
        self.logger.info('ROI set up')

        self.toggle_live(self.camera_microscope)

    @make_async_thread
    def save_waterfall(self):
        """Assuming a set ROI, this function calculates a waterfall slice per image frame and sends it to a MovieSaver instance
        """
        self.start_saving_images()
        img = self.camera_microscope.temp_image
        self.waterfall_image = np.zeros((img.shape[0],1000)) #MAKE CONFIG PARAMETER
        while self.active:
            img = self.camera_microscope.temp_image
            new_slice = np.sum(img, axis=1)
            self.waterfall_image = np.roll(self.waterfall_image, -1, 1)
            self.waterfall_image[:,-1] = new_slice
            time.sleep(.1)
        self.stop_saving_images()
        
    def start_saving_images(self):
        if self.saving:
            self.logger.warning('Saving process still running: self.saving is true')
        if self.saving_process is not None and self.saving_process.is_alive():
            self.logger.warning('Saving process is alive, stop the saving process first')
            return

        self.saving = True
        base_filename = self.config['info']['filename_movie']
        file = self.get_filename(base_filename)
        self.saving_event.clear()
        self.saving_process = WaterfallSaver(
            file,
            self.config['saving']['max_memory'],
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
    def toggle_live(self, camera):
        self.logger.info(f'Toggle live on {camera}')
        if camera.continuous_reads_running:
            camera.stop_continuous_reads()
            camera.stop_free_run()
            self.logger.info('Continuous reads ended')
            self.display_camera = None
        else:
            camera.start_free_run()
            camera.continuous_reads()
            self.display_camera = camera
            self.logger.info('Continuous reads started')

    def update_camera(self, camera, new_config):
        """ Updates the properties of the camera.
        new_config should be dict with keys exposure_time and gain"""

        self.logger.info('Updating parameters of the camera')
        camera.config.update({
                'exposure': Q_(new_config['exposure_time']),
                'gain': float(new_config['gain']),
        })
        camera.config.apply_all()

    def set_laser_power(self, power: int):
        """ Sets the laser power, taking into account closing the shutter if the power is 0
        """
        self.logger.info(f'Setting laser power to {power}')
        power = int(power)

        self.electronics.scattering_laser = power
        self.config['laser']['power'] = power

    @Action
    def toggle_laser(self):
        if self.electronics.scattering_laser == 0:
            
            if self.display_camera == self.camera_fiber: 
                self.update_camera(self.camera_fiber, self.config['laser_focusing']['low'])
                self.electronics.scattering_laser = 1
            if self.display_camera == self.camera_microscope: 
                self.update_camera(self.camera_microscope, self.config['microscope_focusing']['high'])
                self.electronics.scattering_laser = 99
        else: 
            self.electronics.scattering_laser = 0
            self.electronics.fiber_led = 1
            self.update_camera(self.camera_fiber, self.config['laser_focusing']['high'])

    def get_latest_image(self):
        return self.camera_microscope.temp_image

    def get_waterfall_image(self):
        return self.waterfall_image

    def prepare_folder(self) -> str:
        """Creates the folder with the proper date, using the base directory given in the config file"""
        base_folder = self.config['info']['folder']
        today_folder = f'{datetime.today():%Y-%m-%d}'
        folder = os.path.join(base_folder, today_folder)
        if not os.path.isdir(folder):
            os.makedirs(folder)
        return folder

    def get_filename(self, base_filename: str) -> str:
        """Checks if the given filename exists in the given folder and increments a counter until the first non-used
        filename is available.

        :param base_filename: must have two placeholders {cartridge_number} and {i}
        :returns: full path to the file where to save the data
        """
        folder = self.prepare_folder()
        i = 0
        cartridge_number = self.config['info']['cartridge_number']
        while os.path.isfile(os.path.join(folder, base_filename.format(
                cartridge_number=cartridge_number,
                i=i))):
            i += 1

        return os.path.join(folder, base_filename.format(cartridge_number=cartridge_number, i=i))

    def finalize(self):
        if self.finalized:
           return
        self.logger.info('Finalizing calibration experiment')
        self.active = False
        
        if self.saving:
            self.logger.debug('Finalizing the saving images')
            self.stop_saving_images()
        self.saving_event.set()

        self.camera_microscope.finalize()
        self.set_laser_power(0)
        self.electronics.finalize()

        super(MainSetup, self).finalize()
        self.finalized = True