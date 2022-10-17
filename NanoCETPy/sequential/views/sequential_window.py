"""
    Module containing the main GUI window and all the functional widgets to be displayed on it.

    
"""

import os
import time

BASE_DIR_VIEW = os.path.dirname(os.path.abspath(__file__))

from PyQt5 import uic, QtGui
from PyQt5.QtCore import QTimer, pyqtSignal, pyqtSlot, QDir, Qt
from PyQt5.QtWidgets import QMainWindow, QWidget, QFileDialog, QLabel, QSizePolicy, QMessageBox

from experimentor import Q_
from experimentor.lib.log import get_logger
from experimentor.views.base_view import BaseView
from .camera_viewer_widget import CameraViewerWidget

logger = get_logger(__name__)


class SequentialMainWindow(QMainWindow, BaseView):
    '''Main Window of the Application with current UI being displayed on the main_widget.
    Listens to signals from this widget to change views'''
    init_failed = pyqtSignal()

    def __init__(self, experiment=None):
        super(SequentialMainWindow, self).__init__()

        # fontId = QtGui.QFontDatabase.addApplicationFont(os.path.join(BASE_DIR_VIEW, 'Roboto-Regular.ttf'))
        # families = QtGui.QFontDatabase.applicationFontFamilies(fontId)
        # font = QtGui.QFont(families[0])
        # QApplication.instance().setFont(font)
        #if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        #    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        #if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        #    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

        uic.loadUi(os.path.join(BASE_DIR_VIEW, 'Sequential_Main_Window.ui'), self)
        self.experiment = experiment
        self.experiment.parent = self  # Setting the SequentialMainWindow as the parent of experiment class
        self.setWindowIcon(QtGui.QIcon(os.path.join(BASE_DIR_VIEW, 'dispertech-logo.png')))
        
        self.sequence = ['\u2460 Startup\n', '\u2461 Place \ncartridge', '\u2462 Focus and \nAlign', '\u2463 Set up \nexperiment', '\u2464 Measure-\nment\n']
        self.label_redirect_dict = {
            self.sequence[0]: self.startup_w,
            self.sequence[1]: self.preferences_w,
            self.sequence[2]: self.focus_w,
            self.sequence[3]: self.parameters_w,
            self.sequence[4]: self.measurement_w,
             }
        self.left_frame.layout().addStretch()
        self.right_frame.layout().addStretch()
        self.init_failed.connect(self.initializing_failed)
        self.startup_w()
    
    def startup_w(self):
        self.clear_main_widget()
        startup_widget = StartupWidget(self.experiment)
        self.main_widget.layout().addWidget(startup_widget)
        startup_widget.ready_signal.connect(self.preferences_w)
        self.set_sequence_display(0)
        self.setWindowTitle('NanoCET - Startup')

    @pyqtSlot()
    def preferences_w(self):
        self.clear_main_widget()
        title = QLabel(' \u2461 Place cartridge', objectName='title')
        self.main_widget.layout().addWidget(title)
        preferences_widget = PreferencesWidget(self.experiment)
        self.main_widget.layout().addWidget(preferences_widget)
        preferences_widget.focus_signal.connect(self.focus_w)
        self.set_sequence_display(1)
        self.setWindowTitle('NanoCET - Place cartridge')
        self.experiment.electronics.state('place_cartridge')
    
    @pyqtSlot()
    def focus_w(self):
        self.clear_main_widget()
        title = QLabel('\u2462 Focus and Align', objectName='title')
        self.main_widget.layout().addWidget(title)
        focus_widget = FocusWidget(self.experiment)
        self.main_widget.layout().addWidget(focus_widget)
        focus_widget.parameters_signal.connect(self.parameters_w)
        focus_widget.status_signal.connect(self.set_status)
        self.set_sequence_display(2)
        self.setWindowTitle('NanoCET - Focus and Align')
        self.experiment.electronics.state('align')

    @pyqtSlot()
    def parameters_w(self):
        self.clear_main_widget()
        title = QLabel('\u2463 Set up experiment', objectName='title')
        self.main_widget.layout().addWidget(title)
        parameters_widget = ParametersWidget(self.experiment)
        self.main_widget.layout().addWidget(parameters_widget)
        parameters_widget.start_signal.connect(self.measurement_w)
        self.set_sequence_display(3)
        self.setWindowTitle('NanoCET - Set up experiment')
        self.experiment.electronics.state('place_sample')
    
    @pyqtSlot()
    def measurement_w(self):
        self.clear_main_widget()
        title = QLabel('\u2464 Measurement', objectName='title')
        self.main_widget.layout().addWidget(title)
        measurement_widget = MeasurementWidget(self.experiment)
        self.main_widget.layout().addWidget(measurement_widget)
        measurement_widget.quit_signal.connect(self.close_w)
        measurement_widget.parameters_signal.connect(self.parameters_w)
        self.set_sequence_display(4)
        self.setWindowTitle('NanoCET - Measurement')
        self.experiment.electronics.state('measuring')

    @pyqtSlot()
    def close_w(self):
        self.experiment.electronics.state('standby')
        self.clear_main_widget()
        title = QLabel('Closing', objectName='title')
        self.main_widget.layout().addWidget(title)
        close_widget = CloseWidget(self.experiment)
        self.main_widget.layout().addWidget(close_widget)
        close_widget.close_signal.connect(self.close)
        close_widget.preferences_signal.connect(self.preferences_w)
        self.set_sequence_display(5)
        self.setWindowTitle('NanoCET - Closing')

    @pyqtSlot(str)
    def set_status(self, status):
        self.statusbar.showMessage(status)

    def set_sequence_display(self, step_id):
        before = self.sequence[:step_id]
        after = self.sequence[step_id+1:]
        left, right = self.left_frame.layout(), self.right_frame.layout()
        for layout in (left, right):
            for i in range(layout.count()): 
                widget = layout.itemAt(i).widget()
                if widget: widget.deleteLater()
        for idx, step in enumerate(before): 
            widget = Label(step)
            left.insertWidget(idx,widget)
            widget.label_signal.connect(self.label_redirect)
        for idx, step in enumerate(after): right.insertWidget(idx,Label(step))  

    @pyqtSlot(str)
    def label_redirect(self, label_text):
        if not self.experiment.saving: 
            self.logger.info('TEST redirect')
            self.label_redirect_dict[label_text]()

    def clear_main_widget(self):
        for i in reversed(range(self.main_widget.layout().count())):
            widget = self.main_widget.layout().itemAt(i).widget()
            if widget: widget.deleteLater()

    @pyqtSlot()
    def initializing_failed(self):
        msgBox = QMessageBox(parent=self)
        # msgBox.setIcon(QMessageBox.Close)
        msgBox.setText("Could not detect all devices.\nCheck usb connection or drivers.")
        msgBox.setWindowTitle("Initializing failed")
        msgBox.setStandardButtons(QMessageBox.Close)
        button = msgBox.exec()
        if button == QMessageBox.Close:
            self.close()

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        if self.experiment.saving:
            msg = QMessageBox(parent=self)
            msg.setWindowTitle('Warning!')
            msg.setText("The experiment is still running. Do you really want to quit?")
            msg.setIcon(QMessageBox.Warning)
            msg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
            return_val = msg.exec()
            if return_val == QMessageBox.Cancel:
                a0.ignore()
                return
        logger.info('Main Window Closed')
        self.experiment.active = False
        self.experiment.finalize()
        super().closeEvent(a0)


