"""Merge branches

Revision ID: 1f623c63f0c4
Revises: f490433d731d, e8c0d3d8aa23
Create Date: 2025-07-14 11:14:28.569621

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "1f623c63f0c4"
down_revision = ("f490433d731d", "e8c0d3d8aa23")
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
