from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.core.exceptions import ValidationError
import json
from decimal import Decimal
from .models import Unit, Indicator, IndicatorValue, ImportTemplate
from .generators import generate_test_values
from .formula_parser import parse_formula, validate_formula_dependencies, calculate_aggregate_value
from .excel_parser import parse_indicators_from_excel
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta


def index(request):
    """Главная страница - реестр показателей"""
    indicators = Indicator.objects.all().select_related('unit').order_by('-created_at')
    
    # Поиск
    search_query = request.GET.get('search', '')
    if search_query:
        indicators = indicators.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    # Фильтр по типу
    indicator_type = request.GET.get('type', '')
    if indicator_type:
        indicators = indicators.filter(indicator_type=indicator_type)
    
    # Пагинация
    paginator = Paginator(indicators, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'indicator_type': indicator_type,
        'total_count': indicators.count(),
    }
    return render(request, 'indicators/index.html', context)


def indicator_detail(request, pk):
    """Детальная страница показателя"""
    indicator = get_object_or_404(Indicator, pk=pk)
    
    # Получаем последние значения
    values = indicator.values.all().order_by('-date')[:30]
    
    # Получаем зависимости для агрегатных показателей
    dependencies = []
    if indicator.indicator_type == 'aggregate' and indicator.formula:
        dep_names = parse_formula(indicator.formula)
        dependencies = Indicator.objects.filter(name__in=dep_names)
    
    # Проверяем режим редактирования
    edit_mode = request.GET.get('edit', 'false') == 'true'
    
    context = {
        'indicator': indicator,
        'values': values,
        'dependencies': dependencies,
        'units': Unit.objects.all(),
        'indicators': Indicator.objects.exclude(pk=pk).order_by('name'),
        'edit_mode': edit_mode,
    }
    return render(request, 'indicators/detail.html', context)


