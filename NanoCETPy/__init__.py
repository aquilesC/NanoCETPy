from pathlib import Path

# with open('_version.py', 'r', encoding='utf-8-sig') as f:
with open(Path(__file__).parent / '_version.py', 'r', encoding='utf-8-sig') as f:
    while True:
        version_line = f.readline()
        if version_line.startswith('__version__'):
            break

    __version__ = version_line.split('=')[1].strip().replace("'", "")

BASE_PATH = Path(__file__).parent
USER_CONFIG_PATH = Path.home() / '.dispertech' / 'nanoCET_config.yml'
