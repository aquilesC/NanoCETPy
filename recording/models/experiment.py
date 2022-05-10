import os
from ssl import ALERT_DESCRIPTION_ACCESS_DENIED
import time
from datetime import datetime

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




class RecordingSetup(Experiment):
    """ Setup for recording Fiber core
    """
    # What is Signal() for? 

    def __init__(self, filename=None):
        super(RecordingSetup, self).__init__(filename=filename)
        
        #self.camera_fiber = None
        self.camera_microscope = None
        self.electronics = None
        self.display_camera = None
        self.finalized = False
        

        self.demo_image = data.colorwheel()
        self.processed_image = self.demo_image
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
        self.snap_image(self.camera_microscope)
        img = self.camera_microscope.temp_image
        measure = np.sum(img, axis=0)
        cx = np.argwhere(measure = np.max(measure))[0][0]
        measure = measure[cx-100:cx+100]
        xvals = np.arange(0,measure.shape[0],1)
        gaussian1d = lambda x, mean, var, A, bg: A * np.exp(-(x-mean)**2 / (2 *var)) + bg
        popt, pcov = optimize.curve_fit(gaussian1d, xvals, measure, p0=[0, 50, np.max(measure)-np.min(measure), np.min(measure)])
        cx += int(popt[0])
        width = int(2 * np.sqrt(popt[1]))    

        current_roi = self.camera_microscope.ROI
        new_roi = (current_roi[0], (cx-width, 2*width))
        self.camera_microscope.ROI = new_roi

        self.toggle_live(self.camera_microscope)

    @make_async_thread
    def save_waterfall(self):
        """Assuming a set ROI, this function calculates a waterfall slice per image frame and sends it to a MovieSaver instance
        """
        while self.active:
            img = self.camera_microscope.temp_image
        self.camera_microscope.new_image.emit('stop')
        
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
        return self.processed_image

    def finalize(self):
        if self.finalized:
           return
        self.logger.info('Finalizing calibration experiment')
        
        self.camera_microscope.finalize()
        self.set_laser_power(0)
        self.electronics.finalize()

        super(RecordingSetup, self).finalize()
        self.finalized = True