def indicator_edit(request, pk):
    """Редактирование показателя"""
    indicator = get_object_or_404(Indicator, pk=pk)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        indicator_type = request.POST.get('indicator_type')
        unit_id = request.POST.get('unit')
        direction = request.POST.get('direction', 'increasing')
        value_type = request.POST.get('value_type', 'decimal')
        min_value = request.POST.get('min_value')
        max_value = request.POST.get('max_value')
        unacceptable_value = request.POST.get('unacceptable_value')
        acceptable_value = request.POST.get('acceptable_value')
        good_value = request.POST.get('good_value')
        formula = request.POST.get('formula', '')
        
        try:
            unit = Unit.objects.get(pk=unit_id)
            
            # Обновляем поля показателя
            indicator.name = name
            indicator.description = description
            indicator.indicator_type = indicator_type
            indicator.unit = unit
            indicator.direction = direction
            indicator.value_type = value_type
            indicator.formula = formula if indicator_type == 'aggregate' else ''
            
            # Обновляем числовые поля
            if min_value:
                indicator.min_value = min_value
            else:
                indicator.min_value = None
                
            if max_value:
                indicator.max_value = max_value
            else:
                indicator.max_value = None
                
            if unacceptable_value:
                indicator.unacceptable_value = unacceptable_value
            else:
                indicator.unacceptable_value = None
                
            if acceptable_value:
                indicator.acceptable_value = acceptable_value
            else:
                indicator.acceptable_value = None
                
            if good_value:
                indicator.good_value = good_value
            else:
                indicator.good_value = None
            
            # Валидация
            try:
                indicator.full_clean()
            except ValidationError as e:
                # Обрабатываем ошибки валидации
                error_messages = []
                if hasattr(e, 'error_dict'):
                    for field, errors in e.error_dict.items():
                        for error in errors:
                            error_messages.append(f'{field}: {error.message}')
                else:
                    error_messages.append(str(e))
                
                messages.error(request, 'Ошибки валидации: ' + '; '.join(error_messages))
                
                # Получаем зависимости для отображения
                dependencies = []
                if indicator.indicator_type == 'aggregate' and indicator.formula:
                    dep_names = parse_formula(indicator.formula)
                    dependencies = Indicator.objects.filter(name__in=dep_names)
                
                return render(request, 'indicators/detail.html', {
                    'indicator': indicator,
                    'units': Unit.objects.all(),
                    'indicators': Indicator.objects.exclude(pk=pk).order_by('name'),
                    'values': indicator.values.all().order_by('-date')[:30],
                    'dependencies': dependencies,
                    'edit_mode': True,
                    'form_data': request.POST,
                })
            
            # Валидация формулы для агрегатных показателей
            if indicator_type == 'aggregate' and formula:
                # Сохраняем временно для валидации
                indicator.save()
                is_valid, errors = validate_formula_dependencies(indicator)
                if not is_valid:
                    messages.error(request, f'Ошибка в формуле: {"; ".join(errors)}')
                    
                    # Получаем зависимости для отображения
                    dependencies = []
                    if indicator.formula:
                        dep_names = parse_formula(indicator.formula)
                        dependencies = Indicator.objects.filter(name__in=dep_names)
                    
                    return render(request, 'indicators/detail.html', {
                        'indicator': indicator,
                        'units': Unit.objects.all(),
                        'indicators': Indicator.objects.exclude(pk=pk).order_by('name'),
                        'values': indicator.values.all().order_by('-date')[:30],
                        'dependencies': dependencies,
                        'edit_mode': True,
                        'form_data': request.POST,
                    })
                # Если валидация прошла, объект уже сохранен
                messages.success(request, f'Показатель "{indicator.name}" успешно обновлен!')
                return redirect('indicators:indicator_detail', pk=indicator.pk)
            
            indicator.save()
            messages.success(request, f'Показатель "{indicator.name}" успешно обновлен!')
            return redirect('indicators:indicator_detail', pk=indicator.pk)
            
        except Exception as e:
            messages.error(request, f'Ошибка при обновлении показателя: {str(e)}')
            
            # Получаем зависимости для отображения
            dependencies = []
            if indicator.indicator_type == 'aggregate' and indicator.formula:
                dep_names = parse_formula(indicator.formula)
                dependencies = Indicator.objects.filter(name__in=dep_names)
            
            return render(request, 'indicators/detail.html', {
                'indicator': indicator,
                'units': Unit.objects.all(),
                'indicators': Indicator.objects.exclude(pk=pk).order_by('name'),
                'values': indicator.values.all().order_by('-date')[:30],
                'dependencies': dependencies,
                'edit_mode': True,
                'form_data': request.POST,
            })
    
    # GET запрос - просто редирект на детальную страницу с флагом редактирования
    return redirect('indicators:indicator_detail', pk=pk)


@require_http_methods(["POST"])
def save_formula_only(request, pk):
    """Сохранение только формулы показателя"""
    indicator = get_object_or_404(Indicator, pk=pk)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            formula = data.get('formula', '').strip()
            
            if indicator.indicator_type != 'aggregate':
                return JsonResponse({
                    'success': False,
                    'error': 'Формула может быть указана только для агрегатного показателя'
                })
            
            # Обновляем формулу
            old_formula = indicator.formula
            indicator.formula = formula
            
            # Валидация
            try:
                indicator.full_clean()
                is_valid, errors = validate_formula_dependencies(indicator)
                
                if not is_valid:
                    indicator.formula = old_formula  # Восстанавливаем старую формулу
                    return JsonResponse({
                        'success': False,
                        'error': '; '.join(errors) if errors else 'Ошибка валидации формулы'
                    })
                
                # Сохраняем
                indicator.save()
                
                return JsonResponse({
                    'success': True,
                    'message': 'Формула успешно сохранена'
                })
                
            except ValidationError as e:
                indicator.formula = old_formula  # Восстанавливаем старую формулу
                error_messages = []
                for field, messages_list in e.message_dict.items():
                    error_messages.extend(messages_list)
                return JsonResponse({
                    'success': False,
                    'error': '; '.join(error_messages)
                })
                
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Неверный формат данных'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': f'Ошибка: {str(e)}'})
    
    return JsonResponse({'success': False, 'error': 'Метод не разрешен'})


