"""merge_all_heads

Revision ID: 8bac67096ba6
Revises: 3f398689e601, b349a432da9e
Create Date: 2025-09-23 12:44:29.617931

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "8bac67096ba6"
down_revision = ("3f398689e601", "b349a432da9e")
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
