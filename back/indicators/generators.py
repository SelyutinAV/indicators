"""Утилиты для генерации тестовых данных"""
import random
from decimal import Decimal
from datetime import date, timedelta
from itertools import product
from django.utils import timezone
from .models import Indicator, IndicatorValue


def generate_test_values(indicator, start_date, end_date, min_value=None, max_value=None, step='day', dictionary_items=None):
    """
    Генерирует тестовые значения для показателя в указанном диапазоне дат
    с поддержкой случайных всплесков и отклонений
    
    Args:
        indicator: Экземпляр Indicator
        start_date: Начальная дата (date)
        end_date: Конечная дата (date)
        min_value: Минимальное значение для генерации (Decimal или None)
        max_value: Максимальное значение для генерации (Decimal или None)
        step: Шаг генерации - 'day' (день) или 'month' (месяц)
        dictionary_items: Список конкретных элементов справочников для генерации (опционально)
                         Если None, генерирует для всех комбинаций
    
    Returns:
        int: Количество созданных записей
    """
    # Используем переданные значения или значения из модели
    if min_value is None:
        min_value = indicator.min_value
    if max_value is None:
        max_value = indicator.max_value
    
    if min_value is None or max_value is None:
        raise ValueError("Для генерации данных необходимо указать min_value и max_value")
    
    if start_date > end_date:
        raise ValueError("Начальная дата должна быть меньше или равна конечной")
    
    min_val = float(min_value)
    max_val = float(max_value)
    range_size = max_val - min_val
    center = (min_val + max_val) / 2
    
    # Определяем комбинации элементов справочников
    dictionary_combinations = []
    
    if indicator.dictionaries.exists():
        # Получаем все активные элементы для каждого справочника через промежуточную модель
        from .models import IndicatorDictionary
        indicator_dicts = IndicatorDictionary.objects.filter(
            indicator=indicator,
            dictionary__is_active=True
        ).select_related('dictionary').prefetch_related('dictionary__items')
        
        dictionaries_list = [ind_dict.dictionary for ind_dict in indicator_dicts]
        required_dicts = {ind_dict.dictionary.id: ind_dict.is_required for ind_dict in indicator_dicts}
        
        if dictionary_items:
            # Если указаны конкретные элементы, используем их
            dictionary_combinations = [tuple(dictionary_items)]
        else:
            # Генерируем все комбинации элементов справочников
            dict_items_lists = []
            for dictionary in dictionaries_list:
                items = list(dictionary.items.filter(is_active=True))
                if items:
                    dict_items_lists.append(items)
            
            if dict_items_lists:
                # Создаем все комбинации через product
                dictionary_combinations = list(product(*dict_items_lists))
            else:
                # Нет активных элементов - создаем пустую комбинацию
                dictionary_combinations = [tuple()]
        
        # Если есть справочники с is_required=False, добавляем также вариант без разреза
        # Но если все справочники обязательные, не добавляем вариант без разреза
        if required_dicts and not all(required_dicts.values()):
            # Добавляем вариант без разреза только если не все справочники обязательные
            dictionary_combinations.append(tuple())
    else:
        # Нет справочников - генерируем без разреза
        dictionary_combinations = [tuple()]
    
    created_count = 0
    current_date = start_date
    
    # Словарь для хранения предыдущих значений для каждой комбинации справочников (для плавности)
    # Ключ - tuple из ID элементов справочников, значение - предыдущее значение
    previous_values = {}
    
    while current_date <= end_date:
        # Генерируем значения для каждой комбинации справочников
        # Для каждой комбинации генерируем ОТДЕЛЬНОЕ случайное значение
        for dict_items_tuple in dictionary_combinations:
            # Создаем ключ для этой комбинации справочников
            dict_key = tuple(sorted([item.id for item in dict_items_tuple])) if dict_items_tuple else tuple()
            
            # Базовое значение с нормальным распределением вокруг центра диапазона
            # Используем нормальное распределение с отклонением = 1/3 от диапазона
            std_dev = range_size / 3
            base_value = random.gauss(center, std_dev)
            
            # Ограничиваем базовое значение диапазоном
            base_value = max(min_val, min(max_val, base_value))
            
            # Добавляем плавность - новое значение зависит от предыдущего для ЭТОЙ комбинации (70% предыдущего + 30% нового)
            if dict_key in previous_values:
                base_value = 0.7 * previous_values[dict_key] + 0.3 * base_value
            
            # Случайные всплески (10% вероятность)
            if random.random() < 0.1:
                # Всплеск может быть вверх или вниз
                spike_direction = random.choice([-1, 1])
                # Размер всплеска от 20% до 50% от диапазона
                spike_size = range_size * random.uniform(0.2, 0.5)
                base_value += spike_direction * spike_size
            
            # Случайные отклонения (30% вероятность меньших отклонений)
            if random.random() < 0.3:
                deviation = range_size * random.uniform(-0.15, 0.15)
                base_value += deviation
            
            # Ограничиваем финальное значение диапазоном
            final_value = max(min_val, min(max_val, base_value))
            # Конвертируем в Decimal и округляем в зависимости от типа значения
            if indicator.value_type == 'integer':
                # Для целых значений округляем до целого числа
                random_value = Decimal(str(round(final_value))).quantize(Decimal('1'))
            else:
                # Для дробных значений округляем до 4 знаков после запятой
                random_value = Decimal(str(final_value)).quantize(Decimal('0.0001'))
        
            # Получаем множество ID элементов справочников для проверки уникальности
            dict_items_set = set(item.id for item in dict_items_tuple) if dict_items_tuple else set()
            
            # Ищем существующее значение с такой же комбинацией справочников
            existing_values = IndicatorValue.objects.filter(
                indicator=indicator,
                date=current_date
            ).prefetch_related('dictionary_items')
            
            value_obj = None
            for existing_value in existing_values:
                existing_items_set = set(item.id for item in existing_value.dictionary_items.all())
                if existing_items_set == dict_items_set:
                    value_obj = existing_value
                    break
            
            # Если не нашли, создаем новое значение
            if value_obj is None:
                value_obj = IndicatorValue.objects.create(
                    indicator=indicator,
                    date=current_date,
                    value=random_value
                )
            else:
                # Обновляем существующее значение
                value_obj.value = random_value
                value_obj.save()
            
            # Устанавливаем элементы справочников
            if dict_items_tuple:
                value_obj.dictionary_items.set(dict_items_tuple)
            else:
                value_obj.dictionary_items.clear()
            
            # Сохраняем для следующей итерации для ЭТОЙ комбинации справочников
            previous_values[dict_key] = float(final_value)
            
            created_count += 1
        
        # Переходим к следующей дате в зависимости от шага
        if step == 'month':
            # Переход на следующий месяц
            if current_date.month == 12:
                current_date = date(current_date.year + 1, 1, 1)
            else:
                current_date = date(current_date.year, current_date.month + 1, 1)
        else:
            # Шаг по дням (по умолчанию)
            current_date += timedelta(days=1)
    
    return created_count

