import time

import pyvisa

from NanoCETPy.dispertech.models.arduino import ArduinoModel
from experimentor.lib.log import get_logger, log_to_screen
from experimentor.models import Feature

rm = pyvisa.ResourceManager('@py')


class ArduinoExperimental(ArduinoModel):
    '''ArduinoModel with modified initialize routine to enable NanoCET software connection check screen
    '''
    def __init__(self, port=None, device=0, baud_rate=9600, initial_config=None):
        super().__init__(port=port, device=device, baud_rate=baud_rate, initial_config=initial_config)
        self.logger = get_logger(__name__)

    @Feature()
    def scattering_laser(self):
        """ Changes the laser power.

        Parameters
        ----------
        power : int
            Percentage of power (0-100)
        """
        return self._scattering_laser_power

    @scattering_laser.setter
    def scattering_laser(self, power):
        with self.query_lock:
            power = int(power * 4095 / 100)
            self.driver.query(f'laser:{power}')
            self.logger.info(f'laser:{power}')
            self._scattering_laser_power = int(power)

    @Feature()
    def top_led(self):
        return self._top_led

    @top_led.setter
    def top_led(self, status):
        with self.query_lock:
            self.driver.query(f'LED:TOP:{status}')
            self._top_led = status
            self.logger.info(f'LED:TOP:{status}')

    @Feature()
    def fiber_led(self):
        return self._fiber_led

    @fiber_led.setter
    def fiber_led(self, status):
        with self.query_lock:
            self.driver.query(f'LED:FIBER:{status}')
            self._fiber_led = status
            self.logger.info(f'LED:FIBER:{status}')


if __name__ == "__main__":
    #dev = Arduino.list_devices()[0]
    logger = get_logger()
    handler = log_to_screen(logger=logger)
    ard = ArduinoExperimental(port='ASRL4::INSTR', baud_rate=115200)
    ard.initialize()
    ard.fiber_led = 0
    time.sleep(.1)
    ard.top_led = 0
    for i in range(100,200):
        ard.scattering_laser = i * 100 / 4095
        time.sleep(1)
    ard.scattering_laser = 0
    ard.finalize()
   