from typing import Any, Dict, List

from fastapi import HTTPException


def filter_regular_streams(streams: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    regular_streams = [stream for stream in streams if stream.get("type") == "regular"]
    return [{"id": stream["id"], "name": stream["name"]} for stream in regular_streams]


def get_effective_creo(user_creo: str | None, keitaro_config_creo: str) -> str:
    return user_creo if user_creo is not None else keitaro_config_creo


def update_adname_in_utm_filter(
    stream_data: Dict[str, Any], adname: str, creo: str, action: str = "add"
) -> Dict[str, Any]:
    filters = stream_data.get("filters", [])

    for filter_item in filters:
        payload = filter_item.get("payload", {})
        if filter_item.get("name") == "parameter" and isinstance(payload, dict) and payload.get("name") == creo:
            utm_values = payload["value"]
            if action == "add" and adname not in utm_values:
                utm_values.append(adname)
            elif action == "remove" and adname in utm_values:
                utm_values.remove(adname)
            return stream_data

    raise HTTPException(
        status_code=400,
        detail=f"Filter with creo parameter '{creo}' not found in stream",
    )


def validate_campaign_stream_match(stream_campaign_id: int, requested_campaign_id: int, stream_id: int) -> None:
    if stream_campaign_id != requested_campaign_id:
        raise HTTPException(
            status_code=400,
            detail=f"Stream {stream_id} belongs to campaign {stream_campaign_id}, not {requested_campaign_id}",
        )


def validate_stream_creative_association(creative, stream_id: int, creative_id: int) -> None:
    """Validate that stream is associated with creative."""
    current_streams = creative.streams if hasattr(creative, "streams") else []
    if not any(stream.get("id") == stream_id for stream in current_streams):
        raise HTTPException(status_code=400, detail=f"Stream {stream_id} is not associated with creative {creative_id}")


def handle_keitaro_404_error(e: HTTPException, resource_type: str, resource_id: int) -> None:
    if e.status_code == 404:
        raise HTTPException(status_code=404, detail=f"{resource_type} with id {resource_id} not found")
    raise e


def find_user_by_username(users: List[Dict[str, Any]], username: str) -> Dict[str, Any]:
    for user in users:
        if user.get("login") == username:
            return user
    raise HTTPException(status_code=404, detail=f"User with username '{username}' not found in Keitaro")


def resolve_campaign_group_id(user: Dict[str, Any], username: str, groups: List[Dict[str, Any]]) -> int | None:
    access_data = user.get("access_data", {})
    campaign_groups = access_data.get("campaigns_selected_groups", [])

    if not campaign_groups:
        return None

    if len(campaign_groups) == 1:
        return int(campaign_groups[0])

    for group in groups:
        if group.get("name", "").lower() == username.lower():
            return group.get("id")

    return groups[0].get("id") if groups else None


def filter_campaigns_by_group_id(campaigns: List[Dict[str, Any]], group_id: int) -> List[Dict[str, Any]]:
    return [
        {"id": campaign.get("id"), "name": campaign.get("name")}
        for campaign in campaigns
        if campaign.get("group_id") == group_id
    ]