@require_http_methods(["POST"])
def validate_formula_ajax(request):
    """Проверка формулы через AJAX"""
    try:
        data = json.loads(request.body)
        formula = data.get('formula', '').strip()
        indicator_id = data.get('indicator_id')  # None для нового показателя
        
        if not formula:
            return JsonResponse({'success': False, 'error': 'Формула не указана'})
        
        # Создаем временный объект показателя для валидации
        # Если это редактирование, получаем существующий показатель
        old_formula = None
        if indicator_id:
            try:
                indicator = Indicator.objects.get(pk=indicator_id)
                # Временно сохраняем формулу для валидации
                old_formula = indicator.formula
                indicator.formula = formula
            except Indicator.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Показатель не найден'})
        else:
            # Для нового показателя создаем временный объект
            # Нужно получить хотя бы один показатель для создания временного объекта
            try:
                first_indicator = Indicator.objects.first()
                if not first_indicator:
                    return JsonResponse({'success': False, 'error': 'Нет показателей в системе для валидации'})
                indicator = Indicator(
                    name='__temp__',
                    indicator_type='aggregate',
                    unit=first_indicator.unit,
                    formula=formula
                )
            except Exception:
                return JsonResponse({'success': False, 'error': 'Ошибка при создании временного объекта'})
        
        # Валидация формулы
        try:
            is_valid, errors = validate_formula_dependencies(indicator)
            
            if is_valid:
                # Дополнительная проверка синтаксиса формулы
                try:
                    # Пробуем извлечь все показатели
                    indicators_in_formula = parse_formula(formula)
                    if not indicators_in_formula:
                        return JsonResponse({
                            'success': False, 
                            'error': 'В формуле не найдено ни одного показателя'
                        })
                    
                    # Проверяем, что все показатели существуют
                    missing_indicators = []
                    for ind_name in indicators_in_formula:
                        if not Indicator.objects.filter(name=ind_name).exists():
                            missing_indicators.append(ind_name)
                    
                    if missing_indicators:
                        return JsonResponse({
                            'success': False,
                            'error': f'Показатели не найдены: {", ".join(missing_indicators)}'
                        })
                    
                    return JsonResponse({
                        'success': True,
                        'message': 'Формула валидна',
                        'indicators': indicators_in_formula
                    })
                except Exception as e:
                    return JsonResponse({
                        'success': False,
                        'error': f'Ошибка при проверке формулы: {str(e)}'
                    })
            else:
                return JsonResponse({
                    'success': False,
                    'error': '; '.join(errors) if errors else 'Ошибка валидации формулы'
                })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Ошибка при валидации: {str(e)}'
            })
        finally:
            # Восстанавливаем старую формулу, если это было редактирование
            if indicator_id and old_formula is not None and hasattr(indicator, 'id'):
                indicator.formula = old_formula
    
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Неверный формат данных'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Ошибка: {str(e)}'})


