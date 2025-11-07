from app.schemas.enums.task_event import TaskAction, TaskEvent


def handle_event_info(
    event: TaskEvent,
    action: TaskAction | None = None,
    new_status: str | None = None,
) -> str:
    if event is TaskEvent.STATUS:
        return new_status or "unknown"
    return f"{event.value}_{action.value}" if action else event.value
