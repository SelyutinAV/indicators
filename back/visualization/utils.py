from datetime import date, timedelta
from django.db.models import Q
from indicators.models import Indicator, IndicatorValue
import json


def apply_dictionary_filters(values_query, dictionary_filters):
    """
    Применяет фильтры по справочникам к запросу значений показателей.
    
    Args:
        values_query: QuerySet значений показателей
        dictionary_filters: dict с фильтрами вида {dictionary_id: [item_id1, item_id2, ...]}
    
    Returns:
        Отфильтрованный QuerySet
    """
    if not dictionary_filters or not isinstance(dictionary_filters, dict):
        return values_query
    
    # Применяем фильтры: для каждого справочника фильтруем по выбранным элементам
    for dict_id, item_ids in dictionary_filters.items():
        if item_ids and isinstance(item_ids, list):
            try:
                # Преобразуем ID в int, если они строки
                item_ids = [int(item_id) for item_id in item_ids if item_id]
                if item_ids:
                    values_query = values_query.filter(dictionary_items__id__in=item_ids)
            except (ValueError, TypeError):
                continue
    
    return values_query.distinct()


def aggregate_by_period(values, period):
    """
    Агрегирует значения по периоду.
    
    Args:
        values: QuerySet или список IndicatorValue объектов
        period: 'day', 'week', 'month', 'quarter', 'year'
    
    Returns:
        Список словарей с ключами: date, value, count
    """
    if not values:
        return []
    
    if period == 'day':
        # Без агрегации, возвращаем как есть
        return [
            {
                'date': v.date,
                'value': float(v.value),
                'count': 1
            }
            for v in values
        ]
    
    # Группируем по периоду
    aggregated = {}
    
    for value in values:
        # Определяем ключ периода
        if period == 'week':
            # Первый день недели (понедельник)
            week_start = value.date - timedelta(days=value.date.weekday())
            period_key = week_start
        elif period == 'month':
            period_key = date(value.date.year, value.date.month, 1)
        elif period == 'quarter':
            quarter_month = ((value.date.month - 1) // 3) * 3 + 1
            period_key = date(value.date.year, quarter_month, 1)
        elif period == 'year':
            period_key = date(value.date.year, 1, 1)
        else:
            period_key = value.date
        
        # Агрегируем (используем среднее значение)
        if period_key not in aggregated:
            aggregated[period_key] = {
                'date': period_key,
                'values': [],
                'count': 0
            }
        
        aggregated[period_key]['values'].append(float(value.value))
        aggregated[period_key]['count'] += 1
    
    # Вычисляем средние значения
    result = []
    for period_key in sorted(aggregated.keys()):
        values_list = aggregated[period_key]['values']
        avg_value = sum(values_list) / len(values_list) if values_list else 0
        result.append({
            'date': aggregated[period_key]['date'],
            'value': avg_value,
            'count': aggregated[period_key]['count']
        })
    
    return result


def get_indicator_data(indicator, days_back=30, aggregation_period=None, dictionary_filters=None, end_date=None):
    """
    Получает данные показателя для визуализации.
    
    Args:
        indicator: объект Indicator
        days_back: количество дней назад для выборки данных
        aggregation_period: период агрегации ('day', 'week', 'month', 'quarter', 'year')
        dictionary_filters: фильтры по справочникам (dict)
        end_date: конечная дата (строка ISO или date объект)
    
    Returns:
        dict с ключами:
            - dates: список дат (ISO формат)
            - values: список значений
            - statuses: список статусов (green/yellow/red) если пороговые значения заданы
    """
    # Вычисляем дату начала
    start_date = date.today() - timedelta(days=days_back)
    
    # Парсим end_date если передан как строка
    if end_date and isinstance(end_date, str):
        try:
            end_date = date.fromisoformat(end_date)
        except (ValueError, TypeError):
            end_date = None
    
    # Получаем значения показателя
    values_query = IndicatorValue.objects.filter(
        indicator=indicator,
        date__gte=start_date
    )
    
    # Применяем фильтр по конечной дате
    if end_date:
        values_query = values_query.filter(date__lte=end_date)
    
    values_query = values_query.prefetch_related('dictionary_items').order_by('date')
    
    # Применяем фильтры по справочникам
    if dictionary_filters:
        values_query = apply_dictionary_filters(values_query, dictionary_filters)
    
    # Получаем все значения
    values = list(values_query)
    
    # Агрегируем по периоду, если указан
    if aggregation_period and aggregation_period != 'day':
        aggregated_data = aggregate_by_period(values, aggregation_period)
        dates = [item['date'] for item in aggregated_data]
        values_list = [item['value'] for item in aggregated_data]
    else:
        dates = [v.date for v in values]
        values_list = [float(v.value) for v in values]
    
    # Если нет данных, возвращаем пустые списки
    if not dates or not values_list:
        return {
            'dates': [],
            'values': [],
            'statuses': None
        }
    
    # Определяем статусы, если пороговые значения заданы
    statuses = None
    if indicator.unacceptable_value is not None and \
       indicator.acceptable_value is not None and \
       indicator.good_value is not None:
        statuses = []
        for val in values_list:
            status = indicator.get_value_status(val)
            statuses.append(status if status else 'gray')
    
    return {
        'dates': [d.isoformat() for d in dates],
        'values': values_list,
        'statuses': statuses
    }

