"""Парсер для импорта показателей из Excel файлов"""
import openpyxl
from decimal import Decimal, InvalidOperation
from django.core.exceptions import ValidationError
from .models import Indicator, Unit, ImportTemplate


def parse_indicators_from_excel(file_path, template=None, **kwargs):
    """
    Парсит показатели из Excel файла
    
    Args:
        file_path: Путь к Excel файлу
        template: Экземпляр ImportTemplate (опционально)
        **kwargs: Переопределение параметров шаблона:
            - sheet_name: Название листа
            - indicator_column: Колонка с показателями
            - start_row: Строка начала данных
    
    Returns:
        dict: {
            'success': bool,
            'created': int,
            'updated': int,
            'errors': list,
            'warnings': list
        }
    """
    result = {
        'success': True,
        'created': 0,
        'updated': 0,
        'errors': [],
        'warnings': []
    }
    
    # Получаем параметры из шаблона или kwargs
    if template:
        sheet_name = kwargs.get('sheet_name', template.sheet_name or None)
        indicator_column = kwargs.get('indicator_column', template.indicator_column or 'M')
        start_row = kwargs.get('start_row', template.start_row or 2)
    else:
        sheet_name = kwargs.get('sheet_name')
        indicator_column = kwargs.get('indicator_column', 'M')
        start_row = kwargs.get('start_row', 2)
    
    try:
        # Открываем файл
        workbook = openpyxl.load_workbook(file_path, data_only=True)
        
        # Выбираем лист
        if sheet_name:
            if sheet_name not in workbook.sheetnames:
                result['errors'].append(f'Лист "{sheet_name}" не найден в файле')
                result['success'] = False
                workbook.close()
                return result
            sheet = workbook[sheet_name]
        else:
            sheet = workbook.active
        
        # Используем единицу измерения "Штука" по умолчанию для всех импортируемых показателей
        # Пользователь сможет изменить единицу измерения для каждого показателя вручную после импорта
        unit, created = Unit.objects.get_or_create(
            name='Штука',
            defaults={'symbol': 'шт', 'description': 'Единица измерения по умолчанию'}
        )
        
        # Проходим по строкам колонки
        row = start_row
        indicators_processed = set()
        
        while True:
            cell = sheet[f'{indicator_column}{row}']
            indicator_name = cell.value
            
            # Если ячейка пустая, прекращаем обработку
            if indicator_name is None or (isinstance(indicator_name, str) and not indicator_name.strip()):
                break
            
            # Очищаем название от лишних пробелов
            if isinstance(indicator_name, str):
                indicator_name = indicator_name.strip()
            
            # Пропускаем пустые строки
            if not indicator_name:
                row += 1
                continue
            
            # Пропускаем дубликаты в рамках одного файла
            if indicator_name in indicators_processed:
                result['warnings'].append(f'Пропущен дубликат: {indicator_name}')
                row += 1
                continue
            
            indicators_processed.add(indicator_name)
            
            try:
                # Пытаемся найти существующий показатель
                indicator, created = Indicator.objects.get_or_create(
                    name=indicator_name,
                    defaults={
                        'indicator_type': 'atomic',
                        'unit': unit,  # Используется единица "Штука" по умолчанию, пользователь может изменить вручную
                        'description': f'Импортирован из Excel файла'
                    }
                )
                
                if created:
                    result['created'] += 1
                else:
                    result['updated'] += 1
                    result['warnings'].append(f'Показатель "{indicator_name}" уже существует, обновлен')
                
            except Exception as e:
                result['errors'].append(f'Ошибка при обработке "{indicator_name}": {str(e)}')
                result['success'] = False
            
            row += 1
        
        workbook.close()
        
    except FileNotFoundError:
        result['errors'].append(f'Файл не найден: {file_path}')
        result['success'] = False
    except Exception as e:
        result['errors'].append(f'Ошибка при чтении файла: {str(e)}')
        result['success'] = False
    
    return result

