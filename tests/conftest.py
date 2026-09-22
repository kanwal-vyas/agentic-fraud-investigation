import pytest
from pathlib import Path
import sys

# Ensure src/ is on python path
src_dir = Path(__file__).resolve().parent.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

@pytest.fixture
def raw_data_dir():
    return Path("HHGOA_IEEE")

@pytest.fixture
def sample_data_dir():
    return Path("data/sample")
