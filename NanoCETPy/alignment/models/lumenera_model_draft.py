"""
    This is a camera model for a Teledyne Lumenera USB camera using the experimentor BaseCamera model

    It is using a python wrapper (unofficial, from Lumenera) for the Lucam API dll.
    This wrapper consists of :py:module:`..controller.api` :py:module:`..controller.camera` 
    with the :py:class:`..controller.camera.Camera` class containing the high level pythonic functionality.
    
    API reference manual link: `https://www.lumenera.com/lucam-software.html`
    .. codeauthor:: Jakob Schröder
"""

import inspect
from multiprocessing import Lock

import numpy as np

from experimentor import Q_
from experimentor.core.signal import Signal
from experimentor.lib.log import get_logger
from experimentor.models import Feature
from experimentor.models.action import Action
from experimentor.models.decorators import make_async_thread
from experimentor.models.devices.cameras.base_camera import BaseCamera
from experimentor.models.devices.cameras.exceptions import CameraNotFound
from ..controller.lucamapi.camera import *


class LumeneraCamera(BaseCamera):
    _acquisition_mode = BaseCamera.MODE_SINGLE_SHOT
    new_image = Signal()
    _lumenera_lock = Lock()

    def __init__(self, camera, initial_config=None):
        super().__init__(camera, initial_config=initial_config)
        self.logger = get_logger(__name__)
        self._camera = None
        self.snapshot_settings = None
        self.current_dtype = None
        self.free_run_running = False
        self.keep_reading = False
        self.continuous_reads_running = False
        self.finalized = False

    def __str__(self):
        return f'Lumenera {self.camera}'

    @Action
    def initialize(self):
        self.logger.info('lumenera init entry')
        api = Api()
        
        cameras = api.EnumCameras()
        if len(cameras) < 1: raise CameraNotFound('No cameras found')
        
        for i, camera in enumerate(cameras):
            if self.camera == camera.SerialNumber():
                handle = api.CameraOpen(i+1)
                self._camera = Camera(api, handle)
        
        if self._camera is None:
            msg = f'Lumenera {self.camera} not found. Please check if the camera is connected'
            self.logger.error(msg)
            raise CameraNotFound(msg)

        self.logger.info(f'Loaded camera {self._camera}')

        self.snapshot_settings = self._camera.CreateSnapshotSettings()
        self.config.fetch_all()
        self.logger.info('lumenera init test')
        if self.initial_config is not None:
            self.logger.info('lumenera init test')
            self.config.update(self.initial_config)
            self.logger.info('lumenera init test')
            self.config.apply_all()
            self.logger.info('lumenera init test')
        self.logger.info('lumenera init exit')
    
    @Feature()
    def acquisition_mode(self):
        self.logger.debug(f'calling {inspect.stack()[0][3]}')
        return self._acquisition_mode

    @acquisition_mode.setter
    def acquisition_mode(self, mode):
        self.logger.info(f'{self} Setting acquisition mode to {mode}')
        self._camera.DisableFastFrames()

        if mode == self.MODE_CONTINUOUS:
            self._acquisition_mode = mode

        elif mode == self.MODE_SINGLE_SHOT:
            try:
                self._camera.EnableFastFrames(self.snapshot_settings)
            except ApiError: 
                self.logger.error('Api error')
            self._acquisition_mode = mode

    @Feature()
    def exposure(self) -> Q_:
        """ The exposure of the camera, defined in units of time """
        self.logger.debug(f'calling {inspect.stack()[0][3]}')
        if self.config['exposure'] is not None:
            return self.config['exposure']
        try:
            if self.acquisition_mode == self.MODE_SINGLE_SHOT: return float(self.snapshot_settings.exposure * 1000) * Q_('us')
            exposure = float(self._camera.GetPropertyValue(PROPERTY_EXPOSURE) * 1000) * Q_('us')
            return exposure
        except:
            self.logger.error('Timeout getting the exposure')
            return self.config['exposure']

    @exposure.setter
    def exposure(self, exposure: Q_):
        self.logger.info(f'Setting exposure to {exposure}')
        try:
            if not isinstance(exposure, Q_):
                exposure = Q_(exposure)
            self._camera.SetProperty(PROPERTY_EXPOSURE,exposure.m_as('ms'))
            if self.acquisition_mode == self.MODE_SINGLE_SHOT:
                self._camera.DisableFastFrames()
                self.snapshot_settings.exposure = exposure.m_as('ms')
                self._camera.EnableFastFrames(self.snapshot_settings)
            exposure = float(self._camera.GetPropertyValue(PROPERTY_EXPOSURE) * 1000) * Q_('us')
            self.config.upgrade({'exposure': exposure})
        except:
            self.logger.error(f'Timed out setting the exposure to {exposure}')

    @Feature()
    def gain(self):
        """ Gain is a float """
        self.logger.debug(f'calling {inspect.stack()[0][3]}')
        if self.acquisition_mode == self.MODE_SINGLE_SHOT:
            return self.snapshot_settings.gain
        try:
            return float(self._camera.GetPropertyValue(PROPERTY_GAIN))
        except:
            self.logger.error('Timeout while reading the gain from the camera')
            return self.config['gain']

    @gain.setter
    def gain(self, gain: float):
        self.logger.info(f'Setting gain to {gain}')
        if self.acquisition_mode == self.MODE_SINGLE_SHOT:
            self._camera.DisableFastFrames()
            self.snapshot_settings.gain = gain
            self._camera.EnableFastFrames(self.snapshot_settings)
        try:
            self._camera.SetProperty(PROPERTY_GAIN, gain)
        except:
            self.logger.error('Problem setting the gain')

    @Feature()
    def pixel_format(self):
        self.logger.debug(f'calling {inspect.stack()[0][3]}')
        """ Pixel format must be one of PIXEL_FORMAT_8 or PIXEL_FORMAT_16"""
        if self.acquisition_mode == self.MODE_SINGLE_SHOT:
            pixel_format = self.snapshot_settings.format.pixelFormat
        elif self.acquisition_mode == self.MODE_CONTINUOUS:
            pixel_format = self._camera.GetFrameFormat().pixelFormat

        if pixel_format == PIXEL_FORMAT_8:
            self.current_dtype = np.uint8
        elif pixel_format == PIXEL_FORMAT_16:
            self.current_dtype = np.uint16
        else:
            self.logger.warning(f'Current pixel format is {pixel_format} while only PIXEL_FORMAT_8 and PIXEL_FORMAT_16 are supported')
        return pixel_format

    @pixel_format.setter
    def pixel_format(self, mode):
        self.logger.info(f'Setting pixel format to {mode}')

        if self.acquisition_mode == self.MODE_SINGLE_SHOT:
            self._camera.DisableFastFrames()
            self.snapshot_settings.format.pixelFormat = mode
            self._camera.EnableFastFrames(self.snapshot_settings)
        
        self._camera.SetPixelFormat(mode)

        if mode == PIXEL_FORMAT_8:
            self.current_dtype = np.uint8
        elif mode == PIXEL_FORMAT_16:
            self.current_dtype = np.uint16
        else:
            self.logger.warning(f'Trying to set pixel_format to {mode}, which is not valid')
        self.logger.info(f'\tCurrent dtype is {self.current_dtype}')

    @Feature()
    def ccd_height(self):
        self.logger.debug(f'calling {inspect.stack()[0][3]}')
        return self._camera.GetPropertyValue(PROPERTY_MAX_HEIGHT)

    @Feature()
    def ccd_width(self):
        self.logger.debug(f'calling {inspect.stack()[0][3]}')
        return self._camera.GetPropertyValue(PROPERTY_MAX_WIDTH)

    @Feature()
    def width(self):
        self.logger.debug(f'calling {inspect.stack()[0][3]}')
        if self.acquisition_mode == self.MODE_SINGLE_SHOT: 
            return self.snapshot_settings.format.width
        elif self.acquisition_mode == self.MODE_CONTINUOUS:
            return self._camera.GetFrameFormat().width

    @Feature()
    def height(self):
        self.logger.debug(f'calling {inspect.stack()[0][3]}')
        if self.acquisition_mode == self.MODE_SINGLE_SHOT: 
            return self.snapshot_settings.format.height
        elif self.acquisition_mode == self.MODE_CONTINUOUS:
            return self._camera.GetFrameFormat().height

    @Feature()
    def ROI(self):
        self.logger.debug(f'calling {inspect.stack()[0][3]}')
        try:
            ff = self._camera.GetFormat()[0]
        except ApiError:
            self.logger.error(f'API error in {inspect.stack()[0][3]}')
        return ((ff.xOffset, ff.xOffset+ff.width),(ff.yOffset, ff.yOffset+ff.height))
        
    @ROI.setter
    def ROI(self, vals):
        x_offset, width = vals[0]
        y_offset, height = vals[1]
        x_unit = int(self._camera.GetPropertyValue(PROPERTY_UNIT_WIDTH))
        y_unit = int(self._camera.GetPropertyValue(PROPERTY_UNIT_HEIGHT))
        x_offset -= x_offset % x_unit
        width -= width % x_unit
        y_offset -= y_offset % y_unit
        height -= height % y_unit
        self.logger.info(f'Updating ROI: (x, y, width, height) = ({x_offset}, {y_offset}, {width}, {height})')

        ff, fr = self._camera.GetFormat()
        ff.xOffset = int(x_offset)
        ff.width = int(width)
        ff.yOffset = int(y_offset)
        ff.height = int(height)
        self._camera.SetFormat(ff,fr)
        if self.acquisition_mode == self.MODE_SINGLE_SHOT:
            self._camera.DisableFastFrames()
        self.snapshot_settings.format.xOffset = int(x_offset)
        self.snapshot_settings.format.width = int(width)
        self.snapshot_settings.format.yOffset = int(y_offset)
        self.snapshot_settings.format.height = int(height)
        if self.acquisition_mode == self.MODE_SINGLE_SHOT: 
            self._camera.EnableFastFrames(self.snapshot_settings)          

    @Feature()
    def frame_rate(self):
        self.logger.debug(f'calling {inspect.stack()[0][3]}')
        return float(self._camera.GetFrameRate()) 

    #@Feature()
    #@not_implemented
    #def auto_exposure(self):
    #    pass   

    #@Feature()
    #@not_implemented
    #def auto_gain(self):
    #    pass

    #
    # ALL OTHER FEATURES
    #

    def trigger_camera(self):
        self.logger.info(f'Triggering {self} with mode: {self.acquisition_mode}')
        mode = self.acquisition_mode
        if mode == self.MODE_SINGLE_SHOT:
            try:
                self._camera.TriggerFastFrame()
            except ApiError:
                self.logger.error('ApiError in trigger_camera') 
        elif mode == self.MODE_CONTINUOUS:
            self._camera.SetStreamState(START_STREAMING)
    
    def read_camera(self) -> list:
        with self._lumenera_lock:
            img = []
            mode = self.acquisition_mode
            self.logger.debug(f'Grabbing mode: {mode}')
            if mode == self.MODE_SINGLE_SHOT:
                try:
                    buffer = self._camera.TakeFastFrame()
                except ApiError:
                    self.logger.error('ApiError in read_camera')
                img.append(np.frombuffer(buffer, dtype=self.current_dtype).reshape((self.width,self.height), order='F'))
                self.temp_image = img[0]
            elif mode == self.MODE_CONTINUOUS:
                buffer = self._camera.CaptureRawVideoImage()[0]
                # How to read all of available buffer in the fastest way? 
                assert buffer is not None
                img.append(np.frombuffer(buffer, dtype=self.current_dtype).reshape((self.width,self.height), order='F'))
                self.temp_image = img[0]
            return img
    
    @make_async_thread
    def continuous_reads(self):
        self.continuous_reads_running = True
        self.keep_reading = True
        while self.keep_reading:
            imgs = self.read_camera()
            if len(imgs) >= 1:
                for img in imgs:
                    self.new_image.emit(img)
            time.sleep(1 / self.frame_rate)
        self.continuous_reads_running = False

    def stop_continuous_reads(self):
        self.keep_reading = False
        while self.continuous_reads_running:
            time.sleep(.1)
        self.logger.info(f'{self} - Stopped continuous reads')

    def start_free_run(self):
        """ Starts a free run from the camera. It will preserve only the latest image. It depends
        on how quickly the experiment reads from the camera whether all the images will be available
        or only some.
        """
        if self.free_run_running:
            self.logger.info(f'Trying to start again the free acquisition of camera {self}')
            return
        self.logger.info(f'Starting a free run acquisition of camera {self}')
        self.free_run_running = True
        self.logger.debug('First frame of a free_run')
        self.acquisition_mode = self.MODE_CONTINUOUS
        self.trigger_camera()  # Triggers the camera only once
    
    @Action
    def stop_free_run(self):
        self._camera.SetStreamState(STOP_STREAMING)
        self.free_run_running = False

    @Action
    def stop_camera(self):
        self._camera.Close()
    
    def finalize(self):
        self.logger.info(f'Finalizing camera {self}')
        if self.finalized:
            return

        self.stop_continuous_reads()
        self.stop_free_run()

        self.stop_camera()
        while self.continuous_reads_running:
            time.sleep(.1)

        super(LumeneraCamera, self).finalize()
        self.finalized = True
    
