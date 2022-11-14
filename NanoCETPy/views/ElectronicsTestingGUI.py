USE_FIBER_CAMERA = False

import sys
from NanoCETPy.models.arduino import ArduinoNanoCET
from NanoCETPy.models.basler import BaslerCamera as Camera
from NanoCETPy.models.experiment import MainSetup
from experimentor import Q_
import time
from scipy import ndimage
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (QApplication, QGridLayout, QHBoxLayout, QGroupBox, QSpinBox,
                             QPushButton, QWidget, QSlider)


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
import pyqtgraph as pg
from pyqtgraph import GraphicsLayoutWidget


class call_back:
    """
    A class to wrap the writing of properties into a function.
    Instantiate an object with the arduino
    """
    def __init__(self, arduino, property_name, name):
        self.arduino = arduino
        self.property_name = property_name
        self.name = name

    def __call__(self, value):
        print('setting', self.name, 'to', value)
        setattr(self.arduino, self.property_name, value)
        # self.property = value

class Window(QWidget):
    def __init__(self, arduino, camera_fiber=None, plot_func=None):
        super(Window, self).__init__()
        custom_font = QFont()
        custom_font.setPointSize(12)
        self.arduino = arduino
        self.camera_fiber = camera_fiber
        self.plot_func = plot_func

        # self.camera_fiber.trigger_camera()
        # img = self.camera_fiber.read_camera()[-1]


        if self.camera_fiber:
            self.viewport = GraphicsLayoutWidget()
            self.view = self.viewport.addViewBox(lockAspect=False, enableMenu=True)
            # self.imgItem = pg.ImageItem()
            # self.view.addItem(self.imgItem)
            self.imv = pg.ImageView(view=self.view)#, imageItem=self.imgItem)
            self.imgItem = self.imv.getImageItem()

            self.imv.ui.roiBtn.hide()
            self.imv.ui.menuBtn.hide()

            self.pw = pg.PlotWidget()
            self.resize(1200, 800)

            self.exposure_widget = QGroupBox('Exposure')
            exposure_slider = QSlider(Qt.Horizontal)
            exposure_slider.setRange(0, 1)
            exposure_slider.setValue(1)
            exposure_slider.valueChanged.connect(self.change_fiber_cam_exposure)
            exposure_layout = QHBoxLayout()
            exposure_layout.addWidget(exposure_slider)
            self.exposure_widget.setLayout(exposure_layout)
            # self.exposure_widget.setLayout(QHBoxLayout())
            # self.exposure_widget.layout().addWidget(exposure_slider)

        else:
            self.resize(650, 450)

        self.setFont(custom_font)
        self.setWindowTitle("Electronics Testing NanoCET: Connecting...")

        self.show()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_connection)
        self.connect()

        grid = QGridLayout()
        self.sliders = []
        grid.addWidget(QPushButton('ALL OFF', clicked=self.all_off), 0, 0)
        grid.addWidget(self.led_slider('Top', 'top_led', max_val=1), 0, 1)
        grid.addWidget(self.led_slider('Fiber', 'fiber_led', max_val=1), 0, 2)
        grid.addWidget(self.led_slider('Side', 'side_led', max_val=1), 0, 3)
        grid.addWidget(self.led_slider('Power', 'power_led'), 1, 0)
        grid.addWidget(self.led_slider('Cartridge', 'cartridge_led'), 1, 1)
        grid.addWidget(self.led_slider('Sample', 'sample_led'), 1, 2)
        grid.addWidget(self.led_slider('Measuring', 'measuring_led'), 1, 3)
        grid.addWidget(self.laser_slider('Laser', 10, 100), 2, 0, 1, grid.columnCount()-bool(self.plot_func))

        self.piezo_speed = QSpinBox(value=10, maximum=2**6-1)
        box_speed = QGroupBox('Piezo speed')
        layout_speed = QGridLayout()
        layout_speed.addWidget(self.piezo_speed, 0, 0)
        box_speed.setLayout(layout_speed)

        for i, name in {1: 'Mirror H?', 2: 'Mirror V?', 3: 'Lens'}.items():
            grid.addWidget(self.piezo(i, name), 3, i - 1)

        grid.addWidget(box_speed, 3, 3)

        if self.camera_fiber:
            grid.addWidget(self.imv, 0, 4, 4, 5)
            grid.setColumnStretch(4, 9)
            grid.addWidget(self.exposure_widget, 2, 3)

        if self.plot_func and self.camera_fiber:
            grid.addWidget(self.pw, 4, 0, 4, grid.columnCount())
            self.plot = self.pw.plot([0])
            self.plot.setPen(pg.mkPen(100, 200, 100))

            self.plot2 = self.pw.plot([0])
            self.plot2.setPen(pg.mkPen(200, 100, 100))

            self.fom = []
            # self.curves.append(self.graph.plot([0]))
            # self.gr = self.pw.getPlotItem()


        self.setLayout(grid)

        if self.camera_fiber:
            self.connect_camera_fiber()


    def connect_camera_fiber(self):
        self.camera_fiber.initialize()
        time.sleep(1)
        self.camera_fiber.start_free_run()
        self.camera_fiber.continuous_reads()
        self.timer_fiber = QTimer()
        self.timer_fiber.timeout.connect(self.update_fiber_image)
        time.sleep(0.2)
        self.timer_fiber.start(50)

    def update_fiber_image(self):
        self.img = self.camera_fiber.temp_image
        self.imv.setImage(self.img)#, autoLevels=auto_levels, autoRange=auto_range, autoHistogramRange=auto_histogram_range)

    def process_fiber_image(self):
        if self.plot_func and self.camera_fiber.initialized:

            core_x, core_y = self.arduino.factory_cam
            cm = ndimage.measurements.center_of_mass(self.img ** 2)
            dist = ((cm[0] - core_y) ** 2 + (cm[1] - core_x) ** 2) ** 0.5
            print(f'stored coord {(core_y, core_x)} detected coord {cm}, distance: {dist}')


            fom = self.plot_func(self.img, core_x, core_y, tolerance=50)
            self.fom.append(fom)
            print(fom)
            self.plot.setData(self.fom)
            self.plot2.setData([k//2 for k in self.fom])

    def change_fiber_cam_exposure(self, slider_value):
        self.camera_fiber.stop_continuous_reads()
        self.camera_fiber.stop_free_run()
        exposures = (Q_('10us'), Q_('50ms'))
        self.camera_fiber.config.update({'exposure': exposures[slider_value]})
        self.camera_fiber.config.apply_all()

        self.camera_fiber.start_free_run()
        self.camera_fiber.continuous_reads()



    def check_connection(self):
        try:
            print(self.arduino.lid)
            # idn = self.arduino.driver.query('IDN')
            idn = True
            # print(idn)
        except:
            idn = False
        if not idn:
            self.connected = False
            self.timer.stop()
            del self.arduino
            # try:
            #     del self.arduino
            # except:
            #     pass

            print('Lost connection')
            self.connect()

    def connect(self):
        self.connected = False
        self.setWindowTitle("Electronics Testing NanoCET: Connecting...")
        while not self.connected:
            try:
                # self.arduino = ArduinoNanoCET(baud_rate=115200)
                self.arduino.initialize()
            except:
                del self.arduino
                continue
            t0 = time.time()
            timeout = False
            while not self.arduino.initialized:
                time.sleep(.01)
                if time.time() > t0 + 10:
                    break
            if not self.arduino.initialized:
                del self.arduino
                continue
            time.sleep(0.1)
            idn = self.arduino.driver.query('IDN')
            if isinstance(idn, str):
                self.setWindowTitle("Connected: "+idn)
                if not idn.lower().startswith('dispertech'):
                    self.setWindowTitle("WARNING: Connected to unknown device")
            self.connected = idn
            self.arduino.retrieve_factory_values()
            # self.timer.start(1000)


    def piezo(self, axis, name):
        groupBox = QGroupBox('Piezo '+name)
        layout = QGridLayout()

        def move_piezo_callback(dir, ax):
            self.arduino.move_piezo(self.piezo_speed.value(), dir, ax)
            self.process_fiber_image()

        layout.addWidget(QPushButton('-', clicked=lambda _: move_piezo_callback(0, axis), maximumWidth=60), 0, 0)
        layout.addWidget(QPushButton('+', clicked=lambda _: move_piezo_callback(1, axis), maximumWidth=60), 0, 1)

        # layout.addWidget(QPushButton('-', clicked=lambda : self.arduino.move_piezo(self.piezo_speed.value(), 0, axis), maximumWidth=60), 0, 0)
        # layout.addWidget(QPushButton('+', clicked=lambda : self.arduino.move_piezo(self.piezo_speed.value(), 1, axis), maximumWidth=60), 0, 1)

        groupBox.setLayout(layout)
        return groupBox

    def all_off(self):
        for slider in reversed(self.sliders):
            slider.setValue(0)
            time.sleep(0.01)

    def laser_slider(self, name, step=10, max_val=100):
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
        slider.valueChanged.connect(call_back(self.arduino, arduino_property, name=name))
        # slider.valueChanged.connect(lambda value: setattr(self.arduino, arduino_property, value))
        self.sliders.append(slider)
        layout = QGridLayout()
        layout.addWidget(slider, 0, 0)
        groupBox.setLayout(layout)
        return groupBox

    def closeEvent(self, event):
        self.timer.stop()
        if self.camera_fiber:
            self.camera_fiber.stop_continuous_reads()
            self.camera_fiber.stop_free_run()
        if self.connected:
            print('Closing connection to Arduino')
            self.arduino.driver.close()
        event.accept()


if __name__ == '__main__':
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            if arg.startswith('USE_FIBER_CAMERA='):
                c = arg.split('=')[-1].lower()
                if c in ('true', '1'):
                    USE_FIBER_CAMERA = True
                if c in ('false', '0'):
                    USE_FIBER_CAMERA = False

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
    arduino = ArduinoNanoCET(baud_rate=115200)
    if USE_FIBER_CAMERA:
        camera_fiber = Camera(conf_fiber['init'], conf_fiber['config'])
    else:
        camera_fiber = None

    app = QApplication(sys.argv)
    window = Window(arduino, camera_fiber, plot_func=MainSetup.focus_optimization_function)
    app.exec()