#!/usr/bin/env python
"""
Скрипт запуска Django сервера с проверкой занятости порта
"""
import os
import sys
import socket
import subprocess
import signal
import time
from pathlib import Path

# Порт по умолчанию
DEFAULT_PORT = 8000
DEFAULT_HOST = '127.0.0.1'


def is_port_in_use(host, port):
    """Проверяет, занят ли порт"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.settimeout(1)
            result = s.connect_ex((host, port))
            return result == 0
        except Exception:
            return False


def find_process_on_port(port):
    """Находит процесс, использующий указанный порт"""
    try:
        # Для macOS и Linux
        result = subprocess.run(
            ['lsof', '-ti', f':{port}'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().split('\n')
    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
        pass
    
    # Альтернативный способ через netstat (если lsof недоступен)
    try:
        result = subprocess.run(
            ['netstat', '-anv'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            lines = result.stdout.split('\n')
            for line in lines:
                if f':{port}' in line and 'LISTEN' in line:
                    # Пытаемся извлечь PID (может не работать на всех системах)
                    parts = line.split()
                    if len(parts) > 0:
                        return parts
    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
        pass
    
    return None


def kill_process_on_port(port):
    """Останавливает процесс на указанном порту"""
    try:
        # Используем lsof для поиска процесса
        result = subprocess.run(
            ['lsof', '-ti', f':{port}'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0 and result.stdout.strip():
            pids = result.stdout.strip().split('\n')
            for pid in pids:
                try:
                    pid_int = int(pid)
                    print(f"Остановка процесса с PID {pid_int}...")
                    os.kill(pid_int, signal.SIGTERM)
                    # Ждем немного для корректного завершения
                    time.sleep(1)
                    # Если процесс еще жив, принудительно завершаем
                    try:
                        os.kill(pid_int, 0)  # Проверяем, существует ли процесс
                        print(f"Принудительное завершение процесса {pid_int}...")
                        os.kill(pid_int, signal.SIGKILL)
                    except ProcessLookupError:
                        pass  # Процесс уже завершен
                except (ValueError, ProcessLookupError, PermissionError) as e:
                    print(f"Не удалось остановить процесс {pid}: {e}")
            return True
    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError) as e:
        print(f"Ошибка при поиске процесса: {e}")
        return False
    
    return False


def main():
    """Основная функция запуска"""
    # Получаем порт из аргументов или используем по умолчанию
    port = DEFAULT_PORT
    host = DEFAULT_HOST
    
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print(f"Неверный номер порта: {sys.argv[1]}. Используется порт {DEFAULT_PORT}")
            port = DEFAULT_PORT
    
    # Проверяем, занят ли порт
    if is_port_in_use(host, port):
        print(f"⚠️  Порт {port} занят. Попытка остановить процесс...")
        
        if kill_process_on_port(port):
            # Ждем немного, чтобы порт освободился
            time.sleep(2)
            
            # Проверяем еще раз
            if is_port_in_use(host, port):
                print(f"❌ Не удалось освободить порт {port}. Попробуйте остановить процесс вручную.")
                sys.exit(1)
            else:
                print(f"✅ Порт {port} освобожден. Запуск сервера...")
        else:
            print(f"❌ Не удалось автоматически остановить процесс на порту {port}.")
            print(f"   Попробуйте выполнить вручную: lsof -ti :{port} | xargs kill")
            sys.exit(1)
    else:
        print(f"✅ Порт {port} свободен. Запуск сервера...")
    
    # Активируем виртуальное окружение, если оно существует
    venv_python = Path(__file__).parent / 'venv' / 'bin' / 'python'
    if venv_python.exists():
        python_cmd = str(venv_python)
    else:
        python_cmd = sys.executable
    
    # Запускаем Django сервер
    manage_py = Path(__file__).parent / 'manage.py'
    
    if not manage_py.exists():
        print("❌ Файл manage.py не найден!")
        sys.exit(1)
    
    print(f"🚀 Запуск Django сервера на http://{host}:{port}/")
    print("   Нажмите Ctrl+C для остановки\n")
    
    try:
        # Запускаем сервер
        os.chdir(Path(__file__).parent)
        subprocess.run(
            [python_cmd, str(manage_py), 'runserver', f'{host}:{port}'],
            check=True
        )
    except KeyboardInterrupt:
        print("\n\n⏹️  Сервер остановлен пользователем")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Ошибка при запуске сервера: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()

