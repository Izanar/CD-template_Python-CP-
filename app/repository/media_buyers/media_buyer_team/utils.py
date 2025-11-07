from operator import attrgetter

from app.schemas.media_buyer import MediaBuyerStatisticsSchema


def sort_vertical_stats(
    stats: list[dict],
    order_by: str | None,
    order_direction: str = "desc",
) -> list[dict]:
    if not order_by:
        return stats

    reverse = order_direction == "desc"

    if order_by == "vertical":
        return sorted(stats, key=lambda s: s["vertical"].lower(), reverse=reverse)

    return sorted(
        stats,
        key=lambda s: sum(team.get(order_by, 0) for team in s["teams"]),
        reverse=reverse,
    )


def sort_buyer_stats(
    stats: list[MediaBuyerStatisticsSchema],
    order_by: str | None,
    order_direction: str = "desc",
) -> list[MediaBuyerStatisticsSchema]:
    if not order_by:
        return stats

    reverse = order_direction == "desc"

    if order_by == "username":
        return sorted(
            stats,
            key=lambda s: (s.user.username if hasattr(s.user, "username") else s.user.get("username", "")).lower(),
            reverse=reverse,
        )

    if order_by == "mean_rating":
        return sorted(
            stats,
            key=lambda s: (
                s.mean_rating in (None, 0),
                -s.mean_rating if reverse and s.mean_rating not in (None, 0) else s.mean_rating,
            ),
            reverse=False,
        )

    if order_by in {"tasks_created", "tasks_completed"}:
        return sorted(
            stats,
            key=lambda s: (
                getattr(s, order_by) == 0,
                -getattr(s, order_by) if reverse else getattr(s, order_by),
            ),
            reverse=False,
        )

    return sorted(stats, key=attrgetter(order_by), reverse=reverse)
