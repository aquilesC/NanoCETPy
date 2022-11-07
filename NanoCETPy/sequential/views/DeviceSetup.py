USE_FIBER_CAMERA = False

from experimentor.lib.log import get_logger, log_to_screen
from NanoCETPy.sequential.models.experiment import MainSetup
from NanoCETPy import BASE_PATH
import yaml


import sys
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (QApplication, QGridLayout, QHBoxLayout, QVBoxLayout, QGroupBox, QSpinBox,
                             QPushButton, QWidget, QSlider)
import time

class NanoCETSetupGUI(QWidget):
    def __init__(self, experiment:MainSetup):
        self.logger = get_logger(name=__name__)
        super(NanoCETSetupGUI, self).__init__()
        self.experiment = experiment

        layout = QVBoxLayout()
        layout.addWidget(self.create_front_led_widget())
        layout.addWidget(self.create_chamber_led_widget())
        self.setLayout(layout)

    def create_chamber_led_widget(self):
        groupBox = QGroupBox('Sample chamber LEDs')
        layout = QHBoxLayout()
        self.button_fiber = QPushButton('Fiber', checkable=True, clicked=lambda state: setattr(self.experiment.electronics, "fiber_led", int(state)))
        self.button_top = QPushButton('Microscope', checkable=True, clicked=lambda state: setattr(self.experiment.electronics, "top_led", int(state)))
        layout.addWidget(self.button_fiber)
        layout.addWidget(self.button_top)
        groupBox.setLayout(layout)
        return groupBox

    def create_front_led_widget(self):
        groupBox = QGroupBox('Test frontpanel LEDs')
        layout = QHBoxLayout()
        button_off = QPushButton('off', clicked=lambda:self.front_led(0))
        button_blink = QPushButton('blink', clicked=lambda: self.front_led(2))
        button_on = QPushButton('on', clicked=lambda: self.front_led(1))
        layout.addWidget(button_off)
        layout.addWidget(button_blink)
        layout.addWidget(button_on)
        groupBox.setLayout(layout)
        return groupBox

    def front_led(self, value):
        for led in ("power_led", "cartridge_led", "sample_led", "measuring_led"):
            setattr(self.experiment.electronics, led, value)
            if value != 2:
                time.sleep(0.5)


        # print(value)
        # setattr(self.experiment.electronics, "power_led", value)
        # setattr(self.experiment.electronics, "cartridge_led", value)
        # # self.experiment.electronics._cartridge_led = value
        # self.experiment.electronics.sample_led = value
        # self.experiment.electronics.measuring_led = value
        # # leds = [self.experiment.electronics._power_led,
        # #         self.experiment.electronics._cartridge_led,
        # #         self.experiment.electronics._sample_led,
        # #         self.experiment.electronics._measuring_led]
        # # for k in range(4):
        # #     leds[k] = value
        # #     time.sleep(0.5)


if __name__ == '__main__':
    logger = get_logger()
    log_to_screen(logger=logger)
    experiment = MainSetup()
    if not (config_filepath := BASE_PATH / 'config_user.yml').is_file():
        config_filepath = BASE_PATH / 'resources/config_default.yml'
    experiment.load_configuration(config_filepath, yaml.UnsafeLoader)
    experiment.initialize()
    t0 = time.time()
    while time.time() < t0 + 10:
        try:
            if all([experiment.camera_fiber.initialized,
                   experiment.camera_microscope.initialized,
                   experiment.electronics.initialized]):
                break
        except:
            pass
    app = QApplication([])
    main_window = NanoCETSetupGUI(experiment=experiment)
    main_window.show()
    app.exec()

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

