from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5.QtWidgets import (QApplication, QGridLayout, QGroupBox, QSpinBox,
                             QPushButton, QHBoxLayout, QWidget, QSlider)
import time


# class LedSlider(QSlider):
#     def __init__(self, arduino, name, arduino_command, states=('off', 'on', 'blink'), *args, **kwargs):
#         super().__init__(self, *args, **kwargs)
#         self.name = name
#         self.command = arduino_command
#         self.states = states
#         self.valueChanged(self.send_command)
#         self.arduino = arduino
#
#     def send_command(self, value):
#         self.arduino.

class call_back:
    def __init__(self, property, name):
        self.property = property
        self.name = name

    def __call__(self, value):
        print('setting', self.name, 'to', value)
        self.property = value

class Window(QWidget):
    def __init__(self, arduino):
        super(Window, self).__init__()
        self.setWindowTitle("Electronics Testing NanoCET: Loading")
        self.resize(500, 300)
        self.show()

        self.arduino = arduino

        grid = QGridLayout()
        self.sliders = []

        grid.addWidget(QPushButton('OFF', clicked=lambda: [s.setValue(0) for s in self.sliders]), 0, 0)
        grid.addWidget(self.led_slider('Top', self.arduino.top_led, max_val=1), 0, 2)
        grid.addWidget(self.led_slider('Fiber', self.arduino.fiber_led, max_val=1), 0, 3)
        grid.addWidget(self.led_slider('Power', lambda status: self.arduino.driver.query(f'LED:POWER:{status}')), 1, 0)
        grid.addWidget(self.led_slider('Cartridge', lambda status: self.arduino.driver.query(f'LED:CARTRIDGE:{status}')), 1, 1)
        grid.addWidget(self.led_slider('Sample', lambda status: self.arduino.driver.query(f'LED:SAMPLE:{status}')), 1, 2)
        grid.addWidget(self.led_slider('Measuring', lambda status: self.arduino.driver.query(f'LED:MEASURING:{status}')), 1, 3)
        grid.addWidget(self.laser_slider('Laser', grid.columnCount(), 10, 100), 2, 0, 1, grid.columnCount())

        # grid.addWidget(self.add_LED_slider('Laser', lambda status: self.arduino.driver.query(f'LED:MEASURING:{status}'), max_val=100), 2, 1, 1, 3)

        self.setLayout(grid)



        arduino.initialize()
        while not arduino.initialized:
            time.sleep(.01)
        idn = self.arduino.driver.query('IDN')
        if isinstance(idn, str):
            self.setWindowTitle(idn)
            if not idn.lower().startswith('dispertech'):
                print("WARNING: IDN string doesn't contain 'Dispertech'")



    def laser_slider(self, name, gridspan=4, step=10, max_val=100):
        groupBox = QGroupBox(name)
        spinbox = QSpinBox()
        spinbox.setMaximum(max_val)
        slider = QSlider(Qt.Horizontal)
        slider.setFocusPolicy(Qt.StrongFocus)
        slider.setTickPosition(QSlider.TicksBothSides)
        slider.setRange(0, max_val)
        slider.setTickInterval(step)
        slider.setPageStep(step)
        slider.setSingleStep(step)
        self.sliders.append(slider)

        # slider.setSingleStep(step)
        def spin_changed(value):
            slider.setValue(value)

        def slider_changed(value):
            spinbox.setValue(value)

        spinbox.valueChanged.connect(spin_changed)
        slider.valueChanged.connect(slider_changed)
        hbox = QHBoxLayout()
        hbox.addWidget(spinbox)
        hbox.addWidget(slider)
        # grid.addStretch(1)
        groupBox.setLayout(hbox)
        return groupBox

    def led_slider(self, name, arduino_property, max_val=2):
        groupBox = QGroupBox(name)

        slider = QSlider(Qt.Horizontal)
        slider.setFocusPolicy(Qt.StrongFocus)
        slider.setTickPosition(QSlider.TicksBothSides)
        slider.setRange(0, max_val)
        slider.setPageStep(1)
        slider.setTickInterval(1)
        print(slider.pageStep())
        slider.valueChanged.connect(call_back(arduino_property, name=name))
        self.sliders.append(slider)
        # @pyqtSlot
        # def test(value):
        #     print(value)
        # slider.valueChanged.connect(test)
        grid = QGridLayout()
        grid.addWidget(slider, 0, 0)
        # vbox.addStretch(1)
        groupBox.setLayout(grid)

        return groupBox


if __name__ == '__main__':
    import sys

    # Can't do relative import because NanoCETPy is not a package
    #from ..models.arduino import ArduinoNanoCET
    sys.path.append('../models')
    from arduino import ArduinoNanoCET

    arduino = ArduinoNanoCET(baud_rate=115200)
    app = QApplication(sys.argv)
    window = Window(arduino)
    # window.show()
    sys.exit(app.exec())