class Label(QLabel):
    label_signal = pyqtSignal(str)

    def __init__(self, *args, **kwargs):
        super(Label, self).__init__(*args, **kwargs)
        self.setAlignment(Qt.AlignTop)
        self.setMaximumSize(150,100)
        self.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        self.setStyleSheet(
            'border: 2px solid rgba(0,0,0,30%);'
            'border-radius: 10px;'
            'max-height: 100px;'
            'max-width: 150px;')
        #self.mouseReleaseEvent.connect(self.label_emit)

    def mouseReleaseEvent(self, event):
        self.label_signal.emit(self.text())


class StartupWidget(QWidget, BaseView):
    '''Widget to check for connections to NanoCET and then emit signal
    
    TODO: Make it respond to status of hardware'''
    ready_signal = pyqtSignal()

    def __init__(self, experiment, parent=None):
        super(StartupWidget, self).__init__(parent=parent)
        uic.loadUi(os.path.join(BASE_DIR_VIEW, 'Startup_Widget.ui'), self)
        self.experiment = experiment

        self.intialized = [False, False, False]
        self.check_string = {True: 'initialized.', False: '...'}
        #self.device_label.setText(f' {self.experiment.camera_fiber.camera} \n\n {self.experiment.camera_microscope.camera} \n\n Electronics ')

        if self.experiment.electronics is None: self.experiment.initialize()
        self.check_connections_timer = QTimer()
        self.check_connections_timer.timeout.connect(self.check_connections)
        self.check_connections_timer.start(100)

    def check_connections(self):
        if self.experiment.electronics is None: return # to wait for initialize function of experiment
        initialized = [self.experiment.camera_fiber.initialized, self.experiment.camera_microscope.initialized, self.experiment.electronics.initialized]
        self.device_label.setText(f' {self.experiment.camera_fiber.camera} \n\n {self.experiment.camera_microscope.camera} \n\n Electronics ')
        self.check_label.setText(f' {self.check_string[initialized[0]]} \n\n {self.check_string[initialized[1]]} \n\n {self.check_string[initialized[2]]}')
        if all(initialized):
            self.ready_signal.emit()
            self.check_connections_timer.stop()
            logger.info('Ready')


