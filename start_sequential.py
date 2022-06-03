import logging
import time
import sys
import os

import yaml
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

from sequential.models.experiment import MainSetup
from sequential.models.demo import DemoExperiment
from sequential.views.sequential_window import SequentialMainWindow
from experimentor.lib.log import log_to_screen, get_logger

if __name__ == "__main__":
    logger = get_logger()
    handler = log_to_screen(logger=logger)
    if sys.argv[1] == 'demo':
        experiment = DemoExperiment()
    else:
        experiment = MainSetup()
    experiment.load_configuration('dispertech_test.yml', yaml.UnsafeLoader)
    #executor = experiment.initialize()
    #while executor.running():
    #    time.sleep(.1)

    #QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    #QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    app = QApplication([])
    main_window = SequentialMainWindow(experiment=experiment)
    main_window.show()
    app.exec()
    experiment.finalize()