def calculate_aggregate_values(request, pk):
    """Расчет значений агрегатного показателя"""
    indicator = get_object_or_404(Indicator, pk=pk)
    
    if indicator.indicator_type != 'aggregate':
        messages.error(request, 'Расчет значений доступен только для агрегатных показателей')
        return redirect('indicators:indicator_detail', pk=pk)
    
    if not indicator.formula:
        messages.error(request, 'Для расчета значений необходимо указать формулу')
        return redirect('indicators:indicator_detail', pk=pk)
    
    if request.method == 'POST':
        start_date_str = request.POST.get('start_date')
        end_date_str = request.POST.get('end_date')
        step = request.POST.get('step', 'day')
        
        try:
            start_date = date.fromisoformat(start_date_str)
            end_date = date.fromisoformat(end_date_str)
        except (ValueError, TypeError):
            messages.error(request, 'Неверный формат даты')
            return redirect('indicators:indicator_detail', pk=pk)
        
        if start_date > end_date:
            messages.error(request, 'Начальная дата не может быть больше конечной')
            return redirect('indicators:indicator_detail', pk=pk)
        
        # Генерируем список дат для расчета
        dates_to_calculate = []
        current_date = start_date
        
        if step == 'day':
            while current_date <= end_date:
                dates_to_calculate.append(current_date)
                current_date += timedelta(days=1)
        elif step == 'month':
            while current_date <= end_date:
                dates_to_calculate.append(current_date)
                current_date += relativedelta(months=1)
        else:
            messages.error(request, 'Неподдерживаемый шаг расчета')
            return redirect('indicators:indicator_detail', pk=pk)
        
        # Рассчитываем значения для каждой даты
        calculated_count = 0
        error_count = 0
        errors = []
        
        for target_date in dates_to_calculate:
            try:
                # Рассчитываем значение
                calculated_value = calculate_aggregate_value(indicator, target_date)
                
                # Сохраняем или обновляем значение
                IndicatorValue.objects.update_or_create(
                    indicator=indicator,
                    date=target_date,
                    defaults={'value': calculated_value}
                )
                calculated_count += 1
            except ValueError as e:
                error_count += 1
                errors.append(f"{target_date.strftime('%d.%m.%Y')}: {str(e)}")
            except Exception as e:
                error_count += 1
                errors.append(f"{target_date.strftime('%d.%m.%Y')}: {str(e)}")
        
        # Показываем результаты
        if calculated_count > 0:
            messages.success(request, f'Успешно рассчитано значений: {calculated_count}')
        if error_count > 0:
            error_msg = f'Ошибок при расчете: {error_count}'
            if len(errors) <= 5:
                error_msg += '. ' + '; '.join(errors)
            else:
                error_msg += f'. Первые 5 ошибок: {"; ".join(errors[:5])}'
            messages.warning(request, error_msg)
        
        return redirect('indicators:indicator_detail', pk=pk)
    
    # GET запрос - показываем форму
    return redirect('indicators:indicator_detail', pk=pk)


def indicator_create(request):
    """Создание нового показателя"""
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        indicator_type = request.POST.get('indicator_type')
        unit_id = request.POST.get('unit')
        direction = request.POST.get('direction', 'increasing')
        value_type = request.POST.get('value_type', 'decimal')
        min_value = request.POST.get('min_value')
        max_value = request.POST.get('max_value')
        unacceptable_value = request.POST.get('unacceptable_value')
        acceptable_value = request.POST.get('acceptable_value')
        good_value = request.POST.get('good_value')
        formula = request.POST.get('formula', '')
        
        try:
            unit = Unit.objects.get(pk=unit_id)
            
            indicator = Indicator(
                name=name,
                description=description,
                indicator_type=indicator_type,
                unit=unit,
                direction=direction,
                value_type=value_type,
                formula=formula if indicator_type == 'aggregate' else '',
            )
            
            if min_value:
                indicator.min_value = min_value
            if max_value:
                indicator.max_value = max_value
            if unacceptable_value:
                indicator.unacceptable_value = unacceptable_value
            if acceptable_value:
                indicator.acceptable_value = acceptable_value
            if good_value:
                indicator.good_value = good_value
            
            # Валидация
            indicator.full_clean()
            
            # Валидация формулы для агрегатных показателей
            if indicator_type == 'aggregate' and formula:
                # Сохраняем временно для валидации
                indicator.save()
                is_valid, errors = validate_formula_dependencies(indicator)
                if not is_valid:
                    indicator.delete()  # Удаляем, если валидация не прошла
                    messages.error(request, f'Ошибка в формуле: {"; ".join(errors)}')
                    return render(request, 'indicators/create.html', {
                        'units': Unit.objects.all(),
                        'form_data': request.POST,
                    })
                # Если валидация прошла, объект уже сохранен
                messages.success(request, f'Показатель "{indicator.name}" успешно создан!')
                return redirect('indicators:indicator_detail', pk=indicator.pk)
            
            indicator.save()
            messages.success(request, f'Показатель "{indicator.name}" успешно создан!')
            return redirect('indicators:indicator_detail', pk=indicator.pk)
            
        except Exception as e:
            messages.error(request, f'Ошибка при создании показателя: {str(e)}')
    
    context = {
        'units': Unit.objects.all(),
        'indicators': Indicator.objects.all().order_by('name'),
    }
    return render(request, 'indicators/create.html', context)


