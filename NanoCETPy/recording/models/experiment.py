import os
import time
from datetime import datetime
from multiprocessing import Event

import numpy as np
from scipy import optimize
from skimage import data

from NanoCETPy.dispertech.models.arduino import ArduinoModel
from experimentor import Q_
from experimentor.models.action import Action
from experimentor.models.decorators import make_async_thread
from experimentor.models.devices.cameras.basler.basler import BaslerCamera as Camera
from experimentor.models.experiments import Experiment
from NanoCETPy.recording.models.movie_saver import WaterfallSaver


# from . import model_utils as ut


class RecordingSetup(Experiment):
    """ Setup for recording Fiber core
    """
    def __init__(self, filename=None):
        super(RecordingSetup, self).__init__(filename=filename)
        
        #self.camera_fiber = None
        self.camera_microscope = None
        self.electronics = None
        self.display_camera = None
        self.finalized = False
        self.saving_event = Event()
        self.saving = False
        self.saving_process = None
        

        self.demo_image = data.colorwheel()
        self.waterfall_image = self.demo_image
        self.display_image = self.demo_image
        self.active = True
        self.now = None

    @Action
    def initialize(self):
        self.initialize_cameras()
        self.initialize_electronics()
        #self.logger.info('Starting free runs and continuous reads')
        #time.sleep(1)
        #self.camera.start_free_run()
        #self.camera.continuous_reads()

    def initialize_cameras(self):
        """Assume a specific setup working with baslers and initialize both cameras"""
        self.logger.info('Initializing cameras')
        config_mic = self.config['camera_microscope']
        self.camera_microscope = Camera(config_mic['init'], initial_config=config_mic['config'])
        self.logger.info(f'Initializing {self.camera_microscope}')
        self.camera_microscope.initialize()
        self.logger.debug(f'Configuring {self.camera_microscope}')

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

    @make_async_thread
    def find_ROI(self):
        """Assuming alignment, this function fits a gaussian to the microscope images cross section to compute an ROI
        """
        self.update_camera(self.camera_microscope, self.config['microscope_focusing']['high'])
        self.set_laser_power(99)
        time.sleep(1)
        self.snap_image(self.camera_microscope)
        time.sleep(1)
        img = self.camera_microscope.temp_image
        measure = np.sum(img, axis=0)
        cx = np.argwhere(measure == np.max(measure))[0][0]
        measure = measure[cx-100:cx+100]
        xvals = np.arange(0,measure.shape[0],1)
        gaussian1d = lambda x, mean, var, A, bg: A * np.exp(-(x-mean)**2 / (2 *var)) + bg
        popt, pcov = optimize.curve_fit(gaussian1d, xvals, measure, p0=[0, 50, np.max(measure)-np.min(measure), np.min(measure)])
        cx += int(popt[0])
        width = 2 * int(2 * np.sqrt(popt[1]))    

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
        if self.display_camera is not None: 
            self.display_image = self.display_camera.temp_image
        else: self.display_image = self.demo_image
        return self.display_image

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

        super(RecordingSetup, self).finalize()
        self.finalized = True