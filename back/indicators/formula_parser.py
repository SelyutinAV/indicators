"""Парсер и валидатор формул для агрегатных показателей"""
import re
from decimal import Decimal
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from django.core.exceptions import ValidationError
from .models import Indicator, IndicatorValue


def parse_formula(formula):
    """
    Парсит формулу и извлекает названия показателей
    Поддерживает как простые ссылки [Показатель], так и функции агрегации SUM([Показатель], 'period')
    и функции PREV([Показатель], 'period')
    
    Args:
        formula: Строка с формулой, например: "[Показатель1] + [Показатель2] / [Показатель3]"
                 или "SUM([Выручка], 'month')" или "PREV([Выручка], 'month')"
    
    Returns:
        list: Список названий показателей
    """
    if not formula:
        return []
    
    # Извлекаем показатели из функций агрегации: SUM([Показатель], 'period')
    pattern_func = r'(?:SUM|AVG|MAX|MIN|COUNT)\(\[([^\]]+)\],\s*[\'"](\w+)[\'"]\)'
    func_matches = re.findall(pattern_func, formula)
    
    # Извлекаем показатели из функций PREV: PREV([Показатель], 'period')
    pattern_prev = r'PREV\(\[([^\]]+)\],\s*[\'"](\w+)[\'"]\)'
    prev_matches = re.findall(pattern_prev, formula)
    
    # Извлекаем простые ссылки: [Показатель] (но исключаем те, что уже в функциях)
    # Сначала удаляем функции из формулы для поиска простых ссылок
    formula_without_funcs = re.sub(pattern_func, '', formula)
    formula_without_funcs = re.sub(pattern_prev, '', formula_without_funcs)
    pattern_simple = r'\[([^\]]+)\]'
    simple_matches = re.findall(pattern_simple, formula_without_funcs)
    
    # Объединяем и убираем дубликаты
    all_indicators = (
        [match[0].strip() for match in func_matches] +
        [match[0].strip() for match in prev_matches] +
        [match.strip() for match in simple_matches]
    )
    return list(set(all_indicators))


def parse_aggregation_functions(formula):
    """
    Парсит формулу и извлекает функции агрегации
    
    Args:
        formula: Строка с формулой
    
    Returns:
        list: Список кортежей (function_name, indicator_name, period)
              Например: [('SUM', 'Выручка', 'month'), ('AVG', 'Температура', 'day')]
    """
    if not formula:
        return []
    
    pattern = r'(SUM|AVG|MAX|MIN|COUNT)\(\[([^\]]+)\],\s*[\'"](\w+)[\'"]\)'
    matches = re.findall(pattern, formula)
    return [(func.upper(), indicator.strip(), period.lower()) for func, indicator, period in matches]


def parse_prev_functions(formula):
    """
    Парсит формулу и извлекает функции PREV (предыдущий период)
    
    Args:
        formula: Строка с формулой
    
    Returns:
        list: Список кортежей (indicator_name, period)
              Например: [('Выручка за месяц', 'month'), ('Температура', 'day')]
    """
    if not formula:
        return []
    
    pattern = r'PREV\(\[([^\]]+)\],\s*[\'"](\w+)[\'"]\)'
    matches = re.findall(pattern, formula)
    return [(indicator.strip(), period.lower()) for indicator, period in matches]


def validate_formula_dependencies(indicator):
    """
    Валидирует формулу на наличие всех зависимостей и циклические зависимости
    
    Args:
        indicator: Экземпляр Indicator с типом 'aggregate'
    
    Returns:
        tuple: (is_valid, errors_list)
    """
    if indicator.indicator_type != 'aggregate':
        return True, []
    
    if not indicator.formula:
        return False, ['Формула не указана']
    
    errors = []
    visited = set()
    
    def check_dependencies(ind, path_ids, path_names):
        """Рекурсивная проверка зависимостей"""
        if ind.id in visited:
            return True
        
        visited.add(ind.id)
        path_ids = path_ids + [ind.id]
        path_names = path_names + [ind.name]
        
        indicators_in_formula = parse_formula(ind.formula) if ind.formula else []
        
        for indicator_name in indicators_in_formula:
            try:
                dep_indicator = Indicator.objects.get(name=indicator_name)
                
                # Проверка на циклическую зависимость (прямую)
                if dep_indicator.id == indicator.id:
                    cycle_path = ' -> '.join(path_names + [indicator.name])
                    errors.append(f"Циклическая зависимость: {cycle_path}")
                    return False
                
                # Проверка на повторное вхождение в путь (цикл)
                if dep_indicator.id in path_ids:
                    cycle_path = ' -> '.join(path_names + [dep_indicator.name])
                    errors.append(f"Циклическая зависимость: {cycle_path}")
                    return False
                
                # Рекурсивная проверка зависимостей
                if not check_dependencies(dep_indicator, path_ids, path_names):
                    return False
                    
            except Indicator.DoesNotExist:
                errors.append(f"Показатель '{indicator_name}' не найден")
                return False
        
        return True
    
    is_valid = check_dependencies(indicator, [], [])
    return is_valid, errors