#
#
# class call_back:
#     """
#     A class to wrap the writing of properties into a function.
#     Instantiate an object with the arduino
#     """
#     def __init__(self, arduino, property_name, name):
#         self.arduino = arduino
#         self.property_name = property_name
#         self.name = name
#
#     def __call__(self, value):
#         print('setting', self.name, 'to', value)
#         setattr(self.arduino, self.property_name, value)
#         # self.property = value
#
# class Window(QWidget):
#     def __init__(self, arduino, camera_fiber=None, show_plot=False):
#         super(Window, self).__init__()
#         custom_font = QFont()
#         custom_font.setPointSize(12)
#         self.arduino = arduino
#         self.camera_fiber = camera_fiber
#         self.show_plot = show_plot
#
#
#
#         # self.camera_fiber.trigger_camera()
#         # img = self.camera_fiber.read_camera()[-1]
#
#
#
#         if self.camera_fiber:
#             self.viewport = GraphicsLayoutWidget()
#             self.view = self.viewport.addViewBox(lockAspect=False, enableMenu=True)
#             # self.imgItem = pg.ImageItem()
#             # self.view.addItem(self.imgItem)
#             self.imv = pg.ImageView(view=self.view)#, imageItem=self.imgItem)
#             self.imgItem = self.imv.getImageItem()
#
#             self.imv.ui.roiBtn.hide()
#             self.imv.ui.menuBtn.hide()
#
#             self.graph = pg.PlotWidget()
#             self.resize(1200, 800)
#         else:
#             self.resize(650, 450)
#
#         self.setFont(custom_font)
#         self.setWindowTitle("Electronics Testing NanoCET: Connecting...")
#
#         self.show()
#         self.timer = QTimer(self)
#         self.timer.timeout.connect(self.check_connection)
#         self.connect()
#
#         grid = QGridLayout()
#         self.sliders = []
#         grid.addWidget(QPushButton('ALL OFF', clicked=self.all_off), 0, 0)
#         grid.addWidget(self.led_slider('Top', 'top_led', max_val=1), 0, 1)
#         grid.addWidget(self.led_slider('Fiber', 'fiber_led', max_val=1), 0, 2)
#         grid.addWidget(self.led_slider('Side', 'side_led', max_val=1), 0, 3)
#         grid.addWidget(self.led_slider('Power', 'power_led'), 1, 0)
#         grid.addWidget(self.led_slider('Cartridge', 'cartridge_led'), 1, 1)
#         grid.addWidget(self.led_slider('Sample', 'sample_led'), 1, 2)
#         grid.addWidget(self.led_slider('Measuring', 'measuring_led'), 1, 3)
#         grid.addWidget(self.laser_slider('Laser', grid.columnCount(), 10, 100), 2, 0, 1, grid.columnCount())
#
#         self.piezo_speed = QSpinBox(value=10, maximum=2**6-1)
#         box_speed = QGroupBox('Piezo speed')
#         layout_speed = QGridLayout()
#         layout_speed.addWidget(self.piezo_speed, 0, 0)
#         box_speed.setLayout(layout_speed)
#
#         for i, name in {1: 'Mirror H?', 2: 'Mirror V?', 3: 'Lens'}.items():
#             grid.addWidget(self.piezo(i, name), 3, i - 1)
#
#         grid.addWidget(box_speed, 3, 3)
#
#         if self.camera_fiber:
#             grid.addWidget(self.imv, 0, 4, 4, 5)
#             grid.setColumnStretch(4, 9)
#
#         if self.show_plot:
#             grid.addWidget(self.graph, 4, 0, 4, grid.columnCount())
#             self.curves = [self.graph.plot([0])]
#             self.curves.append(self.graph.plot([0]))
#             self.gr = self.graph.getPlotItem()
#
#
#         self.setLayout(grid)
#
#         if self.camera_fiber:
#             self.connect_camera_fiber()
#
#
#     def connect_camera_fiber(self):
#         self.camera_fiber.initialize()
#         self.camera_fiber.start_free_run()
#         self.camera_fiber.continuous_reads()
#         self.timer_fiber = QTimer()
#         self.timer_fiber.timeout.connect(self.update_fiber_image)
#         time.sleep(0.2)
#         self.timer_fiber.start(50)
#
#     def update_fiber_image(self):
#         self.img = self.camera_fiber.temp_image
#         self.imv.setImage(self.img)#, autoLevels=auto_levels, autoRange=auto_range, autoHistogramRange=auto_histogram_range)
#
#     def process_fiber_image(self):
#         if self.show_plot and self.camera_fiber.initialized:
#             img = self.img
#             dark = img.min()
#             mx = img.max()
#             bright = int((mx - dark) * 0.9 + dark)  # the 90% value between min and max value
#             dark = int((bright - dark) * 0.1 + dark)  # the 10% value between "bright" and the min value: i.e. 9%
#             fom = (img < dark).sum() - (img > bright).sum()
#             fom2 = ((img < dark).sum() - (img > bright).sum()) * mx
#             print(fom, fom2)
#             self.gr.curves[0].append(fom)
#             self.gr.curves[1].append(fom2)
#             return fom, fom2
#
#
#     def check_connection(self):
#         try:
#             print(self.arduino.lid)
#             # idn = self.arduino.driver.query('IDN')
#             idn = True
#             # print(idn)
#         except:
#             idn = False
#         if not idn:
#             self.connected = False
#             self.timer.stop()
#             del self.arduino
#             # try:
#             #     del self.arduino
#             # except:
#             #     pass
#
#             print('Lost connection')
#             self.connect()
#
#     def connect(self):
#         self.connected = False
#         self.setWindowTitle("Electronics Testing NanoCET: Connecting...")
#         while not self.connected:
#             try:
#                 # self.arduino = ArduinoNanoCET(baud_rate=115200)
#                 self.arduino.initialize()
#             except:
#                 del self.arduino
#                 continue
#             t0 = time.time()
#             timeout = False
#             while not self.arduino.initialized:
#                 time.sleep(.01)
#                 if time.time() > t0 + 10:
#                     break
#             if not self.arduino.initialized:
#                 del self.arduino
#                 continue
#             idn = self.arduino.driver.query('IDN')
#             if isinstance(idn, str):
#                 self.setWindowTitle("Connected: "+idn)
#                 if not idn.lower().startswith('dispertech'):
#                     self.setWindowTitle("WARNING: Connected to unknown device")
#             self.connected = idn
#             # self.timer.start(1000)
#
#
#     def piezo(self, axis, name):
#         groupBox = QGroupBox('Piezo '+name)
#         layout = QGridLayout()
#         # def move_piezo_callback(dir, ax):
#         #     self.arduino.move_piezo(self.piezo_speed.value(), dir, ax)
#         #     self.process_fiber_image()
#         #
#         # layout.addWidget(QPushButton('-', clicked=lambda axis: move_piezo_callback(0, axis), maximumWidth=60), 0, 0)
#         # layout.addWidget(QPushButton('+', clicked=lambda axis: move_piezo_callback(1, axis), maximumWidth=60), 0, 1)
#
#         layout.addWidget(QPushButton('-', clicked=lambda : self.arduino.move_piezo(self.piezo_speed.value(), 0, axis), maximumWidth=60), 0, 0)
#         layout.addWidget(QPushButton('+', clicked=lambda : self.arduino.move_piezo(self.piezo_speed.value(), 1, axis), maximumWidth=60), 0, 1)
#
#         groupBox.setLayout(layout)
#         return groupBox
#
#     def all_off(self):
#         for slider in reversed(self.sliders):
#             slider.setValue(0)
#             time.sleep(0.01)
#
#     def laser_slider(self, name, gridspan=4, step=10, max_val=100):
#         groupBox = QGroupBox(name)
#         spinbox = QSpinBox()
#         spinbox.setMaximum(max_val)
#         slider = QSlider(Qt.Horizontal)
#         slider.setFocusPolicy(Qt.StrongFocus)
#         slider.setTickPosition(QSlider.TicksBothSides)
#         slider.setRange(0, max_val)
#         slider.setTickInterval(step)
#         slider.setPageStep(step)
#         slider.setSingleStep(step)
#         self.sliders.append(slider)
#
#         def set_laser(value):
#             print(f'Setting {name} to {value}')
#             self.arduino.scattering_laser = value
#
#         def spin_changed(value):
#             slider.setValue(value)
#             set_laser(value)
#
#         def slider_changed(value):
#             spinbox.setValue(value)
#             set_laser(value)
#
#         spinbox.valueChanged.connect(spin_changed)
#         slider.valueChanged.connect(slider_changed)
#         layout = QGridLayout()
#         layout.addWidget(spinbox, 0, 0)
#         layout.addWidget(slider, 0, 1)
#         groupBox.setLayout(layout)
#         return groupBox
#
#     def led_slider(self, name, arduino_property, max_val=2):
#         groupBox = QGroupBox(name)
#         slider = QSlider(Qt.Horizontal)
#         slider.setFocusPolicy(Qt.StrongFocus)
#         slider.setTickPosition(QSlider.TicksBothSides)
#         slider.setRange(0, max_val)
#         slider.setPageStep(1)
#         slider.setTickInterval(1)
#         slider.valueChanged.connect(call_back(self.arduino, arduino_property, name=name))
#         # slider.valueChanged.connect(lambda value: setattr(self.arduino, arduino_property, value))
#         self.sliders.append(slider)
#         layout = QGridLayout()
#         layout.addWidget(slider, 0, 0)
#         groupBox.setLayout(layout)
#         return groupBox
#
#     def closeEvent(self, event):
#         self.timer.stop()
#         if self.camera_fiber:
#             self.camera_fiber.stop_continuous_reads()
#             self.camera_fiber.stop_free_run()
#         if self.connected:
#             print('Closing connection to Arduino')
#             self.arduino.driver.close()
#         event.accept()
#
#
# if __name__ == '__main__':
#     from NanoCETPy.sequential.models.arduino import ArduinoNanoCET
#     from NanoCETPy.sequential.models.basler import BaslerNanoCET
#
#     if len(sys.argv) > 1:
#         for arg in sys.argv[1:]:
#             if arg.startswith('USE_FIBER_CAMERA='):
#                 c = arg.split('=')[-1].lower()
#                 if c in ('true', '1'):
#                     USE_FIBER_CAMERA = True
#                 if c in ('false', '0'):
#                     USE_FIBER_CAMERA = False
#
#     conf_fiber = {
#         "config": {
#             "ROI": [[0, 1280], [0, 960]],
#             "auto_exposure": False,
#             "auto_gain": False,
#             "buffer_size": "2000MB",
#             "binning": [1, 1],
#             "exposure": "50ms",
#             "gain": 0.0,
#             "pixel_format": "Mono8",
#         },
#         "init": "daA1280",
#         "model": "basler",
#         "model_camera": "Dart"
#     }
#     arduino = ArduinoNanoCET(baud_rate=115200)
#     if USE_FIBER_CAMERA:
#         camera_fiber = BaslerNanoCET(conf_fiber['init'], conf_fiber['config'])
#     else:
#         camera_fiber = None
#
#     app = QApplication(sys.argv)
#     window = Window(arduino, camera_fiber)
#     app.exec()