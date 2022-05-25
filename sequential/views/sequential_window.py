import os
import time
import numpy as np

BASE_DIR_VIEW = os.path.dirname(os.path.abspath(__file__))

from PyQt5 import uic, QtGui
from PyQt5.QtCore import QTimer, pyqtSignal, pyqtSlot, QDir
from PyQt5.QtWidgets import QMainWindow, QStatusBar, QWidget, QFileDialog

from experimentor import Q_
from experimentor.lib.log import get_logger
from experimentor.views.base_view import BaseView
from experimentor.views.camera.camera_viewer_widget import CameraViewerWidget

logger = get_logger(__name__)


class SequentialMainWindow(QMainWindow, BaseView):
    '''Main Window of the Application with current UI being displayed on the main_widget.
    Listens to signals from this widget to change views'''

    def __init__(self, experiment=None):
        super(SequentialMainWindow, self).__init__()
        uic.loadUi(os.path.join(BASE_DIR_VIEW, 'Sequential_Main_Window.ui'), self)
        self.experiment = experiment

        self.startup_w()
    
    def startup_w(self):
        startup_widget = StartupWidget(self.experiment)
        self.main_widget.layout().addWidget(startup_widget)
        startup_widget.ready_signal.connect(self.preferences_w)
        self.setWindowTitle('NanoCET - Startup')

    @pyqtSlot()
    def preferences_w(self):
        self.clear_main_widget()
        preferences_widget = PreferencesWidget(self.experiment)
        self.main_widget.layout().addWidget(preferences_widget)
        preferences_widget.focus_signal.connect(self.focus_w)
        self.setWindowTitle('NanoCET - Preferences')
    
    @pyqtSlot()
    def focus_w(self):
        self.clear_main_widget()
        focus_widget = FocusWidget(self.experiment)
        self.main_widget.layout().addWidget(focus_widget)
        focus_widget.parameters_signal.connect(self.parameters_w)
        focus_widget.status_signal.connect(self.set_status)
        self.setWindowTitle('NanoCET - Focus and Align')

    @pyqtSlot()
    def parameters_w(self):
        self.clear_main_widget()
        parameters_widget = ParametersWidget(self.experiment)
        self.main_widget.layout().addWidget(parameters_widget)
        parameters_widget.start_signal.connect(self.measurement_w)
        self.setWindowTitle('NanoCET - Enter parameters')
    
    @pyqtSlot()
    def measurement_w(self):
        self.clear_main_widget()
        measurement_widget = MeasurementWidget(self.experiment)
        self.main_widget.layout().addWidget(measurement_widget)
        measurement_widget.quit_signal.connect(self.close_w)
        self.setWindowTitle('NanoCET - Measurement')

    @pyqtSlot()
    def close_w(self):
        self.clear_main_widget()
        close_widget = CloseWidget(self.experiment)
        self.main_widget.layout().addWidget(close_widget)
        close_widget.close_signal.connect(self.close)
        self.setWindowTitle('NanoCET - Closing')

    @pyqtSlot(str)
    def set_status(self, status):
        self.statusbar.showMessage(status)

    def clear_main_widget(self):
        widget = self.main_widget.layout().itemAt(0).widget()
        if widget: widget.deleteLater()

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        logger.info('Main Window Closed')
        super().closeEvent(a0)


class StartupWidget(QWidget, BaseView):
    '''Widget to check for connections to NanoCET and then emit signal
    
    TODO: Make it respond to status of hardware'''
    ready_signal = pyqtSignal()

    def __init__(self, experiment, parent=None):
        super(StartupWidget, self).__init__(parent=parent)
        uic.loadUi(os.path.join(BASE_DIR_VIEW, 'Startup_Widget.ui'), self)
        self.experiment = experiment

        self.connections = False
        self.count = 0

        self.check_connections_timer = QTimer()
        self.check_connections_timer.timeout.connect(self.check_connections)
        self.check_connections_timer.start(100)

    def check_connections(self):
        if self.connections:
            self.ready_signal.emit()
            logger.info('Ready')
        self.count +=1
        if self.count == 30: self.connections = True


