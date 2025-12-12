#!/usr/bin/env python
"""
Скрипт для создания коммита с версией и автоматическим перечнем изменений
Использование: python scripts/commit_version.py <версия>
Пример: python scripts/commit_version.py 0.1.2
"""
import os
import sys
import subprocess
from pathlib import Path


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


def get_changes_summary():
    """Получает перечень изменений от предыдущего коммита"""
    # Получаем список измененных файлов
    stdout, stderr, code = run_command('git diff --name-status HEAD', check=False)
    
    if code != 0 or not stdout:
        # Если нет изменений в рабочей директории, проверяем staged изменения
        stdout, stderr, code = run_command('git diff --cached --name-status', check=False)
    
    if not stdout:
        return "Нет изменений для коммита"
    
    changes = []
    lines = stdout.split('\n')
    
    for line in lines:
        if not line.strip():
            continue
        
        # Формат: STATUS\tFILE
        parts = line.split('\t', 1)
        if len(parts) == 2:
            status = parts[0].strip()
            file_path = parts[1].strip()
            
            # Расшифровка статуса
            status_map = {
                'A': 'Добавлен',
                'M': 'Изменен',
                'D': 'Удален',
                'R': 'Переименован',
                'C': 'Скопирован'
            }
            
            status_text = status_map.get(status[0], status)
            
            # Для переименований может быть дополнительная информация
            if status.startswith('R'):
                # Формат: R100\told_file\tnew_file
                if len(parts) >= 3:
                    old_file = parts[1].strip()
                    new_file = parts[2].strip()
                    changes.append(f"  - {status_text}: {old_file} → {new_file}")
                else:
                    changes.append(f"  - {status_text}: {file_path}")
            else:
                changes.append(f"  - {status_text}: {file_path}")
    
    return '\n'.join(changes) if changes else "Нет изменений для коммита"


def get_untracked_files():
    """Получает список неотслеживаемых файлов"""
    stdout, stderr, code = run_command('git ls-files --others --exclude-standard', check=False)
    
    if not stdout:
        return []
    
    return [line.strip() for line in stdout.split('\n') if line.strip()]


def create_commit_message(version):
    """Создает сообщение коммита с версией и перечнем изменений"""
    changes = get_changes_summary()
    untracked = get_untracked_files()
    
    message = f"Версия {version}\n\n"
    message += "Изменения:\n"
    message += changes
    
    if untracked:
        message += "\n\nНовые файлы:\n"
        for file in untracked:
            message += f"  - Добавлен: {file}\n"
    
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
    print("📝 Формирование сообщения коммита...")
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
        
        # Предлагаем отправить в репозиторий
        print("\n🚀 Отправить изменения в репозиторий? (y/n): ", end='')
        response = input().strip().lower()
        
        if response in ['y', 'yes', 'да', 'д']:
            print("📤 Отправка изменений...")
            stdout, stderr, code = run_command('git push origin main', check=False)
            if code == 0:
                print("✅ Изменения успешно отправлены в репозиторий!")
            else:
                print(f"⚠️  Ошибка при отправке: {stderr}")
                print("Вы можете отправить вручную: git push origin main")
        else:
            print("💡 Для отправки выполните: git push origin main")
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка при создании коммита: {e.stderr}")
        sys.exit(1)
    finally:
        # Удаляем временный файл
        if temp_file.exists():
            temp_file.unlink()


if __name__ == '__main__':
    main()

