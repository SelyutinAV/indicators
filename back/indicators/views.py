from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import json
from .models import Unit, Indicator, IndicatorValue
from .generators import generate_test_values
from .formula_parser import parse_formula, validate_formula_dependencies
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
