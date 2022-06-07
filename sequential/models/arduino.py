import time
import pyvisa
from pyvisa import VisaIOError
from serial import SerialException

from dispertech.models.electronics.arduino import ArduinoModel
from dispertech.controller.devices.arduino.arduino import Arduino


from experimentor.lib.log import get_logger
from experimentor.models.decorators import make_async_thread


rm = pyvisa.ResourceManager('@py')


class ArduinoNanoCET(ArduinoModel):
    '''ArduinoModel with modified initialize routine to enable NanoCET software connection check screen
    '''
    def __init__(self, port=None, device=0, baud_rate=9600, initial_config=None):
        super().__init__(port=port, device=device, baud_rate=baud_rate, initial_config=initial_config)
        self.logger = get_logger(__name__)
        self.initialized = False

    @make_async_thread
    def initialize(self):
        self.logger.info('TEST arduino init')
        with self.query_lock:
            self.logger.info('TEST arduino init lock')
            try:
                self.logger.info('TEST arduino init try1') 
                if not self.port:
                    self.port = Arduino.list_devices()[self.device]
                self.driver = rm.open_resource(self.port)
                self.logger.info('TEST arduino init try2') 
            except (FileNotFoundError, SerialException): 
                self.logger.error(f'Nothing in Port {self.port}')
                return
            self.logger.info('TEST arduino init sleep') 
            time.sleep(1)
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
            self.initialized = True
