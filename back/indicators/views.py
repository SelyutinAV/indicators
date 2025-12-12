from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import json
from .models import Unit, Indicator, IndicatorValue, ImportTemplate
from .generators import generate_test_values
from .formula_parser import parse_formula, validate_formula_dependencies
from .excel_parser import parse_indicators_from_excel
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from datetime import date, timedelta


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
    
    context = {
        'indicator': indicator,
        'values': values,
        'dependencies': dependencies,
    }
    return render(request, 'indicators/detail.html', context)


def indicator_create(request):
    """Создание нового показателя"""
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        indicator_type = request.POST.get('indicator_type')
        unit_id = request.POST.get('unit')
        direction = request.POST.get('direction', 'increasing')
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
        
        try:
            start_date = date.fromisoformat(start_date_str)
            end_date = date.fromisoformat(end_date_str)
            
            if not indicator.min_value or not indicator.max_value:
                messages.error(request, 'Необходимо указать минимальное и максимальное значение для генерации данных')
                return redirect('indicators:indicator_detail', pk=indicator.pk)
            
            count = generate_test_values(indicator, start_date, end_date)
            messages.success(request, f'Успешно сгенерировано {count} значений!')
            
        except Exception as e:
            messages.error(request, f'Ошибка при генерации данных: {str(e)}')
    
    return redirect('indicators:indicator_detail', pk=indicator.pk)


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
