import os
from ssl import ALERT_DESCRIPTION_ACCESS_DENIED
import time

from skimage import data, filters
import numpy as np
from . import model_utils as ut

from experimentor.models.action import Action
from experimentor import Q_
from experimentor.models.devices.cameras.basler.basler import BaslerCamera as Camera
from experimentor.models.devices.cameras.exceptions import CameraTimeout
from experimentor.models.experiments import Experiment
from dispertech.models.electronics.arduino import ArduinoModel
from experimentor.models.decorators import make_async_thread




class AlignmentSetup(Experiment):
    # What is Signal() for? 

    def __init__(self, filename=None):
        super(AlignmentSetup, self).__init__(filename=filename)
        
        self.camera_fiber = None
        self.electronics = None
        self.finalized = False
        self.display_camera = False

        self.demo_image = data.colorwheel()
        self.processed_image = self.demo_image
        self.display_image = self.demo_image
        #self.display_image = self.demo_image

    @Action
    def initialize(self):
        self.initialize_cameras()
        self.initialize_electronics()
        #self.logger.info('Starting free runs and continuous reads')
        #time.sleep(1)
        #self.camera.start_free_run()
        #self.camera.continuous_reads()

    def initialize_cameras(self):
        self.logger.info('Initializing cameras')
        config_fiber = self.config['camera_fiber']
        self.camera_fiber = Camera(config_fiber['init'], initial_config=config_fiber['config'])
        self.logger.info(f'Initializing {self.camera_fiber}')
        self.camera_fiber.initialize()
        self.logger.debug(f'Configuring {self.camera_fiber}')

    def initialize_electronics(self):
        """ Initializes the electronics associated witht he experiment (but not the cameras).

        TODO:: We should be mindful about what happens once the program starts and what happens once the device is
            switched on.
        """

        self.electronics = ArduinoModel(**self.config['electronics']['arduino'])
        self.logger.info('Initializing electronics arduino')
        self.electronics.initialize()
    
    @make_async_thread
    def start_alignment(self):
        self.logger.info('TEST Starting Laser Alignment')

        # For testing purposes
        self.electronics.fiber_led = 1
        for i in range(4):
            self.electronics.move_piezo(50,1,3) 
            time.sleep(.5)
        self.update_camera(self.camera_fiber, self.config['laser_focusing']['high'])
        # Toggle live
        self.toggle_live(self.camera_fiber)
        # Set exposure and gain
        time.sleep(5)
        self.update_camera(self.camera_fiber, self.config['laser_focusing']['low'])
        # Turn on Laser
        self.electronics.fiber_led = 0
        self.set_laser_power(1)
        # Find focus function
            # WHILE not focus:
                # Move piezo (how?) 
                # check focus of laserf
        time.sleep(.5)
        self.find_focus()
        self.logger.info('TEST focus done')
        # Turn off laser
        self.set_laser_power(0)
        # Turn on fiber LED
        self.electronics.fiber_led = 1
        # Set exposure and gain
        self.update_camera(self.camera_fiber, self.config['laser_focusing']['high'])
        #self.toggle_live(self.camera_fiber)
        # Find center function
            # find maximum
        time.sleep(5)
        fiber = filters.gaussian(self.camera_fiber.temp_image, 4, mode='constant')
        fiber_center = np.argwhere(fiber==np.max(fiber))[0]
        #fiber_center = [454, 174] # for testing
        self.logger.info(f'TEST fiber center is {fiber_center}')
        self.processed_image = np.zeros((fiber.shape[0],fiber.shape[1],3))
        self.processed_image[:,:,1] = ut.to_uint8(fiber)
        self.processed_image[:,:,0]= ut.to_uint8(ut.gaussian2d_array(fiber_center,40,fiber.shape))
        time.sleep(10)
        # Turn off LED
        self.electronics.fiber_led = 0
        # Set exposure and gain
        self.update_camera(self.camera_fiber, self.config['laser_focusing']['low'])
        # Turn on Laser
        self.set_laser_power(1)
        # Find alignment function
            # WHILE not aligned:
                # find center to center distance 
                # move mirror (PID?)
        self.align_laser(fiber_center)

        self.logger.info('TEST Alignment done')

    def find_focus(self):
        self.logger.info('TEST start finding focus')
        direction = 0
        speed = 50
        self.logger.info('TEST 1')
        img = self.camera_fiber.temp_image
        self.logger.info(f'TEST 2, {np.sum(img)}')
        val_new = np.sum(img > 0.8*np.max(img))
        while True:
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
    
    def align_laser(self, fiber_center):
        assert len(fiber_center) == 2
        axis = self.config['electronics']['vertical_axis']
        for idx, c in enumerate(fiber_center):
            self.logger.info(f'TEST start aligning axis {axis}')
            direction = 0
            speed = 1
            img = self.camera_fiber.temp_image
            mask = ut.gaussian2d_array(fiber_center,19000,img.shape)
            mask = mask > 0.66*np.max(mask)
            img = img * mask
            img = 1*(img>0.8*np.max(img))
            self.processed_image[:,:,1] = ut.to_uint8((1*mask))
            lc = ut.centroid(img)
            self.processed_image[:,:,2] = ut.to_uint8(ut.gaussian2d_array(lc,200,img.shape))
            val_new = lc[idx]-c
            while True:
                val_old = val_new
                if val_new > 0: direction = 0
                elif val_new < 0: direction = 1
                self.logger.info(f'TEST moving with speed {speed} in direction {direction}')
                self.electronics.move_piezo(speed,direction,axis)
                time.sleep(1)
                img = self.camera_fiber.temp_image
                img = img * mask
                img = 1*(img>0.8*np.max(img))
                lc = ut.centroid(img)
                self.processed_image[:,:,2] = ut.to_uint8(ut.gaussian2d_array(lc,200,img.shape))
                val_new = lc[idx]-c
                self.logger.info(f'TEST last distances are {val_old}, {val_new}')
                if np.sign(val_old) != np.sign(val_new): break
            axis = self.config['electronics']['horizontal_axis']

    @Action
    def snap_image(self, camera):
        self.logger.info(f'Trying to snap image on {camera}')
        if camera.continuous_reads_running: 
            self.logger.warning('Continuous reads still running')
            return
        camera.acquisition_mode = camera.MODE_SINGLE_SHOT
        camera.trigger_camera()
        camera.read_camera()
        self.display_camera = True
        self.logger.info('Snap Image complete')

    @Action    
    def toggle_live(self, camera):
        self.logger.info(f'Toggle live on {camera}')
        if camera.continuous_reads_running:
            camera.stop_continuous_reads()
            camera.stop_free_run()
            self.logger.info('Continuous reads ended')
            self.display_camera = False
        else:
            camera.start_free_run()
            camera.continuous_reads()
            self.display_camera = True
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

    def get_latest_image(self):
        if self.display_camera: 
            self.display_image = self.camera_fiber.temp_image
        else: self.display_image = self.demo_image
        return self.display_image

    def get_processed_image(self):
        return self.processed_image

    @Action
    def test_changes(self):
        """Changes camera settings every second an calls a processing function
        """

        self.logger.info('TEST Test Changes')
        for i in range(11):
            if i%2 == 0: update_settings = self.config['laser_focusing']['low']
            else: update_settings = self.config['laser_focusing']['high']      
            self.camera_fiber.config.update({
                'exposure': Q_(update_settings['exposure_time']),
                'gain': float(update_settings['gain']),
            })
            self.camera_fiber.config.apply_all()
            self.processing_test(sigma=i)
            time.sleep(1)
    
    def processing_test(self, sigma=1):
        img = self.display_image
        if img is None: self.logger.info('TEST img is None')
        self.processed_image = filters.gaussian(img, sigma=5*sigma, preserve_range=True)

    def finalize(self):
        if self.finalized:
           return
        self.logger.info('Finalizing calibration experiment')
        if self.camera_fiber is not None:
            self.camera_fiber.finalize()

        super(AlignmentSetup, self).finalize()
        self.finalized = True


