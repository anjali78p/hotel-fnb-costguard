import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import pandas as pd, pytest

@pytest.fixture
def load():
    return lambda name: pd.read_csv(ROOT / "sample_data" / name)
