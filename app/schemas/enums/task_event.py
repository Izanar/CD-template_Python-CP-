from enum import Enum


class TaskEvent(str, Enum):
    STATUS = "status"  # смена статуса
    TASK = "task"  # create | update | delete
    MEDIA = "media"  # add | update | delete
    EDIT = "edit"  # requested | approved


class TaskAction(str, Enum):
    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"
    ADDED = "added"
    REQUESTED = "requested"
    APPROVED = "approved"
