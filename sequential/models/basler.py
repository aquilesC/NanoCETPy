from pypylon import pylon, _genicam

from experimentor.models.devices.cameras.basler.basler import BaslerCamera
from experimentor.models.devices.cameras.exceptions import CameraNotFound

from experimentor.lib.log import get_logger
from experimentor.models.action import Action



class BaslerNanoCET(BaslerCamera):
    '''BaslerCamera with modified initialize routine to enable NanoCET software connection check screen
    '''

    def __init__(self, camera, initial_config=None):
        super().__init__(camera, initial_config=initial_config)
        self.logger = get_logger(__name__)
        self.initialized = False

    #@Action
    def initialize(self):
        self.logger.debug('Initializing Basler Camera')
        tl_factory = pylon.TlFactory.GetInstance()
        devices = tl_factory.EnumerateDevices()
        if len(devices) == 0:
            msg = f'Basler {self.camera} not found. Please check if the camera is connected'
            self.logger.error(msg)
            raise CameraNotFound('No camera found')

        for device in devices:
            if self.camera in device.GetFriendlyName():
                self._driver = pylon.InstantCamera()
                self._driver.Attach(tl_factory.CreateDevice(device))
                self._driver.Open()
                self.friendly_name = device.GetFriendlyName()

        if not self._driver:
            msg = f'Basler {self.camera} not found. Please check if the camera is connected'
            self.logger.error(msg)
            raise CameraNotFound(msg)

        self.logger.info(f'Loaded camera {self._driver.GetDeviceInfo().GetModelName()}')

        # self._driver.RegisterConfiguration(pylon.SoftwareTriggerConfiguration(), pylon.RegistrationMode_ReplaceAll,
        #                                    pylon.Cleanup_Delete)

        self.config.fetch_all()
        if self.initial_config is not None:
            self.config.update(self.initial_config)
            self.config.apply_all()
        self.initialized = True

    def clear_ROI(self):
        self._driver.OffsetX.SetValue(0)
        self._driver.OffsetY.SetValue(0)
        self._driver.Width.SetValue(self._driver.WidthMax.GetValue())
        self._driver.Height.SetValue((self._driver.HeightMax.GetValue()))


