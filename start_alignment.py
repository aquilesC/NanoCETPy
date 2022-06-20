import logging
import time

import yaml
from PyQt5.QtWidgets import QApplication

from alignment.models.experiment import AlignmentSetup
from alignment.views.cam_window import AlignmentWindow
from experimentor.lib.log import log_to_screen, get_logger

if __name__ == "__main__":
    logger = get_logger()
    handler = log_to_screen(logger=logger)
    experiment = AlignmentSetup()
    experiment.load_configuration('cam_feed.yml', yaml.UnsafeLoader)
    executor = experiment.initialize()
    while executor.running():
        time.sleep(.1)
    experiment.electronics.top_led = 0

    app = QApplication([])
    cam_window = AlignmentWindow(experiment)
    cam_window.show()
    app.exec()
    experiment.finalize()