class PreferencesWidget(QWidget, BaseView):
    '''Widget to enter username and saving directory for experiment'''
    focus_signal = pyqtSignal()

    def __init__(self, experiment, parent=None):
        super(PreferencesWidget, self).__init__(parent=parent)
        uic.loadUi(os.path.join(BASE_DIR_VIEW, 'Preferences_Widget.ui'), self)
        self.experiment = experiment
        self.config = self.experiment.config['info'] # Does this work?

        instructive_gif = QtGui.QMovie(os.path.join(BASE_DIR_VIEW, 'insert_cartridge.gif')) 
        self.picture_label.setMovie(instructive_gif)
        instructive_gif.start()
        self.helptext_label.setWordWrap(True)
        self.apply_button.clicked.connect(self.apply)
        self.browse_button.clicked.connect(self.browse)
        self.name_line.setText(str(self.config['user']))
        self.directory_line.setText(self.config['files']['folder'])
        #self.directory_box.setCurrentIndex(self.directory_box.findText(self.config['files']['folder']))

    def apply(self):
        # handle config stuff and LEDs
        if not os.path.isdir(self.directory_line.text()):
            msg = QMessageBox(parent=self)
            msg.setText("Please enter a valid directory")
            msg.exec()
            return
        self.config['files']['folder'] = self.directory_line.text()
        self.config['user'] = self.name_line.text()
        self.focus_signal.emit()
    
    def browse(self):
        directory = QDir.toNativeSeparators(QFileDialog.getExistingDirectory(
            self,
            'Select Saving directory',
            self.directory_line.text()))
        self.directory_line.setText(directory)
        #if len(directory) == 0: return
        #if self.directory_box.findText(directory) == -1:
        #    self.directory_box.addItem(directory)
        #self.directory_box.setCurrentIndex(self.directory_box.findText(directory))


