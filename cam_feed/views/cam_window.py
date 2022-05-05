import os
import time
import numpy as np

BASE_DIR_VIEW = os.path.dirname(os.path.abspath(__file__))

from PyQt5 import uic, QtGui
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QMainWindow, QStatusBar

from experimentor import Q_
from experimentor.lib.log import get_logger
from experimentor.views.base_view import BaseView
from experimentor.views.camera.camera_viewer_widget import CameraViewerWidget

logger = get_logger(__name__)

class AlignmentWindow(QMainWindow, BaseView):
    """ Window for testing the alignment procedure. 
    Left display for camera image, right one for observing the current processing underlyig the algorithm.
    Button to start the procedure and further controls for interim troubleshooting.
    CAUTION: always stop live acquisition before triggering alignment!
    """
    def __init__(self, experiment):
        super(AlignmentWindow, self).__init__()
        uic.loadUi(os.path.join(BASE_DIR_VIEW, 'Alignment_Window.ui'), self)

        self.experiment = experiment

        self.camera_viewer = CameraViewerWidget(parent=self)
        self.camera_widget.layout().addWidget(self.camera_viewer)
        self.processing_viewer = CameraViewerWidget(parent=self)
        self.processing_widget.layout().addWidget(self.processing_viewer)
        #self.camera_viewer.clicked_on_image.connect(self.mouse_clicked)

        self.connect_to_action(self.start_button.clicked, self.experiment.start_alignment)
        self.connect_to_action(self.live_button.clicked, lambda: self.experiment.toggle_live(self.experiment.camera_fiber))
        self.connect_to_action(self.live_button_2.clicked, lambda: self.experiment.toggle_live(self.experiment.camera_microscope))
        self.connect_to_action(self.laser_button.clicked, self.experiment.toggle_laser)
        self.stop_button.clicked.connect(self.experiment.toggle_active)
        self.linesave_button.clicked.connect(self.experiment.save_image)
        self.laser_process_button.clicked.connect(self.experiment.process_laser)
        self.up_button.clicked.connect(lambda: self.move_piezo(1,1,self.experiment.config['electronics']['vertical_axis']))
        self.down_button.clicked.connect(lambda: self.move_piezo(1,0,self.experiment.config['electronics']['vertical_axis']))
        self.left_button.clicked.connect(lambda: self.move_piezo(1,1,self.experiment.config['electronics']['horizontal_axis']))
        self.right_button.clicked.connect(lambda: self.move_piezo(1,0,self.experiment.config['electronics']['horizontal_axis']))
        self.plus_button.clicked.connect(lambda: self.move_piezo(30,1,3))
        self.minus_button.clicked.connect(lambda: self.move_piezo(30,0,3))

        while self.experiment.camera_fiber.config['exposure'] is None:
            time.sleep(.1)
        #self.camera_gain_line.setText(str(self.experiment.camera.gain))
        #self.camera_exposure_line.setText("{:~}".format(Q_(self.experiment.camera.exposure)))
        
        self.update_image_timer = QTimer()
        self.update_image_timer.timeout.connect(self.update_image)
        self.update_image_timer.start(50)
        self.update_processed_image_timer = QTimer()
        self.update_processed_image_timer.timeout.connect(self.update_processed_image)
        self.update_processed_image_timer.start(200)

    def update_image(self):
        img = self.experiment.get_latest_image()
        if np.sum(img) == None: 
            img = np.zeros((800,800))
            img[100:700,100:700] += np.ones((600,600))
        self.camera_viewer.update_image(img)

    def update_processed_image(self):
        img = self.experiment.get_processed_image()
        self.processing_viewer.update_image(img)
    
    def update_camera(self):
        """ Updates the properties of the camera. """

        logger.info('Updating parameters of the camera')
        self.experiment.camera.config.update({
            'exposure': Q_(self.camera_exposure_line.text()),
            'gain': float(self.camera_gain_line.text()),
        })
        self.experiment.camera.config.apply_all()

    def move_piezo(self, speed, direction, axis):
        self.experiment.electronics.move_piezo(speed, direction, axis)

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        logger.info('Alignment Window Closed')
        self.update_image_timer.stop()
        super().closeEvent(a0)


class CamWindow(QMainWindow, BaseView):
    """ Window to start and stop live view and snap single image from camera
    """
    def __init__(self, experiment):
        super(CamWindow, self).__init__()
        uic.loadUi(os.path.join(BASE_DIR_VIEW, 'Cam_Window.ui'), self)

        self.experiment = experiment

        self.camera_viewer = CameraViewerWidget(parent=self)
        self.camera_widget.layout().addWidget(self.camera_viewer)
        #self.camera_viewer.clicked_on_image.connect(self.mouse_clicked)

        self.connect_to_action(self.snap_button.clicked, self.experiment.snap_image)
        self.connect_to_action(self.live_button.clicked, self.experiment.toggle_live)
        self.apply_button.clicked.connect(self.update_camera)
        
        while self.experiment.camera.config['exposure'] is None:
            time.sleep(.1)
        self.camera_gain_line.setText(str(self.experiment.camera.gain))
        self.camera_exposure_line.setText("{:~}".format(Q_(self.experiment.camera.exposure)))
        
        self.update_image_timer = QTimer()
        self.update_image_timer.timeout.connect(self.update_image)
        #self.update_ui()
        self.update_image_timer.start(50)

    def update_image(self):
        """ gets latest camera image and raturns a test image if camera image is None
        """
        img = self.experiment.get_latest_image()
        if np.sum(img) == None: 
            img = np.zeros((800,800))
            img[100:700,100:700] += np.ones((600,600))
        self.camera_viewer.update_image(img)
    
    def update_camera(self):
        """ Updates the properties of the camera. """

        logger.info('Updating parameters of the camera')
        self.experiment.camera.config.update({
            'exposure': Q_(self.camera_exposure_line.text()),
            'gain': float(self.camera_gain_line.text()),
        })
        self.experiment.camera.config.apply_all()

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        logger.info('Cam Window Closed')
        self.update_image_timer.stop()
        super().closeEvent(a0)