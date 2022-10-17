"""
    Modified Arduino model to accommodate peculiarities of NanoCET operation

"""

import time

import pyvisa
from pyvisa import VisaIOError
from serial import SerialException

from NanoCETPy.dispertech.models.arduino import ArduinoModel
from experimentor.lib.log import get_logger
from experimentor.models import Feature
from experimentor.models.decorators import make_async_thread

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
        self.led_states = {
            'standby':          (2, 0, 0, 0),  # when the device is powered, but not connected to software
            'connected':        (1, 0, 0, 0),  # connected to software
            'place_cartridge':  (1, 2, 0, 0),  # on "startup page": USER should place cartridge and oil, click [continue] to move to next page
            'align':            (1, 1, 0, 0),  # on "focus/align page"
            'place_sample':     (1, 1, 2, 0),  # on "parameters page": USER should place sample
            'parameters':       (1, 1, 1, 0),  # on "parameters page": when returning form measurement page
            'measuring':        (1, 1, 1, 2),  # on "measurement page" while measuring
            'paused':           (1, 1, 1, 1),  # on "measurement page" while paused/stopped
            'error':            (2, 2, 2, 2),  # a general error state
        }
        self.last_state_set = 'standby'

    @Feature()
    def serial_number(self):
        with self.query_lock:
            return(self.driver.query('SN').strip().split(':')[1])

    def retrieve_factory_values(self):
        with self.query_lock:
            response = self.driver.query('FACTORY').strip()
            factory = [int(x) for x in response.split(':')[1].split(',')]
            self.factory_piezo = factory[:3]
            self.factory_cam = factory[3:]

    def home_piezo(self):
        timeout = self.driver.timeout
        self.driver.timeout = 30000
        with self.query_lock:
            self.driver.query('HOME')
        self.driver.timeout = timeout

    def move_piezo_to_factory(self):
        self.home_piezo()
        x, y, z = self.factory_piezo
        self.long_move_piezo('X', x)
        time.sleep(0.01)
        self.long_move_piezo('Y', y)
        while z:
            z_step = min(1000, z)
            z -= z_step
            time.sleep(0.01)
            self.long_move_piezo('Z', z_step)

    def long_move_piezo(self, axis, duration):
        """
        Moves the piezo for a given duration at a fixed speed (fixed in arduino)
        axis is 'X', 'Y', or 'Z'
        duration is in ms
        A negative duration moves negative direction, positive duration moves in positive direction.
        The maximum duration is limited to 1800ms, (to account for the piezo driver limitation and the serial timeout)
        """
        if axis not in ('X', 'Y', 'Z') or not isinstance(duration, int) or abs(duration) > 1800:
            self.logger.warning('Invalid axis or value for long_move_piezo')
            return
        with self.query_lock:
            self.driver.query(f'PIEZO:{axis}:{duration}')


    def state(self, name, state=(0, 0, 0, 0)):
        if name in self.led_states:
            state = self.led_states[name]
        elif not (name == 'manual' and type(state) in (list, tuple) and len(state)==4):
            self.logger.warning(f'Invalid state [{name}]')
            return
        self.last_state_set = name
        self.power_led, self.cartridge_led, self.sample_led, self.measuring_led = state


    @make_async_thread
    def initialize(self):
        with self.query_lock:
            if self.initialized: return
            self.initializing = True
            if self.port:
                try:
                    if not self.port:
                        self.port = rm.list_resources()[self.device]
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
                        if self.driver.query('IDN').startswith('Dispertech nanoCET FW 1.0'):
                            break
                        # self.driver.close()
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
            print(self.driver.query('INI'))
            if self.initial_config is not None:
                self.config.update(self.initial_config)
                self.config.apply_all()
            self.initialized = True
            # self.logger.info('TEST arduino init done')
            self.retrieve_factory_values()

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
            self.driver.query(f'LASER:{power}')
            self.logger.info(f'LASER:{power}')
            self._scattering_laser_power = int(power)

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


    @Feature()
    def lid(self):
        with self.query_lock:
            return self.driver.query(f'LID').strip()


if __name__ == '__main__':
    a = ArduinoNanoCET(baud_rate=115200)
    a.initialize()
    while not a.initialized:
        time.sleep(0.01)
    print(a.driver.query('IDN'))
    a.power_led = 1
    a.cartridge_led = 1
    a.sample_led = 1
    a.measuring_led = 1

