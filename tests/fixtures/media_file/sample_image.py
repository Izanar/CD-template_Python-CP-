import pytest


@pytest.fixture
def sample_image(tmp_path):
    path = tmp_path / "sample.jpg"
    path.write_bytes(b"fake image data")
    return path
