import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestGetDesignerTasksOrdering:
    endpoint = "/media_buyer/designer/tasks"

    async def test_sort_by_created_by_username(self, client: AsyncClient, designer_user, new_task):
        headers = {"Authorization": f"Bearer {designer_user['access_token']}"}

        resp_asc = await client.get(
            self.endpoint,
            params={"order_by": "created_by_username", "order_direction": "asc", "limit": 20},
            headers=headers,
        )
        assert resp_asc.status_code == 200
        usernames_asc = []
        for task in resp_asc.json()["items"]:
            username = task["created_by_user"]["username"].lower() if task.get("created_by_user") else None
            usernames_asc.append(username)
        assert usernames_asc == sorted(usernames_asc, key=lambda x: (x is None, x))

        resp_desc = await client.get(
            self.endpoint,
            params={"order_by": "created_by_username", "order_direction": "desc", "limit": 20},
            headers=headers,
        )
        assert resp_desc.status_code == 200
        usernames_desc = []
        for task in resp_desc.json()["items"]:
            username = task["created_by_user"]["username"].lower() if task.get("created_by_user") else None
            usernames_desc.append(username)
        assert usernames_desc == sorted(usernames_desc, key=lambda x: (x is not None, x), reverse=True)

    async def test_sort_by_assigned_to_username(self, client: AsyncClient, designer_user, new_task):
        headers = {"Authorization": f"Bearer {designer_user['access_token']}"}

        resp_asc = await client.get(
            self.endpoint,
            params={"order_by": "assigned_to_username", "order_direction": "asc", "limit": 20},
            headers=headers,
        )
        assert resp_asc.status_code == 200
        assigned_usernames_asc = []
        for task in resp_asc.json()["items"]:
            username = task["assigned_to_user"]["username"].lower() if task.get("assigned_to_user") else None
            assigned_usernames_asc.append(username)
        assert assigned_usernames_asc == sorted(assigned_usernames_asc, key=lambda x: (x is None, x))

        resp_desc = await client.get(
            self.endpoint,
            params={"order_by": "assigned_to_username", "order_direction": "desc", "limit": 20},
            headers=headers,
        )
        assert resp_desc.status_code == 200
        assigned_usernames_desc = []
        for task in resp_desc.json()["items"]:
            username = task["assigned_to_user"]["username"].lower() if task.get("assigned_to_user") else None
            assigned_usernames_desc.append(username)
        assert assigned_usernames_desc == sorted(
            assigned_usernames_desc, key=lambda x: (x is not None, x), reverse=True
        )

    async def test_sort_by_assigned_to_rating(self, client: AsyncClient, designer_user, new_task):
        headers = {"Authorization": f"Bearer {designer_user['access_token']}"}

        resp_asc = await client.get(
            self.endpoint,
            params={"order_by": "assigned_to_rating", "order_direction": "asc", "limit": 20},
            headers=headers,
        )
        assert resp_asc.status_code == 200
        ratings_asc = []
        for task in resp_asc.json()["items"]:
            evaluations = task.get("evaluations", [])
            rating = sum(eval["rating"] for eval in evaluations) / len(evaluations) if evaluations else None
            ratings_asc.append(rating)
        assert ratings_asc == sorted(ratings_asc, key=lambda x: (x is None, x))

        resp_desc = await client.get(
            self.endpoint,
            params={"order_by": "assigned_to_rating", "order_direction": "desc", "limit": 20},
            headers=headers,
        )
        assert resp_desc.status_code == 200
        ratings_desc = []
        for task in resp_desc.json()["items"]:
            evaluations = task.get("evaluations", [])
            rating = sum(eval["rating"] for eval in evaluations) / len(evaluations) if evaluations else None
            ratings_desc.append(rating)
        assert ratings_desc == sorted(ratings_desc, key=lambda x: (x is not None, x), reverse=True)

    async def test_sort_by_buyer_team_vertical(self, client: AsyncClient, designer_user, new_task):
        headers = {"Authorization": f"Bearer {designer_user['access_token']}"}

        resp_asc = await client.get(
            self.endpoint,
            params={"order_by": "vertical", "order_direction": "asc", "limit": 20},
            headers=headers,
        )
        assert resp_asc.status_code == 200
        verticals_asc = []
        for task in resp_asc.json()["items"]:
            vertical = task["vertical"] if task.get("vertical") else None
            verticals_asc.append(vertical)
        assert verticals_asc == sorted(verticals_asc, key=lambda x: (x is None, x))

        resp_desc = await client.get(
            self.endpoint,
            params={"order_by": "vertical", "order_direction": "desc", "limit": 20},
            headers=headers,
        )
        assert resp_desc.status_code == 200
        verticals_desc = []
        for task in resp_desc.json()["items"]:
            vertical = task["vertical"] if task.get("vertical") else None
            verticals_desc.append(vertical)
        assert verticals_desc == sorted(verticals_desc, key=lambda x: (x is not None, x), reverse=True)

    async def test_sort_by_deadline(self, client: AsyncClient, designer_user, new_task):
        headers = {"Authorization": f"Bearer {designer_user['access_token']}"}

        resp_asc = await client.get(
            self.endpoint,
            params={"order_by": "deadline", "order_direction": "asc", "limit": 20},
            headers=headers,
        )
        assert resp_asc.status_code == 200
        deadlines_asc = [task["deadline"] for task in resp_asc.json()["items"]]
        assert deadlines_asc == sorted(deadlines_asc, key=lambda x: (x is None, x))

        resp_desc = await client.get(
            self.endpoint,
            params={"order_by": "deadline", "order_direction": "desc", "limit": 20},
            headers=headers,
        )
        assert resp_desc.status_code == 200
        deadlines_desc = [task["deadline"] for task in resp_desc.json()["items"]]
        assert deadlines_desc == sorted(deadlines_desc, key=lambda x: (x is not None, x), reverse=True)
