import pathlib

with open('_version.py', 'r', encoding='utf-8-sig') as f:
    while True:
        version_line = f.readline()
        if version_line.startswith('__version__'):
            break

    __version__ = version_line.split('=')[1].strip().replace("'", "")

BASE_PATH = pathlib.Path(__file__).parent