class FocusWidget(QWidget, BaseView):
    '''Widget to focus the microscope on fiber and start alignment'''
    parameters_signal = pyqtSignal()
    status_signal = pyqtSignal(str)

    def __init__(self, experiment, parent=None):
        super(FocusWidget, self).__init__(parent=parent)
        uic.loadUi(os.path.join(BASE_DIR_VIEW, 'Focus_Widget.ui'), self)
        self.experiment = experiment

        self.microscope_viewer = CameraViewerWidget(parent=self)
        self.microscope_widget.layout().addWidget(self.microscope_viewer)
        self.microscope_timer = QTimer()
        self.microscope_timer.timeout.connect(self.update_microscope_viewer)

        self.experiment.focus_start() #Unset ROI also
        self.ROI_button.clicked.connect(self.set_ROI)
        self.align_button.clicked.connect(self.start_alignment)
        self.continue_button.clicked.connect(self.parameters)
        
        while not self.experiment.camera_microscope.continuous_reads_running:
            time.sleep(.1)
        self.resized = False
        self.microscope_timer.start(50)

    def update_microscope_viewer(self):
        img = self.experiment.get_latest_image()
        if img is not None: self.microscope_viewer.update_image(img)
        if not self.resized: 
            self.resize(self.width()+1, self.height()+1)
            self.resized = True

    def set_ROI(self):
        # Make sure to re-initialize the window (when moving through the software "non-linearly")
        if self.experiment.camera_microscope.ROI != self.experiment.config['camera_microscope']['config']['ROI']:
            self.experiment.focus_start()
        try:
            self.microscope_viewer.roi_box
            logger.info('Already displaying ROI box')
            return
        except:
            logger.info('Display ROI box')
        self.microscope_viewer.setup_roi_box()
        self.align_button.setFlat(False)
        self.align_button.style().unpolish(self.align_button)
        self.align_button.style().polish(self.align_button)

    def start_alignment(self):
        try:
            self.microscope_viewer.roi_box
        except:
            return
        self.status_signal.emit('Aligning laser to fiber center...')
        pos = self.microscope_viewer.roi_box.pos()
        size = self.microscope_viewer.roi_box.size()
        print('ROI box pos and size:', pos, size)
        self.experiment.focus_stop()
        time.sleep(1)
        current_roi = self.experiment.camera_microscope.ROI
        self.experiment.camera_microscope.ROI = (current_roi[0],(pos[1], size[1]))  # This assumes 2nd parameter is "length" and NOT endpoint
        self.experiment.start_alignment()
        self.check_timer = QTimer()
        self.check_timer.timeout.connect(self.check_alignment)
        self.check_timer.start(500)
        logger.info('Timer started')
        self.align_button.setText('Abort alignment')
        self.align_button.style().unpolish(self.align_button)  # ??
        self.align_button.style().polish(self.align_button)    # ??
        self.align_button.clicked.connect(self.abort_alignment)

    def abort_alignment(self):
        self.experiment.aligned = False  # check this ???
        self.check_timer.stop()
        self.align_button.setText('Align')
        self.align_button.style().unpolish(self.align_button)  # ??
        self.align_button.style().polish(self.align_button)  # ??
        self.align_button.clicked.connect(self.start_alignment)


    def check_alignment(self):
        logger.info('Check alignment')
        if self.experiment.aligned: 
            self.status_signal.emit('Alignment done')
            self.continue_button.setFlat(False)
            self.continue_button.style().unpolish(self.continue_button)
            self.continue_button.style().polish(self.continue_button)
            self.check_timer.stop()
            self.experiment.find_ROI()
            self.microscope_viewer.do_auto_range()
            self.resized = False

    def parameters(self):
        if not self.experiment.aligned: return
        
        self.status_signal.emit(' ')
        self.parameters_signal.emit()


class ParametersWidget(QWidget, BaseView):
    '''Widget to enter parameters for experiment'''
    start_signal = pyqtSignal()

    def __init__(self, experiment, parent=None):
        super(ParametersWidget, self).__init__(parent=parent)
        uic.loadUi(os.path.join(BASE_DIR_VIEW, 'Parameters_Widget.ui'), self)
        self.experiment = experiment

        self.microscope_viewer = CameraViewerWidget(parent=self)
        self.microscope_widget.layout().addWidget(self.microscope_viewer)
        self.microscope_viewer.imv.setPredefinedGradient('thermal')
        self.microscope_timer = QTimer()
        self.microscope_timer.timeout.connect(self.update_microscope_viewer)

        self.name_line.setText(str(self.experiment.config['info']['files']['description']))
        expt = self.experiment.config['camera_microscope']['config']['exposure']
        if expt[-2:] == 'ms': expt = int(expt[:-2])
        elif expt[-2:] == 'us': expt = int(expt[:-2]) * 0.001
        self.exp_line.setText(str(expt))
        self.gain_line.setText(str(self.experiment.config['camera_microscope']['config']['gain']))
        self.laser_line.setText(str(self.experiment.config['electronics']['laser']['power']))
        self.name_line.editingFinished.connect(self.update_parameters)
        self.exp_line.editingFinished.connect(self.update_parameters)
        self.gain_line.editingFinished.connect(self.update_parameters)
        self.laser_line.editingFinished.connect(self.update_parameters)

        self.start_button.clicked.connect(self.start)

        self.resized = False
        self.microscope_timer.start(50)
        self.update_parameters()

    def update_microscope_viewer(self):
        img = self.experiment.get_latest_image()
        self.microscope_viewer.update_image(img)
        if not self.resized: 
            self.resize(self.width()+1, self.height()+1)
            self.resized = True

    def update_parameters(self):
        self.experiment.update_camera(self.experiment.camera_microscope, {
            'exposure': Q_(self.exp_line.text()+'ms'),
            'gain': float(self.gain_line.text()),
        })
        self.experiment.config['info']['files'].update({
            'description': self.name_line.text()
        })
        self.experiment.set_laser_power(int(self.laser_line.text()))

    def start(self):
        self.experiment.active = True
        self.experiment.save_waterfall()
        self.start_signal.emit()


