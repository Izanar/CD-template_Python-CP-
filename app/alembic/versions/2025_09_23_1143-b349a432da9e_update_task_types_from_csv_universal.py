"""update_task_types_from_csv_universal

Revision ID: b349a432da9e
Revises: refactor_task_type_to_enum
Create Date: 2025-09-23 11:43:59.880693

"""

import csv
import os
from pathlib import Path

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "b349a432da9e"
down_revision = "refactor_task_type_to_enum"
branch_labels = None
depends_on = None


def upgrade():
    # Универсальная миграция для обновления task_type из CSV файлов
    connection = op.get_bind()
    
    # Проверяем, существует ли колонка task_type
    result = connection.execute(sa.text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'designer_tasks' 
        AND column_name = 'task_type'
    """)).fetchone()
    
    if not result:
        print("⚠️ Колонка task_type не существует, пропускаем обновление")
        return
    
    # Определяем среду по переменной окружения
    env = os.getenv('ENV', 'dev')
    
    # Определяем имя файла в зависимости от среды
    if env == 'main':
        csv_filename = 'task_types_mapping_prod.csv'
    elif env == 'stage':
        csv_filename = 'task_types_mapping.csv'
    else:
        csv_filename = None  # На деве файла нет
    
    if csv_filename:
        # Ищем файл в разных возможных местах
        possible_paths = [
            Path(csv_filename),  # В текущей директории
            Path('/home/helper/HelperCoreBack') / csv_filename,  # На проде/стейдже
            Path('/app') / csv_filename,  # В контейнере
        ]
        
        csv_file = None
        for path in possible_paths:
            if path.exists():
                csv_file = path
                break
        
        if csv_file:
            print(f"📖 Найден CSV файл: {csv_file}")
            
            # Читаем CSV и обновляем задачи
            updates = []
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    task_id = int(row['id'])
                    enum_value = row['enum_value']
                    updates.append((task_id, enum_value))
            
            print(f"📊 Найдено {len(updates)} задач для обновления")
            
            # Обновляем задачи
            updated_count = 0
            for task_id, enum_value in updates:
                try:
                    connection.execute(sa.text("""
                        UPDATE designer_tasks 
                        SET task_type = :enum_value::designertasktypeenum 
                        WHERE id = :task_id
                    """), {'enum_value': enum_value, 'task_id': task_id})
                    updated_count += 1
                except Exception as e:
                    print(f"❌ Ошибка при обновлении задачи {task_id}: {e}")
            
            print(f"🎉 Обновлено {updated_count} задач из CSV файла")
        else:
            print(f"⚠️ CSV файл {csv_filename} не найден, пропускаем обновление")
    else:
        print("🔧 На деве: устанавливаем 'other' для NULL значений")
        # На деве просто устанавливаем 'other' для NULL значений
        connection.execute(sa.text("""
            UPDATE designer_tasks 
            SET task_type = 'other'::designertasktypeenum
            WHERE task_type IS NULL
        """))


def downgrade():
    # В downgrade обнуляем task_type для всех задач
    connection = op.get_bind()
    connection.execute(sa.text("""
        UPDATE designer_tasks 
        SET task_type = NULL
    """))
