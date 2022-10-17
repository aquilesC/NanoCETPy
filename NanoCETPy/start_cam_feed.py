import time

import yaml
from PyQt5.QtWidgets import QApplication

from experimentor.lib.log import get_logger, log_to_screen
from .alignment.models.experiment import CamSetup
from .alignment.views.cam_window import CamWindow

if __name__ == "__main__":
    logger = get_logger()
    handler = log_to_screen(logger=logger)#, level=logging.DEBUG)
    experiment = CamSetup()
    experiment.load_configuration('cam_feed.yml', yaml.UnsafeLoader)
    executor = experiment.initialize()
    while executor.running():
        time.sleep(.1)

    app = QApplication([])
    cam_window = CamWindow(experiment)
    cam_window.show()
    app.exec()
    experiment.finalize()