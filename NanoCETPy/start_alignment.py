import os
import sys
import time

import yaml
from PyQt5.QtWidgets import QApplication

from experimentor.lib.log import get_logger, log_to_screen
from .alignment.models.experiment import AlignmentSetup
from .alignment.views.cam_window import AlignmentWindow, CartridgeWindow

if __name__ == "__main__":
    logger = get_logger()
    handler = log_to_screen(logger=logger)
    experiment = AlignmentSetup()
    experiment.load_configuration('cam_feed.yml', yaml.UnsafeLoader)
    executor = experiment.initialize()
    while executor.running():
        time.sleep(.1)

    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    app = QApplication([])
    if len(sys.argv) > 1 and sys.argv[1] == 'cartridge':
        cam_window = CartridgeWindow(experiment)
    else:
        cam_window = AlignmentWindow(experiment)
    cam_window.show()
    app.exec()
    experiment.finalize()