class MeasurementWidget(QWidget, BaseView):
    '''Widget to observe fiber and waterfall while measuring'''
    quit_signal = pyqtSignal()
    parameters_signal = pyqtSignal()
    preferences_signal = pyqtSignal()

    def __init__(self, experiment, parent=None):
        super(MeasurementWidget, self).__init__(parent=parent)
        uic.loadUi(os.path.join(BASE_DIR_VIEW, 'Measurement_Widget.ui'), self)
        self.experiment = experiment

        self.microscope_viewer = CameraViewerWidget(parent=self)
        self.microscope_viewer.imv.ui.histogram.hide()
        self.microscope_widget.layout().addWidget(self.microscope_viewer)
        self.microscope_viewer.imv.setPredefinedGradient('thermal')

        self.waterfall_viewer = CameraViewerWidget(parent=self)
        self.waterfall_viewer.imv.ui.histogram.hide()
        self.waterfall_widget.layout().addWidget(self.waterfall_viewer)
        self.waterfall_viewer.imv.setPredefinedGradient('thermal')
        self.microscope_timer = QTimer()
        self.microscope_timer.timeout.connect(self.update_microscope_viewer)
        self.waterfall_timer = QTimer()
        self.waterfall_timer.timeout.connect(self.update_waterfall_viewer)

        # self.experiment.reset_waterfall()
        self.stop_button.clicked.connect(self.stop_measurement)
        self.resume_button.clicked.connect(self.resume_measurement)
        self.change_button.clicked.connect(self.parameters)
        #self.more_menu = QMenu(self.more_button)
        #self.more_menu.addAction('With same cartrigde', self.parameters)
        #self.more_menu.addAction('With new cartridge', self.preferences)
        #self.more_button.setMenu(self.more_menu)
        self.quit_button.clicked.connect(self.quit)
        
        self.update_helptext_label()
        self.resized = False
        self.microscope_timer.start(50)
        self.waterfall_timer.start(50)

    def update_helptext_label(self):
        """
        TODO: The naming in the GUI needs to change (because it shows incorrect file), but this should be part of a whole update of saving procedure.
        """
        try:
            data_folder = self.experiment.prepare_folder()
            files = [x for x in os.listdir(data_folder) if x.endswith(".h5")]
            newest = max(files, key=lambda fname: os.path.getctime(os.path.join(data_folder, fname)))
        except Exception as e:
            newest = "Test_Experiment_001.hf"
        if self.experiment.active:
            new_filename = self.experiment.get_filename("")
            filename_split = new_filename.split(os.path.sep)
            self.helptext_label.setText(
                f"Measurement ongoing"
                f"\n\nData being saved to:\n"
                f"{os.path.sep.join(filename_split[:-1])}{os.path.sep}"
                f"\n{filename_split[-1]}"
                f"\n\nLaser power:\t{self.experiment.electronics.scattering_laser}"
                f"\nExposure time:\t{self.experiment.camera_microscope.config['exposure']}"
                f"\nGain:\t{self.experiment.camera_microscope.config['gain']}")
        else:

            self.helptext_label.setText(
                f"Measurement finished"
                f"\n\nData was saved to {newest}"
                f"\n\nLaser power:\t{self.experiment.electronics.scattering_laser}"
                f"\nExposure time:\t{self.experiment.camera_microscope.config['exposure']}"
                f"\nGain:\t{self.experiment.camera_microscope.config['gain']}")

    def update_microscope_viewer(self):
        img = self.experiment.get_latest_image()
        self.microscope_viewer.update_image(img)
        self.microscope_viewer.view.autoRange()
        if not self.resized:
            self.resize(self.width()+1, self.height()+1)
            # self.waterfall_viewer.view.autoRange()
            self.resized = True
            self.logger.info('resizing to force redraw')


    def update_waterfall_viewer(self):
        img = self.experiment.get_waterfall_image()

        self.waterfall_viewer.update_image(img)
        self.waterfall_viewer.view.autoRange()
        # self.waterfall_viewer.do_auto_range(ignore_zeros=True)
        self.waterfall_viewer.imv.setLevels(*self.experiment.waterfall_image_limits)

    def stop_measurement(self):
        if not self.experiment.saving: return
        self.experiment.active = False
        self.update_helptext_label()

        self.stop_button.setFlat(True)
        self.stop_button.style().unpolish(self.stop_button)
        self.stop_button.style().polish(self.stop_button)
        self.resume_button.setFlat(False)
        self.resume_button.style().unpolish(self.resume_button)
        self.resume_button.style().polish(self.resume_button)
        self.change_button.setFlat(False)
        self.change_button.style().unpolish(self.change_button)
        self.change_button.style().polish(self.change_button)
        self.quit_button.setFlat(False)
        self.quit_button.style().unpolish(self.quit_button)
        self.quit_button.style().polish(self.quit_button)
        self.experiment.electronics.state('paused')

    def parameters(self):
        if self.experiment.saving: return
        self.experiment.active = True
        self.parameters_signal.emit()
        self.experiment.electronics.state('parameters')

    def resume_measurement(self):
        if self.experiment.saving:
            return
        self.experiment.active = True
        self.update_helptext_label()
        self.experiment.save_waterfall()
        self.stop_button.setFlat(False)
        self.stop_button.style().unpolish(self.stop_button)
        self.stop_button.style().polish(self.stop_button)
        self.resume_button.setFlat(True)
        self.resume_button.style().unpolish(self.resume_button)
        self.resume_button.style().polish(self.resume_button)
        self.change_button.setFlat(True)
        self.change_button.style().unpolish(self.change_button)
        self.change_button.style().polish(self.change_button)
        self.quit_button.setFlat(True)
        self.quit_button.style().unpolish(self.quit_button)
        self.quit_button.style().polish(self.quit_button)
        self.experiment.electronics.state('measuring')

    def quit(self):
        if self.experiment.saving: return
        self.experiment.active = True
        self.quit_signal.emit()


