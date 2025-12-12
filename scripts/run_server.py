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


def is_process_running(pid):
    """Проверяет, запущен ли процесс"""
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # Процесс существует, но нет прав


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
            pids = [pid.strip() for pid in result.stdout.strip().split('\n') if pid.strip()]
            killed_any = False
            
            for pid_str in pids:
                try:
                    pid_int = int(pid_str)
                    
                    # Пропускаем системные процессы (обычно PID < 100)
                    if pid_int < 100:
                        print(f"⚠️  Пропущен системный процесс с PID {pid_int}")
                        continue
                    
                    print(f"🛑 Остановка процесса с PID {pid_int}...")
                    
                    # Сначала пытаемся мягко завершить
                    try:
                        os.kill(pid_int, signal.SIGTERM)
                        killed_any = True
                    except ProcessLookupError:
                        print(f"   Процесс {pid_int} уже завершен")
                        continue
                    except PermissionError:
                        print(f"   ⚠️  Нет прав для остановки процесса {pid_int}, пробуем принудительно...")
                        try:
                            os.kill(pid_int, signal.SIGKILL)
                            killed_any = True
                        except (ProcessLookupError, PermissionError):
                            print(f"   ❌ Не удалось остановить процесс {pid_int}")
                            continue
                    
                    # Ждем завершения процесса
                    for _ in range(5):  # Ждем до 5 секунд
                        time.sleep(1)
                        if not is_process_running(pid_int):
                            print(f"   ✅ Процесс {pid_int} успешно остановлен")
                            break
                    else:
                        # Процесс все еще работает, принудительно завершаем
                        if is_process_running(pid_int):
                            print(f"   🔨 Принудительное завершение процесса {pid_int}...")
                            try:
                                os.kill(pid_int, signal.SIGKILL)
                                time.sleep(1)
                                if not is_process_running(pid_int):
                                    print(f"   ✅ Процесс {pid_int} принудительно завершен")
                                else:
                                    print(f"   ⚠️  Процесс {pid_int} все еще работает (возможно, системный)")
                            except (ProcessLookupError, PermissionError) as e:
                                print(f"   ⚠️  Не удалось принудительно завершить: {e}")
                    
                except ValueError:
                    print(f"   ⚠️  Неверный PID: {pid_str}")
                    continue
                except Exception as e:
                    print(f"   ❌ Ошибка при остановке процесса {pid_str}: {e}")
                    continue
            
            return killed_any
            
    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError) as e:
        print(f"❌ Ошибка при поиске процесса: {e}")
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
            print("⏳ Ожидание освобождения порта...")
            for attempt in range(5):
                time.sleep(1)
                if not is_port_in_use(host, port):
                    print(f"✅ Порт {port} освобожден. Запуск сервера...")
                    break
            else:
                # Порт все еще занят после попыток - пробуем следующий порт
                print(f"⚠️  Порт {port} все еще занят после попыток остановки.")
                print(f"   Попробуйте выполнить вручную: lsof -ti :{port} | xargs kill -9")
                
                # Пробуем следующие порты
                original_port = port
                for attempt in range(5):
                    port = original_port + attempt + 1
                    if not is_port_in_use(host, port):
                        print(f"🔄 Используем свободный порт {port}...")
                        break
                else:
                    print(f"❌ Не удалось найти свободный порт в диапазоне {original_port}-{port}")
                    sys.exit(1)
        else:
            print(f"❌ Не удалось автоматически остановить процесс на порту {port}.")
            print(f"   Попробуйте выполнить вручную: lsof -ti :{port} | xargs kill -9")
            
            # Пробуем следующие порты
            original_port = port
            for attempt in range(5):
                port = original_port + attempt + 1
                if not is_port_in_use(host, port):
                    print(f"🔄 Используем свободный порт {port}...")
                    break
            else:
                print(f"❌ Не удалось найти свободный порт в диапазоне {original_port}-{port}")
                sys.exit(1)
    else:
        print(f"✅ Порт {port} свободен. Запуск сервера...")
    
    # Активируем виртуальное окружение, если оно существует
    project_root = Path(__file__).parent.parent
    venv_python = project_root / 'venv' / 'bin' / 'python'
    if venv_python.exists():
        python_cmd = str(venv_python)
    else:
        python_cmd = sys.executable
    
    # Запускаем Django сервер
    manage_py = project_root / 'back' / 'manage.py'
    
    if not manage_py.exists():
        print("❌ Файл manage.py не найден!")
        sys.exit(1)
    
    print(f"\n{'='*60}")
    print(f"🚀 Запуск Django сервера на http://{host}:{port}/")
    print(f"📊 Админка: http://{host}:{port}/admin/")
    print(f"{'='*60}")
    print("   Нажмите Ctrl+C для остановки\n")
    
    try:
        # Запускаем сервер из директории back
        os.chdir(project_root / 'back')
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

