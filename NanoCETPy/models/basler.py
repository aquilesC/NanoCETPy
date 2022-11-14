"""
    Modified Basler model to acommodate peculiarities of NanoCET operation
"""

from pypylon import pylon

from experimentor.lib.log import get_logger
from experimentor.models import Feature
from experimentor.models.devices.cameras.basler.basler import BaslerCamera
from experimentor.models.devices.cameras.exceptions import CameraNotFound


class BaslerNanoCET(BaslerCamera):
    '''BaslerCamera with modified initialize routine to enable NanoCET software connection check screen

    while the :py:meth:`~sequential.models.experiment.MainSetup.initialize` of the :class:`~experiment.MainSetup()` runs in a loop 
    triggering the device initialization methods, this :meth:`initialize` only completes if a device is found,
    otherwise it raises an error.
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

    @Feature
    def ROI(self):
        """
        Retrieve the Region of interest, following the Basler convention:
        ((horizontal_offset, width), (vertical_offset, height))
        Note that indexing starts at 0
        """
        offset_X = self._driver.OffsetX.Value
        offset_Y = self._driver.OffsetY.Value
        width = self._driver.Width.Value
        height = self._driver.Height.Value
        return ((offset_X, width),(offset_Y, height))

    @ROI.setter
    def ROI(self, value):
        def snap_to_increment(a, a_max, a_inc):
            # Make sure the values don't exceed the sensor area, and express in units of minimal increment:
            offset = max(a[0], 0) / a_inc
            length = min(a[1], a_max - a[0]) / a_inc
            offset = round(offset * 2) / 2  # Round to nearest integer (except when it's exactly half).
            if offset % 1:                  # In that case, rounding depends on length being above or below increment
                if length % 1 < 0.5:
                    offset += offset % 1  # "ceil" (only works for #.0 and #.5)
                else:
                    offset //= 1  # floor
            offset = int(offset * a_inc)  # Convert to final value
            length = round(length * 2) / 2  # Round to nearest integer (except when it's exactly half):
            if length % 1:
                if offset < a[0]:
                    length += length % 1  # "ceil" (only works for #.0 and #.5)
                else:
                    length //= 1  # floor
            return (offset, int(length * a_inc))
        x_off, width = snap_to_increment(value[0], self._driver.WidthMax.Value, self._driver.Width.Inc)
        y_off, height = snap_to_increment(value[1], self._driver.HeightMax.Value, self._driver.Height.Inc)
        self._driver.OffsetX.SetValue(0)
        self._driver.OffsetY.SetValue(0)
        self.logger.debug(f'Setting width to {width}')
        self._driver.Width.SetValue(width)
        self.logger.debug(f'Setting Height to {height}')
        self._driver.Height.SetValue(height)
        self.logger.debug(f'Setting X offset to {x_off}')
        self._driver.OffsetX.SetValue(x_off)
        self.logger.debug(f'Setting Y offset to {y_off}')
        self._driver.OffsetY.SetValue(y_off)
        self.X = (x_off, width)
        self.Y = (y_off, height)
        self.logger.info(f'ROI updated to {(self.X, self.Y)}')

    # @Feature()
    # def ROI(self):
    #     """
    #     Retrieve the Region Of Interest as:
    #       [ [leftmost pixel index, rightmost pixel index + 1],
    #         [top pixel index, bottom pixel index + 1] ]
    #     I.e. the range is specified up to a pixel (not including that pixel). This is in line with pythonic indexing.
    #     If one of the values exceeds the range of the sensor, it will be limited to the sensor.
    #     If the value is invalid due to increment limitations, it will be adjusted to the nearest value.
    #     """
    #     offset_X = self._driver.OffsetX.Value
    #     offset_Y = self._driver.OffsetY.Value
    #     width = self._driver.Width.Value
    #     height = self._driver.Height.Value
    #     return ((offset_X, offset_X + width),(offset_Y, offset_Y + height))
    #
    # @ROI.setter
    # def ROI(self, vals):
    #     def snap_to_increment(a, a_max, a_inc):
    #         # Make sure the values don't exceed the sensor area, and express in units of minimal increment:
    #         a0 = max(min(a), 0) / a_inc
    #         a1 = min(max(a) + 1, a_max) / a_inc   # Note: the +1 is to be match the ROI definition used so far
    #         adiff = a1 - a0
    #         # Round to nearest integer (except when it's exactly half):
    #         a0, a1 = round(a0 * 2) / 2, round(a1 * 2) / 2
    #         # If it's half, round up or down depending on requested size
    #         if a1 - a0 > adiff:  # Only if current range is larger than requested: ceil
    #             a0 += a0 % 1  # "ceil" (only works for #.0 and #.5)
    #         else:
    #             a0 //= 1  # floor
    #         if a1 % 1:
    #             if a1 - a0 > adiff:
    #                 a1 //= 1  # floor
    #             else:
    #                 a1 += a1 % 1  # "ceil"
    #         return int(a0 * a_inc), int((a1 - a0) * a_inc)
    #     x_off, width = snap_to_increment(vals[0], self._driver.WidthMax.Value, self._driver.Width.Inc)
    #     y_off, height = snap_to_increment(vals[1], self._driver.HeightMax.Value, self._driver.Height.Inc)
    #     self._driver.OffsetX.SetValue(0)
    #     self._driver.OffsetY.SetValue(0)
    #     self.logger.debug(f'Setting width to {width}')
    #     self._driver.Width.SetValue(width)
    #     self.logger.debug(f'Setting Height to {height}')
    #     self._driver.Height.SetValue(height)
    #     self.logger.debug(f'Setting X offset to {x_off}')
    #     self._driver.OffsetX.SetValue(x_off)
    #     self.logger.debug(f'Setting Y offset to {y_off}')
    #     self._driver.OffsetY.SetValue(y_off)
    #     self.X = (x_off, x_off + width)
    #     self.Y = (y_off, y_off + height)
    #     self.logger.info(f'ROI updated to {(self.X, self.Y)}')




if __name__ == '__main__':
    try:
        conf_microscope = {
            "config": {
                "ROI": [[0, 1936], [0, 1216]],
                "auto_exposure": False,
                "auto_gain": False,
                "buffer_size": "2000MB",
                "exposure": "50ms",
                "gain": 0.0,
                "pixel_format": "Mono12",
            },
            "init": "a2A1920",
            "model": "basler",
            "model_camera": "ACE"
        }
        camera_microscope = BaslerNanoCET(conf_microscope['init'], conf_microscope['config'])
        camera_microscope.initialize()
        print("camera_microscope connected")
    except:
        print("Couldn't connect microscope camera")

    try:
        conf_fiber = {
            "config": {
                "ROI": [[0, 1280], [0, 960]],
                "auto_exposure": False,
                "auto_gain": False,
                "buffer_size": "2000MB",
                "binning": [1, 1],
                "exposure": "50ms",
                "gain": 0.0,
                "pixel_format": "Mono8",
            },
            "init": "daA1280",
            "model": "basler",
            "model_camera": "Dart"
        }
        camera_fiber = BaslerNanoCET(conf_fiber['init'], conf_fiber['config'])
        camera_fiber.initialize()
        print("camera_fiber connected")
    except:
        print("Couldn't connect fiber camera")

