#!/usr/bin/env python
"""
Скрипт для создания коммита с версией и функциональным описанием изменений
Использование: python scripts/commit_version.py <версия>
Пример: python scripts/commit_version.py 0.1.2
"""
import os
import sys
import subprocess
import re
from pathlib import Path
from collections import defaultdict


def run_command(cmd, check=True):
    """Выполняет команду и возвращает результат"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            check=check
        )
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except subprocess.CalledProcessError as e:
        return e.stdout.strip(), e.stderr.strip(), e.returncode


def get_changed_files():
    """Получает список измененных файлов"""
    # Получаем список измененных файлов
    stdout, stderr, code = run_command('git diff --name-status HEAD', check=False)
    
    if code != 0 or not stdout:
        # Если нет изменений в рабочей директории, проверяем staged изменения
        stdout, stderr, code = run_command('git diff --cached --name-status', check=False)
    
    if not stdout:
        return []
    
    files = []
    lines = stdout.split('\n')
    
    for line in lines:
        if not line.strip():
            continue
        
        # Формат: STATUS\tFILE или R100\tOLD\tNEW
        parts = line.split('\t')
        if len(parts) >= 2:
            status = parts[0].strip()
            file_path = parts[1].strip() if len(parts) > 1 else ''
            
            files.append({
                'status': status[0],  # A, M, D, R
                'path': file_path,
                'full_status': status
            })
    
    return files


def analyze_functional_changes(files):
    """Анализирует изменения и формирует функциональное описание"""
    changes = defaultdict(list)
    
    for file_info in files:
        path = file_info['path']
        status = file_info['status']
        
        # Анализ по типам файлов и путям
        if 'migrations' in path and path.endswith('.py'):
            if status == 'A':
                # Извлекаем номер миграции и имя
                match = re.search(r'(\d{4})_(\w+)\.py', path)
                if match:
                    migration_num = match.group(1)
                    migration_name = match.group(2)
                    changes['Модели данных'].append(f"Добавлена миграция {migration_num}: {migration_name}")
                else:
                    changes['Модели данных'].append("Добавлена новая миграция базы данных")
        
        elif 'models.py' in path:
            if status == 'A':
                changes['Модели данных'].append("Добавлены новые модели данных")
            elif status == 'M':
                changes['Модели данных'].append("Обновлены модели данных")
        
        elif 'views.py' in path:
            if status == 'A':
                changes['API/Представления'].append("Добавлены новые представления")
            elif status == 'M':
                changes['API/Представления'].append("Обновлены представления")
        
        elif 'urls.py' in path:
            if status == 'A' or status == 'M':
                changes['API/Представления'].append("Обновлена маршрутизация")
        
        elif 'admin.py' in path:
            if status == 'A' or status == 'M':
                changes['Административный интерфейс'].append("Обновлен административный интерфейс")
        
        elif 'management/commands' in path:
            cmd_name = Path(path).stem
            if status == 'A':
                changes['Команды управления'].append(f"Добавлена команда: {cmd_name}")
            elif status == 'M':
                changes['Команды управления'].append(f"Обновлена команда: {cmd_name}")
        
        elif 'templates' in path and path.endswith('.html'):
            template_name = Path(path).stem
            if status == 'A':
                # Определяем тип шаблона по имени
                if 'import' in template_name.lower():
                    changes['Пользовательский интерфейс'].append("Добавлен интерфейс импорта данных")
                elif 'clear' in template_name.lower():
                    changes['Пользовательский интерфейс'].append("Добавлен интерфейс очистки данных")
                elif 'create' in template_name.lower() or 'form' in template_name.lower():
                    changes['Пользовательский интерфейс'].append("Добавлена форма создания/редактирования")
                elif 'detail' in template_name.lower():
                    changes['Пользовательский интерфейс'].append("Добавлена страница детального просмотра")
                elif 'index' in template_name.lower() or 'list' in template_name.lower():
                    changes['Пользовательский интерфейс'].append("Добавлена страница списка")
                else:
                    changes['Пользовательский интерфейс'].append(f"Добавлен новый шаблон: {template_name}")
            elif status == 'M':
                changes['Пользовательский интерфейс'].append(f"Обновлен шаблон: {template_name}")
        
        elif 'static' in path or 'css' in path or 'js' in path:
            if status == 'A':
                changes['Пользовательский интерфейс'].append("Добавлены/обновлены стили или скрипты")
            elif status == 'M':
                changes['Пользовательский интерфейс'].append("Обновлены стили или скрипты")
        
        elif 'excel_parser' in path or 'parser' in path.lower():
            if status == 'A':
                changes['Функциональность'].append("Добавлен парсер для импорта данных из Excel")
            elif status == 'M':
                changes['Функциональность'].append("Обновлен парсер для импорта данных")
        
        elif 'formula_parser' in path:
            if status == 'A' or status == 'M':
                changes['Функциональность'].append("Обновлен парсер формул для агрегатных показателей")
        
        elif 'generators' in path:
            if status == 'A' or status == 'M':
                changes['Функциональность'].append("Обновлена генерация тестовых данных")
        
        elif 'requirements.txt' in path:
            if status == 'A' or status == 'M':
                changes['Зависимости'].append("Обновлены зависимости проекта")
        
        elif 'settings.py' in path:
            if status == 'A' or status == 'M':
                changes['Конфигурация'].append("Обновлены настройки проекта")
        
        elif 'README' in path or 'docs' in path:
            if status == 'A' or status == 'M':
                changes['Документация'].append("Обновлена документация")
        
        elif status == 'D':
            file_name = Path(path).name
            changes['Удалено'].append(f"Удален файл: {file_name}")
    
    return changes


def format_functional_changes(changes):
    """Форматирует функциональные изменения в читаемый вид"""
    if not changes:
        return "Нет изменений для коммита"
    
    sections_order = [
        'Модели данных',
        'API/Представления',
        'Пользовательский интерфейс',
        'Административный интерфейс',
        'Функциональность',
        'Команды управления',
        'Конфигурация',
        'Зависимости',
        'Документация',
        'Удалено'
    ]
    
    result = []
    for section in sections_order:
        if section in changes and changes[section]:
            result.append(f"{section}:")
            for change in changes[section]:
                result.append(f"  - {change}")
            result.append("")
    
    # Добавляем остальные секции, если есть
    for section, items in changes.items():
        if section not in sections_order and items:
            result.append(f"{section}:")
            for change in items:
                result.append(f"  - {change}")
            result.append("")
    
    return '\n'.join(result).strip()


def create_commit_message(version):
    """Создает сообщение коммита с версией и функциональным описанием изменений"""
    files = get_changed_files()
    
    if not files:
        return f"Версия {version}\n\nНет изменений для коммита"
    
    changes = analyze_functional_changes(files)
    functional_desc = format_functional_changes(changes)
    
    message = f"Версия {version}\n\n"
    message += "Изменения:\n"
    message += functional_desc
    
    return message


def main():
    """Основная функция"""
    if len(sys.argv) < 2:
        print("❌ Ошибка: не указана версия")
        print("Использование: python scripts/commit_version.py <версия>")
        print("Пример: python scripts/commit_version.py 0.1.2")
        sys.exit(1)
    
    version = sys.argv[1]
    
    # Проверяем, что мы в git репозитории
    stdout, stderr, code = run_command('git rev-parse --git-dir', check=False)
    if code != 0:
        print("❌ Ошибка: не найден git репозиторий")
        sys.exit(1)
    
    # Проверяем статус
    stdout, stderr, code = run_command('git status --porcelain', check=False)
    if not stdout:
        print("⚠️  Нет изменений для коммита")
        sys.exit(0)
    
    # Добавляем все изменения
    print("📦 Добавление изменений в индекс...")
    stdout, stderr, code = run_command('git add -A', check=True)
    
    # Формируем сообщение коммита
    print("📝 Анализ изменений и формирование функционального описания...")
    commit_message = create_commit_message(version)
    
    print(f"\n📋 Сообщение коммита:\n{'-'*60}")
    print(commit_message)
    print(f"{'-'*60}\n")
    
    # Создаем коммит
    print(f"💾 Создание коммита версии {version}...")
    
    # Сохраняем сообщение во временный файл
    temp_file = Path('/tmp/git_commit_msg.txt')
    temp_file.write_text(commit_message, encoding='utf-8')
    
    try:
        stdout, stderr, code = run_command(
            f'git commit -F {temp_file}',
            check=True
        )
        print(f"✅ Коммит создан успешно!")
        print(stdout)
        
        # Автоматически отправляем в репозиторий (для неинтерактивного режима)
        print("\n📤 Отправка изменений в репозиторий...")
        stdout, stderr, code = run_command('git push origin main', check=False)
        if code == 0:
            print("✅ Изменения успешно отправлены в репозиторий!")
        else:
            print(f"⚠️  Ошибка при отправке: {stderr}")
            print("Вы можете отправить вручную: git push origin main")
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка при создании коммита: {e.stderr}")
        sys.exit(1)
    finally:
        # Удаляем временный файл
        if temp_file.exists():
            temp_file.unlink()


if __name__ == '__main__':
    main()
