"""remove_string_task_type_and_migrate_to_other

Revision ID: 413b74ca822c
Revises: 8bac67096ba6
Create Date: 2025-09-23 13:13:45.673641

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "413b74ca822c"
down_revision = "8bac67096ba6"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    
    result = connection.execute(sa.text("""
        UPDATE designer_tasks 
        SET task_type = 'other'::designertasktypeenum
        WHERE task_type = 'string'::designertasktypeenum
    """))
    
    
    


def downgrade():
    pass
    
