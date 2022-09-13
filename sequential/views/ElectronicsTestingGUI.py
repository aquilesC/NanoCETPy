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

from PyQt5.QtGui import QFont

class call_back:
    def __init__(self, arduino, property_name, name):
        self.arduino = arduino
        self.property_name = property_name
        self.name = name

    def __call__(self, value):
        print('setting', self.name, 'to', value)
        setattr(self.arduino, self.property_name, value)
        # self.property = value

class Window(QWidget):
    def __init__(self, arduino):
        super(Window, self).__init__()
        custom_font = QFont()
        custom_font.setPointSize(14)
        self.setFont(custom_font)
        self.setWindowTitle("Electronics Testing NanoCET: Loading")
        self.resize(800, 500)
        self.show()

        self.arduino = arduino

        grid = QGridLayout()
        self.sliders = []
        grid.addWidget(QPushButton('All Off', clicked=lambda: [s.setValue(0) for s in self.sliders]), 0, 0)
        grid.addWidget(self.led_slider('Top', 'top_led', max_val=1), 0, 1)
        grid.addWidget(self.led_slider('Fiber', 'fiber_led', max_val=1), 0, 2)
        grid.addWidget(self.led_slider('Side', 'side_led', max_val=1), 0, 3)
        grid.addWidget(self.led_slider('Power', 'power_led'), 1, 0)
        grid.addWidget(self.led_slider('Cartridge', 'cartridge_led'), 1, 1)
        grid.addWidget(self.led_slider('Sample', 'sample_led'), 1, 2)
        grid.addWidget(self.led_slider('Measuring', 'measuring_led'), 1, 3)
        grid.addWidget(self.laser_slider('Laser', grid.columnCount(), 10, 100), 2, 0, 1, grid.columnCount())

        self.piezo_speed = QSpinBox(value=10, maximum=2**6-1)
        box_speed = QGroupBox('Piezo speed')
        layout_speed = QGridLayout()
        layout_speed.addWidget(self.piezo_speed, 0, 0)
        box_speed.setLayout(layout_speed)

        for i, name in {1: 'Mirror V?', 2: 'Mirror H?', 3: 'Lens'}.items():
            grid.addWidget(self.piezo(i, name), 3, i - 1)

        grid.addWidget(box_speed, 3, 3)
        self.setLayout(grid)

        arduino.initialize()
        while not arduino.initialized:
            time.sleep(.01)
        idn = self.arduino.driver.query('IDN')
        if isinstance(idn, str):
            self.setWindowTitle(idn)
            if not idn.lower().startswith('dispertech'):
                print("WARNING: IDN string doesn't contain 'Dispertech'")

    def piezo(self, axis, name):
        groupBox = QGroupBox('Piezo '+name)
        layout = QGridLayout()
        layout.addWidget(QPushButton('-', clicked=lambda: self.arduino.move_piezo(self.piezo_speed.value(), 0, axis), maximumWidth=60), 0, 0)
        layout.addWidget(QPushButton('+', clicked=lambda: self.arduino.move_piezo(self.piezo_speed.value(), 1, axis), maximumWidth=60), 0, 1)
        groupBox.setLayout(layout)
        return groupBox

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

        def set_laser(value):
            print(f'Setting {name} to {value}')
            self.arduino.scattering_laser = value

        def spin_changed(value):
            slider.setValue(value)
            set_laser(value)

        def slider_changed(value):
            spinbox.setValue(value)
            set_laser(value)

        spinbox.valueChanged.connect(spin_changed)
        slider.valueChanged.connect(slider_changed)
        layout = QGridLayout()
        layout.addWidget(spinbox, 0, 0)
        layout.addWidget(slider, 0, 1)
        groupBox.setLayout(layout)
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
        slider.valueChanged.connect(call_back(arduino, arduino_property, name=name))
        self.sliders.append(slider)
        layout = QGridLayout()
        layout.addWidget(slider, 0, 0)
        groupBox.setLayout(layout)

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
    sys.exit(app.exec())