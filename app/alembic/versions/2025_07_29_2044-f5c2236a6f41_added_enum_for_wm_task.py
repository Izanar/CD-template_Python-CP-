from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "f5c2236a6f41"
down_revision = "0eccb0aa2e35"
branch_labels = None
depends_on = None

def upgrade():
    # Create the ENUM type
    op.execute("""
        CREATE TYPE webmasterprojecttype AS ENUM (
            'PROKLALAND', 'PRELAND', 'LAND', 'QUIZ',
            'WHITE', 'CAMPAIGN_WHITE', 'OTHER'
        )
    """)

    # Add the column with the ENUM type
    op.add_column(
        "web_master_tasks",
        sa.Column(
            "project_type",
            sa.Enum(
                "PROKLALAND", "PRELAND", "LAND", "QUIZ",
                "WHITE", "CAMPAIGN_WHITE", "OTHER",
                name="webmasterprojecttype"
            ),
            nullable=True,
        ),
    )

def downgrade():
    # Drop the column
    op.drop_column("web_master_tasks", "project_type")

    # Drop the ENUM type
    op.execute("DROP TYPE IF EXISTS webmasterprojecttype")
