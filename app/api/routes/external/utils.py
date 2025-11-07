from typing import List

from app.models import Creative


def format_approaches_for_crm(approaches: List[str]) -> str:
    formatted_approaches = []
    for approach in approaches:
        formatted = approach.replace("_", " ").title()
        formatted_approaches.append(formatted)

    return ", ".join(formatted_approaches)


def format_creative_for_crm(creative: Creative) -> dict:
    celebrities_str = None
    if creative.task and creative.task.celebrities_list:
        sorted_celebrities = sorted(creative.task.celebrities_list, key=lambda x: x["id"])
        celebrity_names = [celeb["name"] for celeb in sorted_celebrities]
        celebrities_str = ", ".join(celebrity_names)

    return {
        "id": creative.id,
        "ad_name": creative.ad_name,
        "approaches": format_approaches_for_crm(creative.approaches),
        "celebrities": celebrities_str,
    }