def generate_data(request, pk):
    """Генерация тестовых данных для показателя"""
    indicator = get_object_or_404(Indicator, pk=pk)
    
    if request.method == 'POST':
        start_date_str = request.POST.get('start_date')
        end_date_str = request.POST.get('end_date')
        min_value_str = request.POST.get('min_value')
        max_value_str = request.POST.get('max_value')
        step = request.POST.get('step', 'day')
        
        try:
            start_date = date.fromisoformat(start_date_str)
            end_date = date.fromisoformat(end_date_str)
            
            # Определяем минимальное и максимальное значения
            min_value = None
            max_value = None
            
            if min_value_str:
                min_value = Decimal(min_value_str)
            elif indicator.min_value:
                min_value = indicator.min_value
                
            if max_value_str:
                max_value = Decimal(max_value_str)
            elif indicator.max_value:
                max_value = indicator.max_value
            
            if min_value is None or max_value is None:
                messages.error(request, 'Необходимо указать минимальное и максимальное значение для генерации данных')
                return redirect('indicators:indicator_detail', pk=indicator.pk)
            
            if min_value >= max_value:
                messages.error(request, 'Максимальное значение должно быть больше минимального')
                return redirect('indicators:indicator_detail', pk=indicator.pk)
            
            count = generate_test_values(
                indicator, 
                start_date, 
                end_date,
                min_value=min_value,
                max_value=max_value,
                step=step
            )
            messages.success(request, f'Успешно сгенерировано {count} значений!')
            
        except ValueError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f'Ошибка при генерации данных: {str(e)}')
    
    return redirect('indicators:indicator_detail', pk=indicator.pk)


def generate_indicators(request):
    """Страница массовой генерации значений для показателей"""
    # Получаем только показатели с настроенными min/max значениями
    indicators = Indicator.objects.filter(
        min_value__isnull=False,
        max_value__isnull=False
    ).select_related('unit').order_by('name')
    
    if request.method == 'POST':
        indicator_ids = request.POST.getlist('indicators')
        start_date_str = request.POST.get('start_date')
        end_date_str = request.POST.get('end_date')
        step = request.POST.get('step', 'day')
        min_value_str = request.POST.get('min_value')
        max_value_str = request.POST.get('max_value')
        
        if not indicator_ids:
            messages.error(request, 'Необходимо выбрать хотя бы один показатель')
            return render(request, 'indicators/generate.html', {
                'indicators': indicators
            })
        
        try:
            start_date = date.fromisoformat(start_date_str)
            end_date = date.fromisoformat(end_date_str)
            
            # Определяем общие min/max значения (если указаны)
            common_min_value = None
            common_max_value = None
            
            if min_value_str:
                common_min_value = Decimal(min_value_str)
            if max_value_str:
                common_max_value = Decimal(max_value_str)
            
            # Генерируем данные для каждого выбранного показателя
            total_generated = 0
            success_count = 0
            error_count = 0
            errors = []
            
            for indicator_id in indicator_ids:
                try:
                    indicator = Indicator.objects.get(pk=indicator_id)
                    
                    # Определяем min/max для конкретного показателя
                    # Если указаны общие значения, используем их, иначе - из настроек показателя
                    min_value = common_min_value if common_min_value is not None else indicator.min_value
                    max_value = common_max_value if common_max_value is not None else indicator.max_value
                    
                    if min_value is None or max_value is None:
                        errors.append(f'{indicator.name}: не указаны min/max значения')
                        error_count += 1
                        continue
                    
                    if min_value >= max_value:
                        errors.append(f'{indicator.name}: максимальное значение должно быть больше минимального (min: {min_value}, max: {max_value})')
                        error_count += 1
                        continue
                    
                    count = generate_test_values(
                        indicator,
                        start_date,
                        end_date,
                        min_value=min_value,
                        max_value=max_value,
                        step=step
                    )
                    total_generated += count
                    success_count += 1
                    
                except Indicator.DoesNotExist:
                    errors.append(f'Показатель с ID {indicator_id} не найден')
                    error_count += 1
                except ValueError as e:
                    errors.append(f'{indicator.name}: {str(e)}')
                    error_count += 1
                except Exception as e:
                    errors.append(f'{indicator.name}: ошибка генерации - {str(e)}')
                    error_count += 1
            
            # Формируем сообщения о результате
            if success_count > 0:
                messages.success(
                    request,
                    f'Успешно сгенерировано данных для {success_count} показателей. Всего создано {total_generated} значений.'
                )
            
            if error_count > 0:
                for error in errors:
                    messages.warning(request, error)
            
            if success_count == 0:
                messages.error(request, 'Не удалось сгенерировать данные ни для одного показателя')
            
            return redirect('indicators:generate_indicators')
            
        except ValueError as e:
            messages.error(request, f'Ошибка в датах: {str(e)}')
        except Exception as e:
            messages.error(request, f'Ошибка при генерации данных: {str(e)}')
    
    context = {
        'indicators': indicators,
    }
    return render(request, 'indicators/generate.html', context)


