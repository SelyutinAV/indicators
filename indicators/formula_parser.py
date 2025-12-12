"""Парсер и валидатор формул для агрегатных показателей"""
import re
from decimal import Decimal
from django.core.exceptions import ValidationError
from .models import Indicator, IndicatorValue


def parse_formula(formula):
    """
    Парсит формулу и извлекает названия показателей
    
    Args:
        formula: Строка с формулой, например: "[Показатель1] + [Показатель2] / [Показатель3]"
    
    Returns:
        list: Список названий показателей
    """
    if not formula:
        return []
    
    pattern = r'\[([^\]]+)\]'
    matches = re.findall(pattern, formula)
    return [match.strip() for match in matches]


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


def calculate_aggregate_value(indicator, target_date):
    """
    Вычисляет значение агрегатного показателя на указанную дату
    
    Args:
        indicator: Экземпляр Indicator с типом 'aggregate'
        target_date: Дата для расчета (date)
    
    Returns:
        Decimal: Рассчитанное значение
    """
    if indicator.indicator_type != 'aggregate':
        raise ValueError("Метод применим только для агрегатных показателей")
    
    if not indicator.formula:
        raise ValueError("Формула не указана")
    
    # Получаем все показатели, используемые в формуле
    indicator_names = parse_formula(indicator.formula)
    
    # Создаем словарь значений показателей на целевую дату
    values_dict = {}
    for indicator_name in indicator_names:
        try:
            dep_indicator = Indicator.objects.get(name=indicator_name)
            try:
                value_obj = IndicatorValue.objects.get(
                    indicator=dep_indicator,
                    date=target_date
                )
                values_dict[indicator_name] = value_obj.value
            except IndicatorValue.DoesNotExist:
                # Если значение отсутствует, пытаемся вычислить для агрегатного
                if dep_indicator.indicator_type == 'aggregate':
                    values_dict[indicator_name] = calculate_aggregate_value(
                        dep_indicator, target_date
                    )
                else:
                    raise ValueError(
                        f"Отсутствует значение для показателя '{indicator_name}' на дату {target_date}"
                    )
        except Indicator.DoesNotExist:
            raise ValueError(f"Показатель '{indicator_name}' не найден")
    
    # Заменяем названия показателей в формуле на их значения
    formula = indicator.formula
    for indicator_name in indicator_names:
        formula = formula.replace(
            f'[{indicator_name}]',
            str(float(values_dict[indicator_name]))
        )
    
    # Безопасное вычисление формулы
    try:
        result = Decimal(str(eval(formula)))
        return result.quantize(Decimal('0.0001'))
    except Exception as e:
        raise ValueError(f"Ошибка вычисления формулы: {str(e)}")

