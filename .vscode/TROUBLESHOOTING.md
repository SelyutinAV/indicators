# Решение проблем с задачами в Cursor

Если задачи не отображаются в "Tasks: Run Task", попробуйте:

## 1. Перезагрузить окно Cursor

- Нажмите `Cmd+Shift+P` (macOS) или `Ctrl+Shift+P` (Windows/Linux)
- Введите "Developer: Reload Window"
- Нажмите Enter

## 2. Проверить расположение файла

Убедитесь, что файл `.vscode/tasks.json` находится в корне проекта:
```
models/
├── .vscode/
│   └── tasks.json  ← должен быть здесь
├── back/
├── front/
└── ...
```

## 3. Проверить формат JSON

Файл должен быть валидным JSON. Проверьте через:
```bash
python3 -m json.tool .vscode/tasks.json
```

## 4. Альтернативный способ запуска

Если задачи все еще не видны, используйте терминал напрямую:

```bash
# Запуск сервера
python scripts/run_server.py

# Или через manage.py
cd back
python manage.py runserver
```

## 5. Проверить настройки Cursor

Убедитесь, что в настройках Cursor включена поддержка задач:
- Откройте настройки (Cmd+, или Ctrl+,)
- Найдите "tasks"
- Убедитесь, что задачи включены

## 6. Создать задачи вручную

Если ничего не помогает, можно создать задачу вручную:
1. `Cmd+Shift+P` → "Tasks: Configure Task"
2. Выберите "Create tasks.json file from template"
3. Выберите "Others"
4. Добавьте свои задачи

