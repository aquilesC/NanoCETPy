import logging
import time

import yaml
from PyQt5.QtWidgets import QApplication

from sequential.models.experiment import MainSetup
from sequential.views.sequential_window import SequentialMainWindow
from experimentor.lib.log import log_to_screen, get_logger

if __name__ == "__main__":
    logger = get_logger()
    handler = log_to_screen(logger=logger)
    experiment = MainSetup()
    experiment.load_configuration('dispertech_test.yml', yaml.UnsafeLoader)
    executor = experiment.initialize()
    while executor.running():
        time.sleep(.1)

    app = QApplication([])
    main_window = SequentialMainWindow(experiment=experiment)
    main_window.show()
    app.exec()
    experiment.finalize()