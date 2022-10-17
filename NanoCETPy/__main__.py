import os
import sys
import pathlib

import yaml
from PyQt5 import QtGui
from PyQt5.QtWidgets import QApplication

from experimentor.lib.log import get_logger, log_to_screen
from .sequential.models.demo import DemoExperiment
from .sequential.models.experiment import MainSetup
from .sequential.views.sequential_window import SequentialMainWindow

# BASE_DIR_VIEW = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BASE_DIR_VIEW = pathlib.Path(__file__).parent


def main():
    logger = get_logger()
    handler = log_to_screen(logger=logger)
    if len(sys.argv) > 1 and sys.argv[1] == 'demo':
        experiment = DemoExperiment()
    else:
        experiment = MainSetup()
    if not (config_filepath := BASE_DIR_VIEW / 'config_user.yml').is_file():
        config_filepath = BASE_DIR_VIEW / 'resources/config_default.yml'
    print(config_filepath.absolute())
    experiment.load_configuration(config_filepath, yaml.UnsafeLoader)

    # QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    # QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    app = QApplication([])
    fontId = QtGui.QFontDatabase.addApplicationFont(str(BASE_DIR_VIEW / 'resources' / 'Roboto-Regular.ttf'))
    families = QtGui.QFontDatabase.applicationFontFamilies(fontId)
    font = QtGui.QFont(families[0])
    app.setFont(font)
    main_window = SequentialMainWindow(experiment=experiment)
    main_window.show()
    app.exec()
    experiment.finalize()
