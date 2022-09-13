"""
    Modified Arduino model to acommodate peculiarities of NanoCET operation

    .. todo:: add Features for the front panel LEDs
"""

import time
import pyvisa
from pyvisa import VisaIOError
from serial import SerialException

from dispertech.models.electronics.arduino import ArduinoModel
from dispertech.controller.devices.arduino.arduino import Arduino


from experimentor.lib.log import get_logger
from experimentor.models.decorators import make_async_thread
from experimentor.models import Feature



rm = pyvisa.ResourceManager('@py')


class ArduinoNanoCET(ArduinoModel):
    '''ArduinoModel with modified initialize routine to enable NanoCET software connection check screen

    while the :py:meth:`~sequential.models.experiment.MainSetup.initialize` of the :class:`~experiment.MainSetup()` runs in a loop 
    triggering the device initialization methods, this :meth:`initialize` only completes if a device is found,
    otherwise it raises an error.

    The device is found by querying any connected serial devices for their name and expecting 'Dispertech' as the beginning.

    Additional getters and setters for laser and LEDs have been added as the query string was changed in the Arduino firmware.
    '''
    def __init__(self, port=None, device=0, baud_rate=9600, initial_config=None):
        super().__init__(port=port, device=device, baud_rate=baud_rate, initial_config=initial_config)
        self.logger = get_logger(__name__)
        self.initialized = False
        self.initializing = False

    @make_async_thread
    def initialize(self):
        with self.query_lock:
            if self.initialized: return
            self.initializing = True
            if self.port:
                try:
                    if not self.port:
                        self.port = Arduino.list_devices()[self.device]
                    self.driver = rm.open_resource(self.port)
                    time.sleep(1)
                except:
                    raise SerialException()
                self.driver.baud_rate = self.baud_rate
            else:    
                device_ports = rm.list_resources()
                if len(device_ports) == 0: raise Exception()
                for port in device_ports:
                    try:
                        self.driver = rm.open_resource(port, baud_rate=115200)
                        time.sleep(2)
                        self.driver.query('IDN')
                        if self.driver.query('IDN').startswith('Dispertech'):
                            break
                        self.driver.close()
                    except:
                        try:
                            self.driver.close()
                        except:
                            pass
                try:
                    self.driver.session
                except pyvisa.errors.InvalidSession:
                    raise
            # This is very silly, but clears the buffer so that next messages are not broken
            try:
                self.driver.query("IDN")
            except VisaIOError:
                try:
                    self.driver.read()
                except VisaIOError:
                    print('another error')
                    pass
            self.config.fetch_all()
            if self.initial_config is not None:
                self.config.update(self.initial_config)
                self.config.apply_all()
            self.initialized = True
            self.logger.info('TEST arduino init done') 

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

    @Feature()
    def side_led(self):
        return self._side_led

    @side_led.setter
    def side_led(self, status):
        with self.query_lock:
            self.driver.query(f'LED:SIDE:{status}')
            self._side_led = status
            self.logger.info(f'LED:SIDE:{status}')
    @Feature()
    def power_led(self):
        return self._power_led

    @power_led.setter
    def power_led(self, status):
        with self.query_lock:
            self.driver.query(f'LED:POWER:{status}')
            self._power_led = status
            self.logger.info(f'LED:POWER:{status}')

    @Feature()
    def cartridge_led(self):
        return self._cartridge_led

    @cartridge_led.setter
    def cartridge_led(self, status):
        with self.query_lock:
            self.driver.query(f'LED:CARTRIDGE:{status}')
            self._cartridge_led = status
            self.logger.info(f'LED:CARTRIDGE:{status}')

    @Feature()
    def sample_led(self):
        return self._sample_led

    @sample_led.setter
    def sample_led(self, status):
        with self.query_lock:
            self.driver.query(f'LED:SAMPLE:{status}')
            self._sample_led = status
            self.logger.info(f'LED:SAMPLE:{status}')

    @Feature()
    def measuring_led(self):
        return self._measuring_led

    @measuring_led.setter
    def measuring_led(self, status):
        with self.query_lock:
            self.driver.query(f'LED:MEASURING:{status}')
            self._measuring_led = status
            self.logger.info(f'LED:MEASURING:{status}')
