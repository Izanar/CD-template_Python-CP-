"""add_missing_designer_task_type_enum_values

Revision ID: 9e9f56f0bd6d
Revises: 413b74ca822c
Create Date: 2025-09-23 14:22:04.984123

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "9e9f56f0bd6d"
down_revision = "413b74ca822c"
branch_labels = None
depends_on = None


def upgrade():
    # Добавляем недостающие значения в enum designertasktypeenum
    # Проверяем и добавляем только те значения, которых еще нет
    
    connection = op.get_bind()
    
    # Сначала проверяем, существует ли enum designertasktypeenum
    enum_exists = connection.execute(
        sa.text("SELECT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'designertasktypeenum')")
    ).scalar()
    
    if not enum_exists:
        print("Enum designertasktypeenum does not exist, skipping migration")
        return
    
    # Список всех значений, которые должны быть в enum (из Python DesignerTaskTypeEnum)
    required_values = [
        'creo_video',
        'creo_statika',
        'land_video',
        'land_statika',
        'plashki/uniq',
        'plashki_uniq',  # добавляем и с подчеркиванием для совместимости
        'other'
    ]
    
    # Получаем существующие значения enum
    existing_values = connection.execute(
        sa.text("SELECT unnest(enum_range(NULL::designertasktypeenum))")
    ).fetchall()
    existing_values = [row[0] for row in existing_values]
    
    # Добавляем только те значения, которых еще нет
    for value in required_values:
        if value not in existing_values:
            try:
                connection.execute(sa.text(f"ALTER TYPE designertasktypeenum ADD VALUE '{value}'"))
                print(f"Added enum value: {value}")
            except Exception as e:
                print(f"Failed to add enum value {value}: {e}")


def downgrade():
    # В PostgreSQL нельзя удалить значения из enum, поэтому downgrade не реализован
    # Если нужно откатить изменения, потребуется пересоздать enum
    pass
