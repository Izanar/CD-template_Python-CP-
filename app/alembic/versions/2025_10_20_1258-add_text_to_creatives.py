"""add_text_to_creatives

Revision ID: a2c5f4e1b9cd
Revises: d452d25177f0
Create Date: 2025-10-20 12:58:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a2c5f4e1b9cd"
down_revision = "d452d25177f0"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("creatives", sa.Column("text", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("creatives", "text")


