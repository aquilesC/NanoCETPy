"""
    Arduino Model
    =============
    This is an ad-hoc model for controlling an Arduino board, which will in turn control a piezo-mirror, a laser,
    and some LED's.
"""
from multiprocessing import Event
from threading import RLock
from time import sleep

import pyvisa
from pyvisa import VisaIOError

from NanoCETPy.dispertech.controllers.arduino import Arduino
from experimentor.lib.log import get_logger
from experimentor.models import Feature
from experimentor.models.decorators import make_async_thread
from experimentor.models.devices.base_device import ModelDevice

rm = pyvisa.ResourceManager('@py')


class ArduinoModel(ModelDevice):
    def __init__(self, port=None, device=0, baud_rate=9600, initial_config=None):
        """ Use the port if you know where the Arduino is connected, or use the device number in the order shown by
        pyvisa.
        """
        super().__init__()
        self._threads = []
        self._stop_temperature = Event()
        self.temp_electronics = 0
        self.temp_sample = 0
        self.query_lock = RLock()
        self.driver = None
        self.port = port
        self.device = device
        self.initial_config = initial_config
        self.baud_rate = baud_rate

        self.logger = get_logger()

        self._scattering_laser_power = None
        self._fluo_laser_power = None
        self._laser_led = 0
        self._fiber_led = 0
        self._top_led = 0
        self._side_led = 0
        self._power_led = 0
        self._measure_led = 0


    @make_async_thread
    def initialize(self):
        """ This is a highly opinionated initialize method, in which the power of the laser is set to a minimum, the
        servo shutter is closed, and LEDs are switched off.
        """
        with self.query_lock:
            if not self.port:
                self.port = Arduino.list_devices()[self.device]
            self.driver = rm.open_resource(self.port)
            sleep(1)
            self.driver.baud_rate = self.baud_rate
            # This is very silly, but clears the buffer so that next messages are not broken
            try:
                self.driver.query("IDN")
            except VisaIOError:
                try:
                    self.driver.read()
                except VisaIOError:
                    pass
            self.config.fetch_all()
            if self.initial_config is not None:
                self.config.update(self.initial_config)
                self.config.apply_all()

            self.logger.info(self.driver.query(f'INI'))

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
            self.driver.query(f'laser:{power}')
            self.logger.info(f'laser:{power}')
            self._scattering_laser_power = int(power)

    @Feature()
    def fluo_laser(self):
        """ Changes the power of the laser used for fluorescence.

        Parameters
        ----------
        power : int
            Percentage of power (0-100)
        """
        return self._fluo_laser_power

    @fluo_laser.setter
    def fluo_laser(self, power):
        with self.query_lock:
            out_power = round(power/100*4095)
            self.driver.query(f'OUT:488:{out_power}')
            self._fluo_laser_power = int(power)

    @Feature()
    def side_led(self):
        return self._side_led

    @side_led.setter
    def side_led(self, status):
        with self.query_lock:
            self.driver.query(f'LED:0:{status}')
            self._side_led = status
            self.logger.info(f'LED:0:{status}')

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
    def power_led(self):
        return self._power_led

    @power_led.setter
    def power_led(self, status):
        with self.query_lock:
            self.driver.query(f'LED:3:{status}')
            self._power_led = status
            self.logger.info(f'LED:3:{status}')

    @Feature()
    def processing_led(self):
        return self._laser_led

    @processing_led.setter
    def processing_led(self, status: int):
        with self.query_lock:
            self.driver.query(f'LED:4:{status}')
            self._laser_led = status
            self.logger.info(f'LED:4:{status}')

    @Feature()
    def initialising_led(self):
        return self._measure_led

    @initialising_led.setter
    def initialising_led(self, status):
        with self.query_lock:
            self.driver.query(f'LED:5:{status}')
            self._measure_led = status
            self.logger.info(f'LED:5:{status}')

    @Feature()
    def ready_led(self):
        return self._measure_led

    @ready_led.setter
    def ready_led(self, status):
        with self.query_lock:
            self.driver.query(f'LED:6:{status}')
            self._measure_led = status
            self.logger.info(f'LED:6:{status}')

    # @make_async_thread
    def move_piezo(self, speed, direction, axis):
        """ Moves the mirror connected to the board

        Parameters
        ----------
        speed : int
            Speed, from 0 to 2^6-1
        direction : int
            0 or 1, depending on which direction to move the mirror
        axis : int
            1, 2, or 3 to select the axis. Normally 1 and 2 are the mirror and 3 is the lens
        """
        # with self.query_lock:
        binary_speed = '{0:06b}'.format(speed)
        binary_speed = str(direction) + str(1) + binary_speed
        number = int(binary_speed, 2)
        bytestring = number.to_bytes(1, 'big')
        self.driver.query(f"mot{axis}")
        self.driver.write_raw(bytestring)
        self.driver.read()
        self.logger.info('Finished moving')

    def finalize(self):
        self.logger.info('Finalizing Arduino')
        self.power_led = 0
        self.power_led = 0
        if self.initial_config is not None:
            self.config.update(self.initial_config)
            self.config.apply_all()
        self.clean_up_threads()
        if len(self._threads):
            self.logger.warning(f'There are {len(self._threads)} still alive in Arduino')
        self.driver.close()
        super().finalize()