class CloseWidget(QWidget, BaseView):
    '''Widget to close the application'''
    close_signal = pyqtSignal()
    preferences_signal = pyqtSignal()

    def __init__(self, experiment, parent=None):
        super(CloseWidget, self).__init__(parent=parent)
        uic.loadUi(os.path.join(BASE_DIR_VIEW, 'Close_Widget.ui'), self)
        self.experiment = experiment

        instructive_gif = QtGui.QMovie(os.path.join(BASE_DIR_VIEW, 'remove_cartridge.gif')) 
        self.picture_label.setMovie(instructive_gif)
        instructive_gif.start()

        self.close_button.clicked.connect(self.close)
        self.new_button.clicked.connect(self.preferences)

    def preferences(self):
        self.experiment.electronics.state('place_cartridge')
        self.experiment.aligned = False
        self.preferences_signal.emit()

    def close(self):
        self.close_signal.emit()


class XWidget(QWidget, BaseView):
    '''Widget to do something'''
    x_signal = pyqtSignal()

    def __init__(self, experiment, parent=None):
        super(XWidget, self).__init__(parent=parent)
        uic.loadUi(os.path.join(BASE_DIR_VIEW, 'X_Widget.ui'), self)
        self.experiment = experiment

    def x_function(self):
        self.x_signal.emit()


if __name__ == '__main__':
    from PyQt5.QtWidgets import QApplication
    from experimentor.lib.log import log_to_screen

    logger = get_logger(__name__)
    handler = log_to_screen(logger=logger)
    app = QApplication([])
    main_window = SequentialMainWindow()
    main_window.show()
    app.exec()