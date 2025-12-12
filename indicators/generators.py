"""Утилиты для генерации тестовых данных"""
import random
from decimal import Decimal
from datetime import date, timedelta
from django.utils import timezone
from .models import Indicator, IndicatorValue


def generate_test_values(indicator, start_date, end_date):
    """
    Генерирует тестовые значения для показателя в указанном диапазоне дат
    
    Args:
        indicator: Экземпляр Indicator
        start_date: Начальная дата (date)
        end_date: Конечная дата (date)
    
    Returns:
        int: Количество созданных записей
    """
    if not indicator.min_value or not indicator.max_value:
        raise ValueError("Для генерации данных необходимо указать min_value и max_value")
    
    if start_date > end_date:
        raise ValueError("Начальная дата должна быть меньше или равна конечной")
    
    created_count = 0
    current_date = start_date
    
    while current_date <= end_date:
        # Генерируем случайное значение в диапазоне
        random_value = Decimal(str(random.uniform(
            float(indicator.min_value),
            float(indicator.max_value)
        )))
        
        # Округляем до 4 знаков после запятой
        random_value = random_value.quantize(Decimal('0.0001'))
        
        # Создаем или обновляем значение
        IndicatorValue.objects.update_or_create(
            indicator=indicator,
            date=current_date,
            defaults={'value': random_value}
        )
        
        created_count += 1
        current_date += timedelta(days=1)
    
    return created_count

