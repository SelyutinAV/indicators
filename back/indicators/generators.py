"""Утилиты для генерации тестовых данных"""
import random
from decimal import Decimal
from datetime import date, timedelta
from django.utils import timezone
from .models import Indicator, IndicatorValue


def generate_test_values(indicator, start_date, end_date, min_value=None, max_value=None, step='day'):
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
    
    created_count = 0
    current_date = start_date
    
    # Переменная для хранения предыдущего значения (для плавности)
    previous_value = None
    
    while current_date <= end_date:
        # Базовое значение с нормальным распределением вокруг центра диапазона
        # Используем нормальное распределение с отклонением = 1/3 от диапазона
        std_dev = range_size / 3
        base_value = random.gauss(center, std_dev)
        
        # Ограничиваем базовое значение диапазоном
        base_value = max(min_val, min(max_val, base_value))
        
        # Добавляем плавность - новое значение зависит от предыдущего (70% предыдущего + 30% нового)
        if previous_value is not None:
            base_value = 0.7 * previous_value + 0.3 * base_value
        
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
        
        # Сохраняем для следующей итерации
        previous_value = float(final_value)
        
        # Создаем или обновляем значение
        IndicatorValue.objects.update_or_create(
            indicator=indicator,
            date=current_date,
            defaults={'value': random_value}
        )
        
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

