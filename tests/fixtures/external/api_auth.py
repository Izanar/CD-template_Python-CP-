import pytest


@pytest.fixture
def valid_api_key():
    return "R4dhqkVNPhFbz_X0bLVwXKsyQKwftSJzVBt_id2bCnw"


@pytest.fixture
def invalid_api_key():
    return "invalid_api_key"


@pytest.fixture
def headers(valid_api_key):
    return {"X-API-Key": valid_api_key}


@pytest.fixture
def invalid_headers(invalid_api_key):
    return {"X-API-Key": invalid_api_key}
