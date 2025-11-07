import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestExternalCreativeAPI:
    async def test_get_creative_success(
        self, client: AsyncClient, headers, test_creative_with_data, cleanup_test_creatives
    ):
        response = await client.post(
            "/api/v1/external/creative",
            json={"ad_name": "test_creative_api"},
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert "id" in data
        assert "ad_name" in data
        assert "approaches" in data

        assert data["ad_name"] == "test_creative_api"
        assert data["approaches"] == "Arrest, Cry, Check, Charges"

    async def test_get_creative_minimal(
        self, client: AsyncClient, headers, test_creative_minimal, cleanup_test_creatives
    ):
        response = await client.post(
            "/api/v1/external/creative",
            json={"ad_name": "test_creative_minimal"},
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["ad_name"] == "test_creative_minimal"
        assert data["approaches"] == ""

    async def test_get_creative_not_found(self, client: AsyncClient, headers):
        response = await client.post(
            "/api/v1/external/creative",
            json={"ad_name": "nonexistent_ad"},
            headers=headers,
        )

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "nonexistent_ad" in data["detail"]

    async def test_get_creative_invalid_api_key(self, client: AsyncClient, invalid_headers):
        response = await client.post(
            "/api/v1/external/creative",
            json={"ad_name": "test_ad6"},
            headers=invalid_headers,
        )

        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
        assert "Invalid API key" in data["detail"]

    async def test_get_creative_missing_api_key(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/external/creative",
            json={"ad_name": "test_ad6"},
        )

        assert response.status_code == 422

    async def test_get_creative_missing_ad_name(self, client: AsyncClient, headers):
        response = await client.post(
            "/api/v1/external/creative",
            json={},
            headers=headers,
        )

        assert response.status_code == 422

    async def test_get_creative_invalid_json(self, client: AsyncClient, headers):
        response = await client.post(
            "/api/v1/external/creative",
            json={"ad_name": None},
            headers=headers,
        )

        assert response.status_code == 422

    async def test_get_creative_wrong_method(self, client: AsyncClient, headers):
        """Тест с неправильным HTTP методом."""
        response = await client.get(
            "/api/v1/external/creative",
            headers=headers,
        )

        assert response.status_code == 405

    async def test_approaches_ordering_consistency(
        self, client: AsyncClient, headers, test_creative_with_data, cleanup_test_creatives
    ):
        response = await client.post(
            "/api/v1/external/creative",
            json={"ad_name": "test_creative_api"},
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()

        approaches = data["approaches"].split(", ")
        expected_order = ["Arrest", "Cry", "Check", "Charges"]
        assert approaches == expected_order

    async def test_response_format(self, client: AsyncClient, headers, test_creative_with_data, cleanup_test_creatives):
        response = await client.post(
            "/api/v1/external/creative",
            json={"ad_name": "test_creative_api"},
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data["id"], int)
        assert isinstance(data["ad_name"], str)
        assert isinstance(data["approaches"], str)

        if data["approaches"]:
            assert "," in data["approaches"]
