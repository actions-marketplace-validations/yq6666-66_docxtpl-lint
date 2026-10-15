import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from make_fixtures import build


@pytest.fixture(scope="session")
def fx(tmp_path_factory):
    return build(tmp_path_factory.mktemp("fixtures"))
