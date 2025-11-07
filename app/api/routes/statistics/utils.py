from collections import Counter
from operator import attrgetter

from app.models import Designer, DesignerTaskStatus
from app.schemas.designers.statistics import (
    DesignerPointsStatistic,
    DesignerStatistic,
    DesignerStatisticShortResponseSchema,
)


def build_designer_statistics(
    designers: list[Designer],
) -> list[DesignerStatistic]:
    statistics = []

    for designer in designers:
        task_statuses = [task.task_status.value for task in designer.assigned_tasks if not task.is_deleted]
        counts = Counter(task_statuses)

        statistics.append(
            DesignerStatistic(
                designer=DesignerStatisticShortResponseSchema(
                    id=designer.id,
                    username=designer.user.username,
                    user_role=designer.user.role.name,
                ),
                designer_team=designer.designer_team,
                waiting_to_start_count=counts.get(DesignerTaskStatus.WAITING_TO_START.value, 0),
                in_progress_count=counts.get(DesignerTaskStatus.IN_PROGRESS.value, 0),
                requested_changes_count=counts.get(DesignerTaskStatus.REQUESTED_CHANGES.value, 0),
                under_tl_review_count=counts.get(DesignerTaskStatus.UNDER_TL_REVIEW.value, 0),
                under_buyer_review_count=counts.get(DesignerTaskStatus.UNDER_BUYER_REVIEW.value, 0),
                completed_count=counts.get(DesignerTaskStatus.COMPLETED.value, 0),
            )
        )

    return statistics


def build_designer_points_statistics(designer_data: list[tuple[Designer, int, int]]) -> list[DesignerPointsStatistic]:
    return [
        DesignerPointsStatistic(
            designer=DesignerStatisticShortResponseSchema(
                id=designer.id,
                username=designer.user.username,
                user_role=designer.user.role.name,
            ),
            designer_team=designer.designer_team,
            completed_tasks=completed_tasks,
            total_points=total_points,
            mean_rating=mean_rating,
        )
        for designer, completed_tasks, total_points, mean_rating in designer_data
    ]


def sort_designer_statistics(
    stats: list["DesignerStatistic"],
    order_by: str | None,
    order_direction: str = "desc",
) -> list["DesignerStatistic"]:
    if order_by == "username":
        reverse = order_direction == "desc"
        return sorted(
            stats,
            key=lambda s: (s.designer.username or "").lower(),
            reverse=reverse,
        )

    if not order_by:
        return sorted(stats, key=lambda s: (s.designer.username or "").lower())

    key_name = f"{order_by}_count"
    reverse = order_direction == "desc"
    return sorted(stats, key=attrgetter(key_name), reverse=reverse)
