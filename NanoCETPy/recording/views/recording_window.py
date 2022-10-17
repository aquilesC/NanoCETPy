import os
import time

import numpy as np

BASE_DIR_VIEW = os.path.dirname(os.path.abspath(__file__))

from PyQt5 import uic, QtGui
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QMainWindow

from experimentor.lib.log import get_logger
from experimentor.views.base_view import BaseView
from experimentor.views.camera.camera_viewer_widget import CameraViewerWidget

logger = get_logger(__name__)

class WaterfallWindow(QMainWindow, BaseView):
    """ Window for displaying fiber core and recording waterfall image
    """
    def __init__(self, experiment):
        super(WaterfallWindow, self).__init__()
        uic.loadUi(os.path.join(BASE_DIR_VIEW, 'Waterfall_Window.ui'), self)

        self.experiment = experiment

        self.camera_viewer = CameraViewerWidget(parent=self)
        self.camera_widget.layout().addWidget(self.camera_viewer)
        self.waterfall_viewer = CameraViewerWidget(parent=self)
        self.waterfall_widget.layout().addWidget(self.waterfall_viewer)

        self.connect_to_action(self.ROI_button.clicked, self.experiment.find_ROI)
        self.connect_to_action(self.save_button.clicked, self.experiment.save_waterfall)
        self.stop_button.clicked.connect(self.experiment.toggle_active)

        while self.experiment.camera_microscope.config['exposure'] is None:
            time.sleep(.1)
        
        self.update_image_timer = QTimer()
        self.update_image_timer.timeout.connect(self.update_image)
        self.update_image_timer.start(50)
        self.update_processed_image_timer = QTimer()
        self.update_processed_image_timer.timeout.connect(self.update_waterfall)
        self.update_processed_image_timer.start(50)

    def update_image(self):
        img = self.experiment.get_latest_image()
        if np.sum(img) == None: 
            img = np.zeros((800,800))
            img[100:700,100:700] += np.ones((600,600))
        self.camera_viewer.update_image(img)

    def update_waterfall(self):
        img = self.experiment.get_waterfall_image()
        self.waterfall_viewer.update_image(img)

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        logger.info('Alignment Window Closed')
        self.update_image_timer.stop()
        super().closeEvent(a0)