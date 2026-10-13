"""Project paths and non-secret import configuration."""
from pathlib import Path
from zoneinfo import ZoneInfo
import json

PROJECT = Path(__file__).resolve().parent.parent
CONFIG = json.loads((PROJECT / 'archive.config.json').read_text())
SOURCE = (PROJECT / CONFIG['archive']).resolve()
DESTINATION = (PROJECT / CONFIG['catalog']).resolve()
LOCAL_TIMEZONE = ZoneInfo(CONFIG['timezone'])
FIT_PREVIEW = (PROJECT / CONFIG['fitPreviewRepository']).resolve()
NATIVE_READER = PROJECT / '.build' / 'native-fit-reader'


def as_json(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False).replace('</', '<\\/')
