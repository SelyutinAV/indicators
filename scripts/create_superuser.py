#!/usr/bin/env python
"""
Скрипт для создания суперпользователя Django
"""
import os
import sys
from pathlib import Path

# Добавляем путь к back в PYTHONPATH
project_root = Path(__file__).parent.parent
back_path = project_root / 'back'
sys.path.insert(0, str(back_path))

# Меняем рабочую директорию на back
os.chdir(back_path)

import django

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'indicators_project.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

# Дефолтные учетные данные
DEFAULT_USERNAME = 'admin'
DEFAULT_EMAIL = 'admin@example.com'
DEFAULT_PASSWORD = 'admin123'

def create_superuser():
    """Создает суперпользователя, если его еще нет"""
    username = DEFAULT_USERNAME
    email = DEFAULT_EMAIL
    password = DEFAULT_PASSWORD
    
    if User.objects.filter(username=username).exists():
        print(f"⚠️  Пользователь '{username}' уже существует.")
        print("   Если забыли пароль, измените его через:")
        print("   python manage.py changepassword admin")
        return False
    
    try:
        User.objects.create_superuser(
            username=username,
            email=email,
            password=password
        )
        print("="*60)
        print("✅ Суперпользователь успешно создан!")
        print("="*60)
        print(f"👤 Логин: {username}")
        print(f"📧 Email: {email}")
        print(f"🔑 Пароль: {password}")
        print("="*60)
        print("\n⚠️  ВНИМАНИЕ: Это дефолтный пароль!")
        print("   Рекомендуется изменить его после первого входа.")
        print("   Команда для смены: python manage.py changepassword admin")
        print()
        return True
    except Exception as e:
        print(f"❌ Ошибка при создании суперпользователя: {e}")
        return False

if __name__ == '__main__':
    create_superuser()

