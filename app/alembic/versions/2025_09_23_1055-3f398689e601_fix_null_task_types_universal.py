"""fix_null_task_types_universal

Revision ID: 3f398689e601
Revises: refactor_task_type_to_enum
Create Date: 2025-09-23 10:55:53.770093

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "3f398689e601"
down_revision = "1d13f13173be"
branch_labels = None
depends_on = None


def upgrade():
    # Универсальная миграция для исправления NULL task_type
    connection = op.get_bind()
    
    # Проверяем, существует ли колонка task_type_id (значит это стейдж)
    result = connection.execute(sa.text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'designer_tasks' 
        AND column_name = 'task_type_id'
    """)).fetchone()
    
    if result:
        # На стейдже/проде: переносим данные из task_type_id с правильным маппингом
        connection.execute(sa.text("""
            UPDATE designer_tasks 
            SET task_type = CASE 
                WHEN tt.name = 'string' THEN 'string'::designertasktypeenum
                WHEN tt.name = 'creo video' THEN 'creo_video'::designertasktypeenum
                WHEN tt.name = 'creo_statika' THEN 'creo_statika'::designertasktypeenum
                WHEN tt.name = 'land video' THEN 'land_video'::designertasktypeenum
                WHEN tt.name = 'statika' THEN 'land_statika'::designertasktypeenum
                WHEN tt.name = 'plashki/uniq' THEN 'plashki/uniq'::designertasktypeenum
                WHEN tt.name = 'other' THEN 'other'::designertasktypeenum
                -- Все остальные типы (TestTask, Test_LB, fast, test estim и т.д.) -> other
                ELSE 'other'::designertasktypeenum
            END
            FROM task_types tt
            WHERE designer_tasks.task_type_id = tt.id
            AND designer_tasks.task_type IS NULL;
        """))
    else:
        # На деве: просто устанавливаем 'other' для NULL значений
        connection.execute(sa.text("""
            UPDATE designer_tasks 
            SET task_type = 'other'::designertasktypeenum
            WHERE task_type IS NULL;
        """))


def downgrade():
    # В downgrade обнуляем task_type для задач, которые были обновлены
    connection = op.get_bind()
    
    # Проверяем, существует ли колонка task_type_id
    result = connection.execute(sa.text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'designer_tasks' 
        AND column_name = 'task_type_id'
    """)).fetchone()
    
    if result:
        # На стейдже: обнуляем task_type для всех задач, которые были обновлены
        connection.execute(sa.text("""
            UPDATE designer_tasks 
            SET task_type = NULL;
        """))
    else:
        # На деве: обнуляем только 'other' значения
        connection.execute(sa.text("""
            UPDATE designer_tasks 
            SET task_type = NULL 
            WHERE task_type = 'other'::designertasktypeenum;
        """))