def get_period_range(target_date, period):
    """
    Определяет диапазон дат для указанного периода
    
    Args:
        target_date: Целевая дата (date)
        period: Период ('day', 'month', 'quarter', 'year')
    
    Returns:
        tuple: (start_date, end_date)
    """
    if period == 'day':
        return target_date, target_date
    elif period == 'month':
        start_date = date(target_date.year, target_date.month, 1)
        if target_date.month == 12:
            end_date = date(target_date.year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(target_date.year, target_date.month + 1, 1) - timedelta(days=1)
        return start_date, end_date
    elif period == 'quarter':
        quarter = (target_date.month - 1) // 3
        start_date = date(target_date.year, quarter * 3 + 1, 1)
        if quarter == 3:
            end_date = date(target_date.year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(target_date.year, (quarter + 1) * 3 + 1, 1) - timedelta(days=1)
        return start_date, end_date
    elif period == 'year':
        start_date = date(target_date.year, 1, 1)
        end_date = date(target_date.year, 12, 31)
        return start_date, end_date
    else:
        raise ValueError(f"Неподдерживаемый период: {period}")


def calculate_aggregation_function(function_name, indicator_name, period, target_date, aggregate_by_dimensions=False, target_dimension_items=None):
    """
    Вычисляет значение функции агрегации для показателя за период
    
    Args:
        function_name: Название функции ('SUM', 'AVG', 'MAX', 'MIN', 'COUNT')
        indicator_name: Название показателя
        period: Период агрегации ('day', 'month', 'quarter', 'year')
        target_date: Целевая дата (date)
        aggregate_by_dimensions: Если True, агрегирует только значения с одинаковыми комбинациями справочников
        target_dimension_items: Комбинация элементов справочников для фильтрации (если aggregate_by_dimensions=True)
    
    Returns:
        Decimal: Результат агрегации
    """
    try:
        dep_indicator = Indicator.objects.get(name=indicator_name)
    except Indicator.DoesNotExist:
        raise ValueError(f"Показатель '{indicator_name}' не найден")
    
    # Определяем диапазон дат для периода
    start_date, end_date = get_period_range(target_date, period)
    
    # Получаем значения за период
    if dep_indicator.indicator_type == 'aggregate':
        # Для агрегатных показателей нужно вычислить значения за период
        values = []
        current_date = start_date
        while current_date <= end_date:
            try:
                value = calculate_aggregate_value(dep_indicator, current_date, target_dimension_items=target_dimension_items)
                values.append(value)
            except ValueError:
                pass  # Пропускаем даты без значений
            current_date += timedelta(days=1)
    else:
        # Для атомарных показателей берем значения из БД
        values_query = IndicatorValue.objects.filter(
            indicator=dep_indicator,
            date__gte=start_date,
            date__lte=end_date
        )
        
        # Проверяем, есть ли у базового показателя справочники
        from .models import IndicatorDictionary
        base_has_dicts = IndicatorDictionary.objects.filter(
            indicator=dep_indicator,
            dictionary__is_active=True
        ).exists()
        
        # Если нужно агрегировать в разрезе справочников И базовый показатель тоже имеет справочники
        if aggregate_by_dimensions and target_dimension_items is not None and base_has_dicts:
            # Фильтруем только значения с указанной комбинацией справочников
            # Преобразуем target_dimension_items в set ID для сравнения
            target_items_ids = set()
            if target_dimension_items:
                for item in target_dimension_items:
                    # Если это объект DictionaryItem, берем ID, иначе считаем что это уже ID
                    if hasattr(item, 'id'):
                        target_items_ids.add(item.id)
                    else:
                        target_items_ids.add(item)
            
            # Фильтруем значения, у которых dictionary_items совпадает с target_dimension_items
            filtered_values = []
            for value_obj in values_query.prefetch_related('dictionary_items'):
                value_items_ids = set(value_obj.dictionary_items.values_list('id', flat=True))
                if value_items_ids == target_items_ids:
                    filtered_values.append(value_obj.value)
            values = filtered_values
        else:
            # Агрегируем все значения независимо от справочников
            # (если базовый показатель не имеет справочников или aggregate_by_dimensions=False)
            values = list(values_query.values_list('value', flat=True))
    
    if not values:
        dimension_str = ""
        if aggregate_by_dimensions and target_dimension_items:
            dimension_str = f" в разрезе {', '.join([str(item) for item in target_dimension_items])}"
        raise ValueError(
            f"Нет значений для показателя '{indicator_name}' за период {period} (с {start_date} по {end_date}){dimension_str}"
        )
    
    # Применяем функцию агрегации
    if function_name == 'SUM':
        result = sum(Decimal(str(v)) for v in values)
    elif function_name == 'AVG':
        result = sum(Decimal(str(v)) for v in values) / len(values)
    elif function_name == 'MAX':
        result = max(Decimal(str(v)) for v in values)
    elif function_name == 'MIN':
        result = min(Decimal(str(v)) for v in values)
    elif function_name == 'COUNT':
        result = Decimal(len(values))
    else:
        raise ValueError(f"Неподдерживаемая функция: {function_name}")
    
    return result


def calculate_prev_period_value(indicator_name, period, target_date, target_dimension_items=None):
    """
    Получает значение показателя за предыдущий период
    
    Args:
        indicator_name: Название показателя
        period: Период ('day', 'month', 'quarter', 'year')
        target_date: Текущая дата
        target_dimension_items: Комбинация элементов справочников для расчета (опционально)
    
    Returns:
        Decimal: Значение за предыдущий период
    """
    try:
        dep_indicator = Indicator.objects.get(name=indicator_name)
    except Indicator.DoesNotExist:
        raise ValueError(f"Показатель '{indicator_name}' не найден")
    
    # Вычисляем дату для предыдущего периода
    # Для месячных/квартальных/годовых агрегатов берем ту же дату в предыдущем периоде
    if period == 'month':
        # Предыдущий месяц - та же дата в предыдущем месяце
        prev_date = target_date - relativedelta(months=1)
    elif period == 'quarter':
        # Предыдущий квартал - та же дата в предыдущем квартале
        prev_date = target_date - relativedelta(months=3)
    elif period == 'year':
        # Предыдущий год - та же дата в предыдущем году
        prev_date = target_date - relativedelta(years=1)
    elif period == 'day':
        # Предыдущий день
        prev_date = target_date - timedelta(days=1)
    else:
        raise ValueError(f"Неподдерживаемый период: {period}")
    
    # Получаем значение показателя на эту дату
    # Если указаны разрезы, ищем значение с нужной комбинацией справочников
    if target_dimension_items is not None:
        # Преобразуем target_dimension_items в set ID для сравнения
        target_items_ids = set()
        if target_dimension_items:
            for item in target_dimension_items:
                if hasattr(item, 'id'):
                    target_items_ids.add(item.id)
                else:
                    target_items_ids.add(item)
        
        # Ищем значение с нужной комбинацией справочников
        value_objs = IndicatorValue.objects.filter(
            indicator=dep_indicator,
            date=prev_date
        ).prefetch_related('dictionary_items')
        
        found_value = None
        for value_obj in value_objs:
            value_items_ids = set(value_obj.dictionary_items.values_list('id', flat=True))
            if value_items_ids == target_items_ids:
                found_value = value_obj.value
                break
        
        if found_value is not None:
            return found_value
        else:
            # Если значение отсутствует, пытаемся вычислить для агрегатного
            if dep_indicator.indicator_type == 'aggregate':
                try:
                    return calculate_aggregate_value(dep_indicator, prev_date, target_dimension_items=target_dimension_items)
                except ValueError:
                    # Если не удалось вычислить, возвращаем 0 (предыдущее значение отсутствует)
                    # Это нормальная ситуация для первой даты расчета
                    return Decimal('0')
            else:
                # Для атомарных показателей, если значение отсутствует, возвращаем 0
                # Это нормальная ситуация для первой даты расчета
                return Decimal('0')
    else:
        # Если разрезы не указаны, берем первое найденное значение
        try:
            value_obj = IndicatorValue.objects.filter(
                indicator=dep_indicator,
                date=prev_date
            ).first()
            
            if value_obj:
                return value_obj.value
            else:
                # Если значение отсутствует, пытаемся вычислить для агрегатного
                if dep_indicator.indicator_type == 'aggregate':
                    try:
                        return calculate_aggregate_value(dep_indicator, prev_date, target_dimension_items=target_dimension_items)
                    except ValueError:
                        # Если не удалось вычислить, возвращаем 0 (предыдущее значение отсутствует)
                        # Это нормальная ситуация для первой даты расчета
                        return Decimal('0')
                else:
                    # Для атомарных показателей, если значение отсутствует, возвращаем 0
                    # Это нормальная ситуация для первой даты расчета
                    return Decimal('0')
        except IndicatorValue.MultipleObjectsReturned:
            # Если несколько значений, берем первое
            value_obj = IndicatorValue.objects.filter(
                indicator=dep_indicator,
                date=prev_date
            ).first()
            if value_obj:
                return value_obj.value
            else:
                # Если значение отсутствует, возвращаем 0 (предыдущее значение отсутствует)
                # Это нормальная ситуация для первой даты расчета
                return Decimal('0')


def calculate_aggregate_value(indicator, target_date, target_dimension_items=None):
    """
    Вычисляет значение агрегатного показателя на указанную дату
    Поддерживает функции агрегации: SUM, AVG, MAX, MIN, COUNT
    
    Args:
        indicator: Экземпляр Indicator с типом 'aggregate'
        target_date: Дата для расчета (date)
        target_dimension_items: Комбинация элементов справочников для расчета (опционально)
    
    Returns:
        Decimal: Рассчитанное значение
    """
    if indicator.indicator_type != 'aggregate':
        raise ValueError("Метод применим только для агрегатных показателей")
    
    if not indicator.formula:
        raise ValueError("Формула не указана")
    
    formula = indicator.formula
    
    # Определяем, нужно ли агрегировать в разрезе справочников
    # Если есть обязательные справочники или установлен флаг aggregate_by_dimensions
    # Для агрегатных показателей: если есть справочники, всегда агрегируем в разрезе
    from .models import IndicatorDictionary
    has_required_dicts = IndicatorDictionary.objects.filter(
        indicator=indicator,
        is_required=True,
        dictionary__is_active=True
    ).exists()
    
    has_any_dicts = indicator.dictionaries.exists()
    
    # Для агрегатных показателей: если есть справочники, всегда агрегируем в разрезе
    aggregate_by_dimensions = (
        indicator.aggregate_by_dimensions or 
        has_required_dicts or 
        (indicator.indicator_type == 'aggregate' and has_any_dicts)
    )
    
    # Обрабатываем функции агрегации
    aggregation_functions = parse_aggregation_functions(formula)
    for func_name, indicator_name, period in aggregation_functions:
        try:
            agg_value = calculate_aggregation_function(
                func_name, indicator_name, period, target_date,
                aggregate_by_dimensions=aggregate_by_dimensions,
                target_dimension_items=target_dimension_items
            )
            # Заменяем функцию в формуле на вычисленное значение
            pattern = f"{func_name}\\(\\[{re.escape(indicator_name)}\\]\\s*,\\s*['\"]{re.escape(period)}['\"]\\)"
            formula = re.sub(pattern, str(float(agg_value)), formula)
        except ValueError as e:
            raise ValueError(f"Ошибка в функции {func_name}([{indicator_name}], '{period}'): {str(e)}")
    
    # Обрабатываем функции PREV (предыдущий период)
    prev_functions = parse_prev_functions(formula)
    for indicator_name, period in prev_functions:
        try:
            prev_value = calculate_prev_period_value(indicator_name, period, target_date, target_dimension_items=target_dimension_items)
            # Заменяем функцию PREV в формуле на вычисленное значение
            pattern = f"PREV\\(\\[{re.escape(indicator_name)}\\]\\s*,\\s*['\"]{re.escape(period)}['\"]\\)"
            formula = re.sub(pattern, str(float(prev_value)), formula)
        except ValueError as e:
            raise ValueError(f"Ошибка в функции PREV([{indicator_name}], '{period}'): {str(e)}")
    
    # Получаем все показатели, используемые в формуле (простые ссылки)
    indicator_names = parse_formula(formula)
    
    # Создаем словарь значений показателей на целевую дату
    values_dict = {}
    for indicator_name in indicator_names:
        try:
            dep_indicator = Indicator.objects.get(name=indicator_name)
            try:
                # Если нужно учитывать разрезы, ищем значение с нужной комбинацией справочников
                if aggregate_by_dimensions and target_dimension_items is not None:
                    # Преобразуем target_dimension_items в set ID для сравнения
                    target_items_ids = set()
                    if target_dimension_items:
                        for item in target_dimension_items:
                            # Если это объект DictionaryItem, берем ID, иначе считаем что это уже ID
                            if hasattr(item, 'id'):
                                target_items_ids.add(item.id)
                            else:
                                target_items_ids.add(item)
                    
                    value_objs = IndicatorValue.objects.filter(
                        indicator=dep_indicator,
                        date=target_date
                    ).prefetch_related('dictionary_items')
                    
                    found_value = None
                    for value_obj in value_objs:
                        value_items_ids = set(value_obj.dictionary_items.values_list('id', flat=True))
                        if value_items_ids == target_items_ids:
                            found_value = value_obj.value
                            break
                    
                    if found_value is not None:
                        values_dict[indicator_name] = found_value
                    else:
                        # Если значение отсутствует, пытаемся вычислить для агрегатного
                        if dep_indicator.indicator_type == 'aggregate':
                            values_dict[indicator_name] = calculate_aggregate_value(
                                dep_indicator, target_date, target_dimension_items=target_dimension_items
                            )
                        else:
                            raise ValueError(
                                f"Отсутствует значение для показателя '{indicator_name}' на дату {target_date} с указанным разрезом"
                            )
                else:
                    # Берем любое значение (первое найденное) или вычисляем для агрегатного
                    value_obj = IndicatorValue.objects.filter(
                        indicator=dep_indicator,
                        date=target_date
                    ).first()
                    
                    if value_obj:
                        values_dict[indicator_name] = value_obj.value
                    else:
                        # Если значение отсутствует, пытаемся вычислить для агрегатного
                        if dep_indicator.indicator_type == 'aggregate':
                            values_dict[indicator_name] = calculate_aggregate_value(
                                dep_indicator, target_date, target_dimension_items=target_dimension_items
                            )
                        else:
                            raise ValueError(
                                f"Отсутствует значение для показателя '{indicator_name}' на дату {target_date}"
                            )
            except IndicatorValue.DoesNotExist:
                # Если значение отсутствует, пытаемся вычислить для агрегатного
                if dep_indicator.indicator_type == 'aggregate':
                    values_dict[indicator_name] = calculate_aggregate_value(
                        dep_indicator, target_date, target_dimension_items=target_dimension_items
                    )
                else:
                    raise ValueError(
                        f"Отсутствует значение для показателя '{indicator_name}' на дату {target_date}"
                    )
        except Indicator.DoesNotExist:
            raise ValueError(f"Показатель '{indicator_name}' не найден")
    
    # Заменяем названия показателей в формуле на их значения
    for indicator_name in indicator_names:
        formula = formula.replace(
            f'[{indicator_name}]',
            str(float(values_dict[indicator_name]))
        )
    
    # Безопасное вычисление формулы
    try:
        result = Decimal(str(eval(formula)))
        # Округляем в зависимости от типа значения показателя
        if indicator.value_type == 'integer':
            result = result.quantize(Decimal('1'))
        else:
            result = result.quantize(Decimal('0.0001'))
        return result
    except Exception as e:
        raise ValueError(f"Ошибка вычисления формулы: {str(e)}")

