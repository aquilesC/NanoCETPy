import sys
import os
BASE_DIR_VIEW = os.path.dirname(os.path.abspath(__file__))

import yaml
from PyQt5.QtWidgets import QApplication

from sequential.models.experiment import MainSetup
from sequential.models.demo import DemoExperiment
from sequential.views.sequential_window import SequentialMainWindow
from experimentor.lib.log import log_to_screen, get_logger

def main():
    logger = get_logger()
    handler = log_to_screen(logger=logger)
    if len(sys.argv) > 1 and sys.argv[1] == 'demo':
        experiment = DemoExperiment()
    else:
        experiment = MainSetup()
    if os.path.isfile(os.path.join(BASE_DIR_VIEW, 'config_user.yml')):
        config_filepath = 'config_user.yml'
    else:
        config_filepath = 'config_default.yml'
    experiment.load_configuration(config_filepath, yaml.UnsafeLoader)

    #QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    #QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    app = QApplication([])
    main_window = SequentialMainWindow(experiment=experiment)
    main_window.show()
    app.exec()
    experiment.finalize()