import time

import yaml
from PyQt5.QtWidgets import QApplication

from experimentor.lib.log import get_logger, log_to_screen
from .recording.models.experiment import RecordingSetup
from .recording.views.recording_window import WaterfallWindow

if __name__ == "__main__":
    logger = get_logger()
    handler = log_to_screen(logger=logger)
    experiment = RecordingSetup()
    experiment.load_configuration('cam_feed.yml', yaml.UnsafeLoader)
    executor = experiment.initialize()
    while executor.running():
        time.sleep(.1)

    app = QApplication([])
    cam_window = WaterfallWindow(experiment)
    cam_window.show()
    app.exec()
    experiment.finalize()