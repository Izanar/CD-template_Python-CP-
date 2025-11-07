"""refactor existing task history

Revision ID: 5d2bda10c7d7
Revises: 1f623c63f0c4
Create Date: 2025-07-15 11:58:54.657175
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "5d2bda10c7d7"
down_revision = "1f623c63f0c4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()


    statuses = [
        "WAITING_TO_ASSIGN",
        "WAITING_TO_START",
        "IN_PROGRESS",
        "UNDER_TL_REVIEW",
        "REQUESTED_CHANGES",
        "UNDER_BUYER_REVIEW",
        "COMPLETED",
        "DRAFT",
    ]

    conn.execute(
        sa.text(
            """
            UPDATE designer_task_history
            SET event = 'status'
            WHERE event = 'create'
              AND event_info = ANY(:statuses)
            """
        ),
        {"statuses": statuses},
    )

    conn.execute(
        sa.text(
            """
            UPDATE designer_task_history
            SET event = 'task',
                event_info = 'created'
            WHERE event = 'create'
              AND event_info <> ALL(:statuses)
            """
        ),
        {"statuses": statuses},
    )

    conn.execute(
        sa.text(
            """
            UPDATE designer_task_history
            SET event = 'task',
                event_info = 'updated'
            WHERE event = 'update'
            """
        )
    )

    media_map = {
        "media_add": "added",
        "media_update": "updated",
        "media_delete": "deleted",
    }
    for old_event, action in media_map.items():
        conn.execute(
            sa.text(
                """
                UPDATE designer_task_history
                SET event = 'media',
                    event_info = :action
                WHERE event = :old_event
                """
            ),
            {"action": action, "old_event": old_event},
        )

    edit_map = {
        "edit_requested": "requested",
        "edit_approved": "approved",
    }
    for old_event, action in edit_map.items():
        conn.execute(
            sa.text(
                """
                UPDATE designer_task_history
                SET event = 'edit',
                    event_info = :action
                WHERE event = :old_event
                """
            ),
            {"action": action, "old_event": old_event},
        )

    conn.execute(
        sa.text(
            """
            UPDATE designer_task_history
            SET event_info = upper(trim(regexp_replace(event_info,
                                                       '^Status changed to\\s+', '',
                                                       'i')))
            WHERE event = 'status'
              AND event_info ILIKE 'Status changed to %'
            """
        )
    )

    conn.execute(
        sa.text(
            """
            UPDATE designer_task_history
            SET active = TRUE
            WHERE active IS FALSE
            """
        )
    )


def downgrade() -> None:
    """Нельзя безопасно откатить — старая форма данных утрачена."""
    raise RuntimeError("Irreversible migration")