class PreferencesWidget(QWidget, BaseView):
    '''Widget to enter username and saving directory for experiment'''
    focus_signal = pyqtSignal()

    def __init__(self, experiment, parent=None):
        super(PreferencesWidget, self).__init__(parent=parent)
        uic.loadUi(os.path.join(BASE_DIR_VIEW, 'Preferences_Widget.ui'), self)
        self.experiment = experiment

        self.apply_button.clicked.connect(self.apply)
        self.browse_button.clicked.connect(self.browse)
        self.name_line.setText(self.experiment.config['user']['name'])
        self.directory_box.addItem(self.experiment.config['info']['folder'])
        self.directory_box.setCurrentIndex(self.directory_box.findText(self.experiment.config['info']['folder']))

    def apply(self):
        # handle config stuff and LEDs
        self.focus_signal.emit()
    
    def browse(self):
        directory = QDir.toNativeSeparators(QFileDialog.getExistingDirectory(
            self,
            'Select Saving directory',
            self.directory_box.currentText()))
        if len(directory) == 0: return
        if self.directory_box.findText(directory) == -1:
            self.directory_box.addItem(directory)
        self.directory_box.setCurrentIndex(self.directory_box.findText(directory))


class FocusWidget(QWidget, BaseView):
    '''Widget to do something'''
    parameters_signal = pyqtSignal()
    status_signal = pyqtSignal(str)

    def __init__(self, experiment, parent=None):
        super(FocusWidget, self).__init__(parent=parent)
        uic.loadUi(os.path.join(BASE_DIR_VIEW, 'Focus_Widget.ui'), self)
        self.experiment = experiment

        self.microscope_viewer = CameraViewerWidget(parent=self)
        self.microscope_widget.layout().addWidget(self.microscope_viewer)

        #self.experiment.focus_settings() # Add this
        self.align_button.clicked.connect(self.start_alignment)
        self.continue_button.clicked.connect(self.parameters)

    def start_alignment(self):
        # Turn off top LED
        self.experiment.start_alignment()
        self.status_signal.emit('Aligning laser to fiber center...')
        self.check_timer = QTimer()
        self.check_timer.timeout.connect(self.check_alignment)
        self.check_timer.start(500)
        logger.info('Timer started')

    def check_alignment(self):
        logger.info('Check alignment')
        if self.experiment.aligned: 
            self.status_signal.emit('Alignment done')
            self.check_timer.stop()

    def parameters(self):
        self.parameters_signal.emit()


class ParametersWidget(QWidget, BaseView):
    '''Widget to do something'''
    start_signal = pyqtSignal()

    def __init__(self, experiment, parent=None):
        super(ParametersWidget, self).__init__(parent=parent)
        uic.loadUi(os.path.join(BASE_DIR_VIEW, 'Parameters_Widget.ui'), self)
        self.experiment = experiment

        self.microscope_viewer = CameraViewerWidget(parent=self)
        self.microscope_widget.layout().addWidget(self.microscope_viewer)

        self.start_button.clicked.connect(self.start)

    def start(self):
        self.start_signal.emit()


class MeasurementWidget(QWidget, BaseView):
    '''Widget to do something'''
    quit_signal = pyqtSignal()

    def __init__(self, experiment, parent=None):
        super(MeasurementWidget, self).__init__(parent=parent)
        uic.loadUi(os.path.join(BASE_DIR_VIEW, 'Measurement_Widget.ui'), self)
        self.experiment = experiment

        self.microscope_viewer = CameraViewerWidget(parent=self)
        self.microscope_widget.layout().addWidget(self.microscope_viewer)
        self.waterfall_viewer = CameraViewerWidget(parent=self)
        self.waterfall_widget.layout().addWidget(self.waterfall_viewer)

        self.quit_button.clicked.connect(self.quit)

    def quit(self):
        self.quit_signal.emit()


class CloseWidget(QWidget, BaseView):
    '''Widget to do something'''
    close_signal = pyqtSignal()

    def __init__(self, experiment, parent=None):
        super(CloseWidget, self).__init__(parent=parent)
        uic.loadUi(os.path.join(BASE_DIR_VIEW, 'Close_Widget.ui'), self)
        self.experiment = experiment

        self.close_button.clicked.connect(self.close)

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