def units_list(request):
    """Список единиц измерения"""
    units = Unit.objects.all().order_by('name')
    return render(request, 'indicators/units.html', {'units': units})


@csrf_exempt
@require_http_methods(["POST"])
def get_excel_sheets(request):
    """Получение списка листов из Excel файла через AJAX"""
    try:
        if 'excel_file' not in request.FILES:
            return JsonResponse({'success': False, 'error': 'Файл не выбран'})
        
        excel_file = request.FILES['excel_file']
        
        # Сохраняем файл временно
        file_path = default_storage.save(
            f'temp_sheets_{excel_file.name}',
            ContentFile(excel_file.read())
        )
        full_path = default_storage.path(file_path)
        
        try:
            import openpyxl
            workbook = openpyxl.load_workbook(full_path, read_only=True)
            sheet_names = workbook.sheetnames
            workbook.close()
            
            # Удаляем временный файл
            if default_storage.exists(file_path):
                default_storage.delete(file_path)
            
            return JsonResponse({
                'success': True,
                'sheets': sheet_names
            })
        except Exception as e:
            # Удаляем временный файл в случае ошибки
            if default_storage.exists(file_path):
                default_storage.delete(file_path)
            return JsonResponse({
                'success': False,
                'error': f'Ошибка при чтении файла: {str(e)}'
            })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Ошибка при обработке файла: {str(e)}'
        })


