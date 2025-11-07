"""refactor task_type to enum

Revision ID: refactor_task_type_to_enum
Revises: 1d13f13173be
Create Date: 2025-01-27 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'refactor_task_type_to_enum'
down_revision = '1d13f13173be'
branch_labels = None
depends_on = None


def upgrade():
    # Создаем enum тип для DesignerTaskTypeEnum (если его еще нет)
    connection = op.get_bind()
    result = connection.execute(sa.text("""
        SELECT typname 
        FROM pg_type 
        WHERE typname = 'designertasktypeenum'
    """)).fetchone()
    
    if not result:
        task_type_enum = postgresql.ENUM(
            'string', 'creo_video', 'land_video', 'statika', 'plashki/uniq', 'other',
            name='designertasktypeenum'
        )
        task_type_enum.create(connection)
    
    # Добавляем новое поле task_type как enum (если его еще нет)
    connection = op.get_bind()
    result = connection.execute(sa.text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'designer_tasks' 
        AND column_name = 'task_type'
    """)).fetchone()
    
    if not result:
        op.add_column('designer_tasks', sa.Column('task_type', task_type_enum, nullable=True))
    
    # Проверяем, существует ли колонка task_type_id
    result = connection.execute(sa.text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'designer_tasks' 
        AND column_name = 'task_type_id'
    """)).fetchone()
    
    if result:
        # Мигрируем данные из task_type_id в task_type
        # Сначала получаем маппинг из таблицы task_types
        result = connection.execute(sa.text("""
            SELECT id, name FROM task_types WHERE is_inactive = false
        """))
        
        type_mapping = {}
        for row in result:
            type_mapping[row.id] = row.name
        
        # Обновляем task_type на основе task_type_id
        for type_id, type_name in type_mapping.items():
            # Маппим имена из БД в enum значения
            enum_value = None
            if type_name == 'string':
                enum_value = 'string'
            elif type_name == 'creo video':
                enum_value = 'creo_video'
            elif type_name == 'land video':
                enum_value = 'land_video'
            elif type_name == 'statika':
                enum_value = 'statika'
            elif type_name == 'plashki/uniq':
                enum_value = 'plashki/uniq'
            elif type_name == 'other':
                enum_value = 'other'
            
            if enum_value:
                connection.execute(sa.text("""
                    UPDATE designer_tasks 
                    SET task_type = :enum_value 
                    WHERE task_type_id = :type_id
                """), {'enum_value': enum_value, 'type_id': type_id})
        
        # Удаляем старое поле task_type_id и внешний ключ
        op.drop_constraint('designer_tasks_task_type_id_fkey', 'designer_tasks', type_='foreignkey')
        op.drop_column('designer_tasks', 'task_type_id')


def downgrade():
    # Добавляем обратно поле task_type_id
    op.add_column('designer_tasks', sa.Column('task_type_id', sa.INTEGER(), nullable=True))
    
    # Создаем внешний ключ обратно
    op.create_foreign_key('designer_tasks_task_type_id_fkey', 'designer_tasks', 'task_types', ['task_type_id'], ['id'])
    
    # Мигрируем данные обратно из task_type в task_type_id
    connection = op.get_bind()
    
    # Получаем маппинг enum -> id из таблицы task_types
    result = connection.execute(sa.text("""
        SELECT id, name FROM task_types WHERE is_inactive = false
    """))
    
    type_mapping = {}
    for row in result:
        # Маппим имена из БД в enum значения
        if row.name == 'string':
            type_mapping['string'] = row.id
        elif row.name == 'creo video':
            type_mapping['creo_video'] = row.id
        elif row.name == 'land video':
            type_mapping['land_video'] = row.id
        elif row.name == 'statika':
            type_mapping['statika'] = row.id
        elif row.name == 'plashki/uniq':
            type_mapping['plashki/uniq'] = row.id
        elif row.name == 'other':
            type_mapping['other'] = row.id
    
    # Обновляем task_type_id на основе task_type
    for enum_value, type_id in type_mapping.items():
        connection.execute(sa.text("""
            UPDATE designer_tasks 
            SET task_type_id = :type_id 
            WHERE task_type = :enum_value
        """), {'type_id': type_id, 'enum_value': enum_value})
    
    # Удаляем новое поле task_type
    op.drop_column('designer_tasks', 'task_type')
    
    # Удаляем enum тип
    task_type_enum = postgresql.ENUM(
        'string', 'creo_video', 'land_video', 'statika', 'plashki/uniq', 'other',
        name='designertasktypeenum'
    )
    task_type_enum.drop(op.get_bind())