class CamSetup(Experiment):
    # What is Signal() for? 

    def __init__(self, filename=None):
        super(CamSetup, self).__init__(filename=filename)
        
        self.camera_fiber = None
        self.finalized = False
        self.display_camera = False

        self.demo_image = data.colorwheel()
        #self.display_image = self.demo_image

    @Action
    def initialize(self):
        self.initialize_cameras()
        self.logger.info('Starting free runs and continuous reads')
        #time.sleep(1)
        #self.camera.start_free_run()
        #self.camera.continuous_reads()

    def initialize_cameras(self):
        self.logger.info('Initializing cameras')
        config_fiber = self.config['camera']
        self.camera_fiber = Camera(config_fiber['init'], initial_config=config_fiber['config'])
        self.logger.info(f'Initializing {self.camera_fiber}')
        self.camera_fiber.initialize()
        self.logger.debug(f'Configuring {self.camera_fiber}')
        
    @Action
    def snap_image(self):
        self.logger.info('Trying to snap image')
        if self.camera_fiber.continuous_reads_running: 
            self.logger.warning('Continuous reads still running')
            return
        if self.display_camera: 
            self.display_camera = False
            return
        self.camera_fiber.acquisition_mode = self.camera_fiber.MODE_SINGLE_SHOT
        self.camera_fiber.trigger_camera()
        self.camera_fiber.read_camera()
        self.display_camera = True
        self.logger.info('Snap Image complete')
        
    @Action
    def toggle_live(self):
        self.logger.info('Toggle live')
        if self.camera_fiber.continuous_reads_running:
            self.camera_fiber.stop_continuous_reads()
            self.camera_fiber.stop_free_run()
            self.logger.info('Continuous reads ended')
            self.display_camera = False
        else:
            self.camera_fiber.start_free_run()
            self.camera_fiber.continuous_reads()
            self.display_camera = True
            self.logger.info('Continuous reads started')

    def get_latest_image(self):
        if self.display_camera: return self.camera_fiber.temp_image
        else: return self.demo_image
    
    def finalize(self):
        if self.finalized:
           return
        self.logger.info('Finalizing calibration experiment')
        if self.camera_fiber is not None:
            self.camera_fiber.finalize()

        super(CamSetup, self).finalize()
        self.finalized = True