@csrf_exempt
@require_http_methods(["POST"])
def unit_create_ajax(request):
    """Создание единицы измерения через AJAX"""
    try:
        data = json.loads(request.body)
        name = data.get('name', '').strip()
        symbol = data.get('symbol', '').strip()
        description = data.get('description', '').strip()
        
        # Валидация
        if not name:
            return JsonResponse({'success': False, 'error': 'Название единицы измерения обязательно'})
        
        if not symbol:
            return JsonResponse({'success': False, 'error': 'Символ единицы измерения обязателен'})
        
        # Проверка на уникальность
        if Unit.objects.filter(name=name).exists():
            return JsonResponse({'success': False, 'error': 'Единица измерения с таким названием уже существует'})
        
        if Unit.objects.filter(symbol=symbol).exists():
            return JsonResponse({'success': False, 'error': 'Единица измерения с таким символом уже существует'})
        
        # Создание единицы измерения
        unit = Unit.objects.create(
            name=name,
            symbol=symbol,
            description=description
        )
        
        return JsonResponse({
            'success': True,
            'unit': {
                'id': unit.id,
                'name': unit.name,
                'symbol': unit.symbol,
                'display': f'{unit.name} ({unit.symbol})'
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Неверный формат данных'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Ошибка при создании единицы измерения: {str(e)}'})


def import_from_excel(request):
    """Импорт показателей из Excel файла"""
    templates = ImportTemplate.objects.all().order_by('-updated_at')
    
    if request.method == 'POST':
        if 'excel_file' not in request.FILES:
            messages.error(request, 'Файл не выбран')
            return render(request, 'indicators/import.html', {
                'templates': templates,
                'units': Unit.objects.all().order_by('name')
            })
        
        excel_file = request.FILES['excel_file']
        
        # Определяем, используется ли сохраненный шаблон
        template_id = request.POST.get('template_id')
        template = None
        if template_id:
            try:
                template = ImportTemplate.objects.get(pk=template_id)
            except ImportTemplate.DoesNotExist:
                messages.warning(request, 'Выбранный шаблон не найден, используются параметры формы')
        
        # Параметры из формы (переопределяют шаблон)
        sheet_name = request.POST.get('sheet_name', '').strip() or None
        column = request.POST.get('column', 'M').strip().upper()
        start_row = int(request.POST.get('start_row', 2))
        
        # Сохраняем файл временно
        file_path = default_storage.save(
            f'temp_import_{excel_file.name}',
            ContentFile(excel_file.read())
        )
        full_path = default_storage.path(file_path)
        
        try:
            # Парсим файл
            result = parse_indicators_from_excel(
                file_path=full_path,
                template=template,
                sheet_name=sheet_name if sheet_name else None,
                indicator_column=column,
                start_row=start_row
            )
            
            if result['success']:
                messages.success(
                    request,
                    f'Импорт завершен успешно! Создано: {result["created"]}, '
                    f'Обновлено: {result["updated"]}'
                )
                if result['warnings']:
                    for warning in result['warnings']:
                        messages.warning(request, warning)
            else:
                messages.error(request, 'Ошибки при импорте:')
                for error in result['errors']:
                    messages.error(request, error)
            
        except Exception as e:
            messages.error(request, f'Ошибка при обработке файла: {str(e)}')
        finally:
            # Удаляем временный файл
            if default_storage.exists(file_path):
                default_storage.delete(file_path)
        
        return redirect('indicators:import_from_excel')
    
    context = {
        'templates': templates
    }
    return render(request, 'indicators/import.html', context)


def import_template_create(request):
    """Создание шаблона импорта"""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        sheet_name = request.POST.get('sheet_name', '').strip() or None
        indicator_column = request.POST.get('indicator_column', 'M').strip().upper()
        start_row = int(request.POST.get('start_row', 2))
        
        if not name:
            messages.error(request, 'Название шаблона обязательно')
            return render(request, 'indicators/import_template_form.html', {})
        
        try:
            template = ImportTemplate.objects.create(
                name=name,
                description=description,
                sheet_name=sheet_name,
                indicator_column=indicator_column,
                start_row=start_row,
                default_unit=None,  # Единица измерения больше не используется в импорте
                created_by=request.user if request.user.is_authenticated else None
            )
            
            messages.success(request, f'Шаблон "{template.name}" успешно создан!')
            return redirect('indicators:import_from_excel')
            
        except Exception as e:
            messages.error(request, f'Ошибка при создании шаблона: {str(e)}')
    
    return render(request, 'indicators/import_template_form.html', {})


def import_template_edit(request, pk):
    """Редактирование шаблона импорта"""
    template = get_object_or_404(ImportTemplate, pk=pk)
    
    if request.method == 'POST':
        template.name = request.POST.get('name', '').strip()
        template.description = request.POST.get('description', '').strip()
        template.sheet_name = request.POST.get('sheet_name', '').strip() or None
        template.indicator_column = request.POST.get('indicator_column', 'M').strip().upper()
        template.start_row = int(request.POST.get('start_row', 2))
        
        if not template.name:
            messages.error(request, 'Название шаблона обязательно')
            return render(request, 'indicators/import_template_form.html', {
                'template': template
            })
        
        try:
            template.default_unit = None  # Единица измерения больше не используется в импорте
            template.save()
            messages.success(request, f'Шаблон "{template.name}" успешно обновлен!')
            return redirect('indicators:import_from_excel')
            
        except Exception as e:
            messages.error(request, f'Ошибка при обновлении шаблона: {str(e)}')
    
    return render(request, 'indicators/import_template_form.html', {
        'template': template
    })


def import_template_delete(request, pk):
    """Удаление шаблона импорта"""
    template = get_object_or_404(ImportTemplate, pk=pk)
    
    if request.method == 'POST':
        template_name = template.name
        template.delete()
        messages.success(request, f'Шаблон "{template_name}" успешно удален!')
        return redirect('indicators:import_from_excel')
    
    return render(request, 'indicators/import_template_delete.html', {
        'template': template
    })


def clear_indicator_values(request, pk):
    """Очистка всех значений конкретного показателя"""
    indicator = get_object_or_404(Indicator, pk=pk)
    
    if request.method == 'POST':
        try:
            values_count = indicator.values.count()
            indicator.values.all().delete()
            messages.success(
                request,
                f'Все значения показателя "{indicator.name}" удалены! Удалено записей: {values_count}'
            )
        except Exception as e:
            messages.error(request, f'Ошибка при удалении значений: {str(e)}')
        
        return redirect('indicators:indicator_detail', pk=indicator.pk)
    
    # GET запрос - показываем подтверждение
    context = {
        'indicator': indicator,
        'values_count': indicator.values.count(),
    }
    return render(request, 'indicators/clear_indicator_values.html', context)


def clear_data(request):
    """Страница управления очисткой базы данных"""
    from django.db import transaction
    
    # Подсчитываем количество записей
    units_count = Unit.objects.count()
    indicators_count = Indicator.objects.count()
    values_count = IndicatorValue.objects.count()
    templates_count = ImportTemplate.objects.count()
    
    total_count = units_count + indicators_count + values_count + templates_count
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        try:
            with transaction.atomic():
                if action == 'clear_all':
                    # Очистка всей базы
                    deleted_values = IndicatorValue.objects.all().delete()
                    deleted_templates = ImportTemplate.objects.all().delete()
                    deleted_indicators = Indicator.objects.all().delete()
                    deleted_units = Unit.objects.all().delete()
                    
                    messages.success(
                        request,
                        f'Вся база данных очищена! Удалено: '
                        f'{deleted_values[0]} значений, '
                        f'{deleted_templates[0]} шаблонов, '
                        f'{deleted_indicators[0]} показателей, '
                        f'{deleted_units[0]} единиц измерения.'
                    )
                    
                elif action == 'clear_values':
                    # Очистка только значений
                    deleted = IndicatorValue.objects.all().delete()
                    messages.success(
                        request,
                        f'Все значения показателей удалены! Удалено записей: {deleted[0]}'
                    )
                    
                elif action == 'clear_indicators':
                    # Очистка реестра показателей
                    deleted_values = IndicatorValue.objects.all().delete()
                    deleted_indicators = Indicator.objects.all().delete()
                    
                    messages.success(
                        request,
                        f'Реестр показателей очищен! Удалено: '
                        f'{deleted_indicators[0]} показателей и '
                        f'{deleted_values[0]} значений. '
                        f'Единицы измерения и шаблоны импорта сохранены.'
                    )
                    
                else:
                    messages.error(request, 'Неверное действие')
                    return redirect('indicators:clear_data')
                    
        except Exception as e:
            messages.error(request, f'Ошибка при очистке базы данных: {str(e)}')
        
        return redirect('indicators:clear_data')
    
    context = {
        'units_count': units_count,
        'indicators_count': indicators_count,
        'values_count': values_count,
        'templates_count': templates_count,
        'total_count': total_count,
    }
    return render(request, 'indicators/clear_data.html', context)
