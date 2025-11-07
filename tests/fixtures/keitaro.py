import pytest_asyncio
from httpx import AsyncClient


@pytest_asyncio.fixture
async def keitaro_config(admin_user, client: AsyncClient) -> dict:
    resp = await client.post(
        "/admin/keitaro/config",
        json={
            "name": "Test Keitaro Config",
            "api_key": "test_api_key_123",
            "base_url": "https://test.keitaro.com",
            "creo": "test_creo_123",
        },
        headers={"Authorization": f"Bearer {admin_user['access_token']}"},
    )
    assert resp.status_code == 201
    return resp.json()


@pytest_asyncio.fixture
async def keitaro_config_2(admin_user, client: AsyncClient) -> dict:
    resp = await client.post(
        "/admin/keitaro/config",
        json={
            "name": "Test Keitaro Config 2",
            "api_key": "test_api_key_456",
            "base_url": "https://test2.keitaro.com",
            "creo": "test_creo_456",
        },
        headers={"Authorization": f"Bearer {admin_user['access_token']}"},
    )
    assert resp.status_code == 201
    return resp.json()


@pytest_asyncio.fixture
async def multiple_keitaro_configs(keitaro_config, keitaro_config_2) -> list[dict]:
    return [keitaro_config, keitaro_config_2]
