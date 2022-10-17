import json
import time

import h5py
import numpy as np
import zmq

from experimentor import Q_
from experimentor.core.meta import ExperimentorProcess


class MovieSaver(ExperimentorProcess):
    def __init__(self, file, max_memory, frame_rate, saving_event, url, topic='', metadata=None):
        super().__init__()
        self.file = file
        self.max_memory = max_memory
        self.saving_event = saving_event
        self.frame_rate = frame_rate
        self.topic = topic
        self.url = url
        self.stop_keyword = "MovieSaverStop"
        if metadata is None:
            metadata = {}
        for key, value in metadata.items():
            if isinstance(value, Q_):
                metadata[key] = str(value)
        self.metadata = metadata
        self.start()

    def run(self) -> None:
        self.logger.info('Starting logger')
        context = zmq.Context()
        socket = context.socket(zmq.SUB)
        socket.connect(self.url)
        socket.setsockopt(zmq.SUBSCRIBE, self.topic.encode('utf-8'))

        with h5py.File(self.file, "a") as f:
            g = f.create_group('data')
            i = 0
            j = 0
            first = True
            while not self.saving_event.is_set():
                event = socket.poll(0)
                if not event:
                    time.sleep(.005)
                    continue
                topic = socket.recv_string()
                metadata = socket.recv_json(flags=0)
                msg = socket.recv(flags=0, copy=True, track=False)
                if not metadata.get('numpy', False):
                    self.logger.info('Got stop keyword')
                    break

                buf = memoryview(msg)
                img = np.frombuffer(buf, dtype=metadata['dtype'])
                img = img.reshape(metadata['shape'], order="F").copy()

                # Using byte order F gives the proper shape, but it is camera-dependent
                # This works fine for Basler, but need to keep an eye for the future
                # TODO: standardize the byte-order for camera frames, are they always Fortran?

                if first:  # First time it runs, creates the dataset
                    x = img.shape[0]
                    y = img.shape[1]
                    allocate = int(self.max_memory / img.nbytes * 1024 * 1024)
                    self.logger.info(f'Allocation {allocate} frames in HDF5 file')
                    d = np.zeros((x, y, allocate), dtype=img.dtype)
                    dset = g.create_dataset('timelapse', (x, y, allocate), maxshape=(x, y, None),
                                            compression='gzip', compression_opts=1,
                                            dtype=img.dtype)  # The images are going to be stacked along the z-axis.
                    first = False
                    meta = {
                        'fps': self.frame_rate,
                        'start': time.time(),
                        'allocate': allocate,
                    }
                    meta.update(self.metadata)
                    metadata = json.dumps(meta)
                    mdset = g.create_dataset('metadata', data=metadata.encode("utf-8", "ignore"))

                d[:, :, i] = img
                i += 1

                if i == allocate:
                    dset[:, :, j:j + allocate] = d
                    dset.resize((x, y, j + 2*allocate))
                    d = np.zeros((x, y, allocate), dtype=img.dtype)
                    i = 0
                    j += allocate

            if i != 0:
                self.logger.info(f'Saving last {i} frames')
                dset[:, :, j:j + i] = d[:, :, :i]

            meta.update({
                'end': time.time(),
                'frames': j+i,
                'allocate': allocate,
            })
            metadata = json.dumps(meta)
            mdset[()] = metadata.encode("utf-8", "ignore")
            self.logger.info(f'Saver finished, total acquired frames: {j+i}')


class WaterfallSaver(ExperimentorProcess):
    def __init__(self, file, max_memory, frame_rate, saving_event, url, topic='', metadata=None):
        super().__init__()
        self.file = file
        self.max_memory = max_memory
        self.saving_event = saving_event
        self.frame_rate = frame_rate
        self.topic = topic
        self.url = url
        self.stop_keyword = "MovieSaverStop"
        if metadata is None:
            metadata = {}
        for key, value in metadata.items():
            if isinstance(value, Q_):
                metadata[key] = str(value)
        self.metadata = metadata
        self.start()

    def run(self) -> None:
        self.logger.info('Starting logger')
        context = zmq.Context()
        socket = context.socket(zmq.SUB)
        socket.connect(self.url)
        socket.setsockopt(zmq.SUBSCRIBE, self.topic.encode('utf-8'))

        with h5py.File(self.file, "a") as f:
            g = f.create_group('data')
            i = 0
            j = 0
            first = True
            while not self.saving_event.is_set():
                event = socket.poll(0)
                if not event:
                    time.sleep(.005)
                    continue
                topic = socket.recv_string()
                metadata = socket.recv_json(flags=0)
                msg = socket.recv(flags=0, copy=True, track=False)
                if not metadata.get('numpy', False):
                    self.logger.info('Got stop keyword')
                    break

                buf = memoryview(msg)
                img = np.frombuffer(buf, dtype=metadata['dtype'])
                img = img.reshape(metadata['shape'], order="F").copy()
                img = np.sum(img, axis=1) #CHECK THIS

                # Using byte order F gives the proper shape, but it is camera-dependent
                # This works fine for Basler, but need to keep an eye for the future
                # TODO: standardize the byte-order for camera frames, are they always Fortran?

                if first:  # First time it runs, creates the dataset
                    shape = img.shape[0]
                    allocate = int(self.max_memory / img.nbytes * 1024 * 1024)
                    self.logger.info(f'Allocation {allocate} frames in HDF5 file')
                    d = np.zeros((shape, allocate), dtype=img.dtype)
                    dset = g.create_dataset('timelapse', (shape, allocate), maxshape=(shape, None),
                                            compression='gzip', compression_opts=1,
                                            dtype=img.dtype)  # The images are going to be stacked along the z-axis.
                    first = False
                    meta = {
                        'fps': self.frame_rate,
                        'start': time.time(),
                        'allocate': allocate,
                    }
                    meta.update(self.metadata)
                    metadata = json.dumps(meta)
                    mdset = g.create_dataset('metadata', data=metadata.encode("utf-8", "ignore"))

                d[:, i] = img
                i += 1

                if i == allocate:
                    dset[:, j:j + allocate] = d
                    dset.resize((shape, j + 2*allocate))
                    d = np.zeros((shape, allocate), dtype=img.dtype)
                    i = 0
                    j += allocate

            if i != 0:
                self.logger.info(f'Saving last {i} frames')
                dset[:, j:j + i] = d[:, :i]

            meta.update({
                'end': time.time(),
                'frames': j+i,
                'allocate': allocate,
            })
            metadata = json.dumps(meta)
            mdset[()] = metadata.encode("utf-8", "ignore")
            self.logger.info(f'Saver finished, total acquired frames: {j+i}')

