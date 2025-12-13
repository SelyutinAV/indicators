from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db.models import Q
from .models import Dashboard, DashboardIndicator
from indicators.models import Indicator, IndicatorDictionary
from .utils import get_indicator_data
import json


def dashboard_list(request):
    """Список дашбордов"""
    dashboards = Dashboard.objects.all().order_by('order', 'name')
    return render(request, 'visualization/list.html', {'dashboards': dashboards})


def dashboard_detail(request, pk):
    """Детальная страница дашборда"""
    from dictionaries.models import Dictionary, DictionaryItem
    from indicators.models import IndicatorDictionary
    
    dashboard = get_object_or_404(Dashboard, pk=pk)
    
    # Проверка доступа
    if not dashboard.is_public and dashboard.created_by != request.user and not request.user.is_superuser:
        messages.error(request, 'У вас нет доступа к этой панели')
        return redirect('visualization:dashboard_list')
    
    # Получаем показатели на панели
    indicators = dashboard.indicators.select_related('indicator', 'indicator__unit').order_by('order')
    
    # Собираем все уникальные справочники из показателей на панели
    all_dictionaries = {}
    for dashboard_indicator in indicators:
        indicator_dicts = IndicatorDictionary.objects.filter(
            indicator=dashboard_indicator.indicator,
            dictionary__is_active=True
        ).select_related('dictionary').prefetch_related('dictionary__items')
        
        for ind_dict in indicator_dicts:
            dict_id = ind_dict.dictionary.id
            if dict_id not in all_dictionaries:
                all_dictionaries[dict_id] = {
                    'dictionary': ind_dict.dictionary,
                    'items': list(ind_dict.dictionary.items.filter(is_active=True).order_by('name'))
                }
    
    # Получаем выбранные фильтры из GET-параметров
    from datetime import date
    
    start_date_filter = request.GET.get('start_date', '')
    end_date_filter = request.GET.get('end_date', '')
    
    # Устанавливаем значения по умолчанию: с начала текущего года до сегодня
    if not start_date_filter:
        start_date_filter = date.today().replace(month=1, day=1).isoformat()
    if not end_date_filter:
        end_date_filter = date.today().isoformat()
    
    selected_items_by_dict = {}
    
    for dict_id in all_dictionaries.keys():
        dict_key = f"dict_{dict_id}"
        selected_item_ids = request.GET.getlist(dict_key)
        try:
            selected_items_by_dict[dict_id] = [
                int(item_id) for item_id in selected_item_ids 
                if item_id and item_id.isdigit() and item_id != 'all'
            ]
        except (ValueError, TypeError):
            selected_items_by_dict[dict_id] = []
    
    return render(request, 'visualization/detail.html', {
        'dashboard': dashboard,
        'indicators': indicators,
        'all_dictionaries': all_dictionaries,
        'start_date_filter': start_date_filter,
        'end_date_filter': end_date_filter,
        'selected_items_by_dict': selected_items_by_dict,
    })


@login_required
def dashboard_create(request):
    """Создание дашборда"""
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        is_public = request.POST.get('is_public') == 'on'
        
        dashboard = Dashboard.objects.create(
            name=name,
            description=description,
            is_public=is_public,
            created_by=request.user
        )
        messages.success(request, f'Дашборд "{dashboard.name}" успешно создан!')
        return redirect('visualization:dashboard_detail', pk=dashboard.pk)
    
    return render(request, 'visualization/create.html')


@login_required
def dashboard_edit(request, pk):
    """Редактирование дашборда"""
    dashboard = get_object_or_404(Dashboard, pk=pk)
    
    # Проверка прав
    if dashboard.created_by != request.user and not request.user.is_superuser:
        messages.error(request, 'У вас нет прав для редактирования этой панели')
        return redirect('visualization:dashboard_detail', pk=pk)
    
    if request.method == 'POST':
        dashboard.name = request.POST.get('name')
        dashboard.description = request.POST.get('description', '')
        dashboard.is_public = request.POST.get('is_public') == 'on'
        order = int(request.POST.get('order', 0) or 0)
        dashboard.order = order
        dashboard.save()
        messages.success(request, f'Дашборд "{dashboard.name}" успешно обновлен!')
        return redirect('visualization:dashboard_detail', pk=dashboard.pk)
    
    # Получаем показатели на панели
    indicators = dashboard.indicators.select_related('indicator', 'indicator__unit').order_by('order')
    
    # Получаем все доступные показатели, исключая уже добавленные
    added_indicator_ids = indicators.values_list('indicator_id', flat=True)
    all_indicators = Indicator.objects.exclude(id__in=added_indicator_ids).select_related('unit').order_by('name')
    
    return render(request, 'visualization/edit.html', {
        'dashboard': dashboard,
        'indicators': indicators,
        'all_indicators': all_indicators,
    })


@require_http_methods(["GET"])
def api_indicator_data(request, indicator_id):
    """
    API endpoint для получения данных показателя для визуализации.
    
    Параметры:
        days_back (int): количество дней назад (по умолчанию 30)
        start_date (str): начальная дата (ISO формат, приоритет над days_back)
        end_date (str): конечная дата (ISO формат)
        aggregation (str): период агрегации (day/week/month/quarter/year)
        filters (str): JSON строка с фильтрами по справочникам
    """
    from datetime import date
    
    indicator = get_object_or_404(Indicator, pk=indicator_id)
    
    # Параметры из запроса
    days_back = int(request.GET.get('days_back', 30))
    start_date_str = request.GET.get('start_date', '')
    end_date_str = request.GET.get('end_date', '')
    aggregation = request.GET.get('aggregation', 'day')
    filters_str = request.GET.get('filters', '{}')
    
    # Определяем период данных
    if start_date_str:
        try:
            start_date = date.fromisoformat(start_date_str)
            # Вычисляем days_back на основе start_date
            days_back = (date.today() - start_date).days
        except (ValueError, TypeError):
            pass
    
    # Парсим фильтры
    dictionary_filters = {}
    try:
        if filters_str:
            dictionary_filters = json.loads(filters_str)
    except json.JSONDecodeError:
        dictionary_filters = {}
    
    # Получаем данные
    try:
        data = get_indicator_data(
            indicator=indicator,
            days_back=days_back,
            aggregation_period=aggregation if aggregation != 'day' else None,
            dictionary_filters=dictionary_filters,
            end_date=end_date_str if end_date_str else None
        )
        
        return JsonResponse({
            'success': True,
            'indicator': {
                'id': indicator.id,
                'name': indicator.name,
                'unit': indicator.unit.symbol,
                'description': indicator.description
            },
            'data': data
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@login_required
@require_http_methods(["POST"])
def dashboard_indicator_add(request, pk):
    """Добавление показателя на панель"""
    dashboard = get_object_or_404(Dashboard, pk=pk)
    
    # Проверка прав
    if dashboard.created_by != request.user and not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': 'Нет прав для редактирования панели'}, status=403)
    
    try:
        data = json.loads(request.body)
        indicator_id = data.get('indicator_id')
        chart_type = data.get('chart_type', 'line')
        order = int(data.get('order', 0) or 0)
        days_back = int(data.get('days_back', 30) or 30)
        aggregation_period = data.get('aggregation_period') or None
        show_legend = data.get('show_legend', True)
        show_grid = data.get('show_grid', True)
        height = int(data.get('height', 400) or 400)
        
        if not indicator_id:
            return JsonResponse({'success': False, 'error': 'Не указан показатель'}, status=400)
        
        indicator = Indicator.objects.get(pk=indicator_id)
        
        # Проверяем, не добавлен ли уже этот показатель
        if DashboardIndicator.objects.filter(dashboard=dashboard, indicator=indicator).exists():
            return JsonResponse({'success': False, 'error': 'Показатель уже добавлен на панель'}, status=400)
        
        # Создаем связь
        dashboard_indicator = DashboardIndicator.objects.create(
            dashboard=dashboard,
            indicator=indicator,
            chart_type=chart_type,
            order=order,
            days_back=days_back,
            aggregation_period=aggregation_period,
            show_legend=show_legend,
            show_grid=show_grid,
            height=height
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Показатель успешно добавлен',
            'dashboard_indicator': {
                'id': dashboard_indicator.id,
                'indicator_name': indicator.name,
                'chart_type': chart_type
            }
        })
        
    except Indicator.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Показатель не найден'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Неверный формат данных'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def dashboard_indicator_update(request, pk, indicator_id):
    """Обновление настроек показателя на панели"""
    dashboard = get_object_or_404(Dashboard, pk=pk)
    dashboard_indicator = get_object_or_404(DashboardIndicator, dashboard=dashboard, pk=indicator_id)
    
    # Проверка прав
    if dashboard.created_by != request.user and not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': 'Нет прав для редактирования панели'}, status=403)
    
    try:
        data = json.loads(request.body)
        
        # Обновляем поля
        if 'chart_type' in data:
            dashboard_indicator.chart_type = data['chart_type']
        if 'order' in data:
            dashboard_indicator.order = int(data['order'] or 0)
        if 'days_back' in data:
            dashboard_indicator.days_back = int(data['days_back'] or 30)
        if 'aggregation_period' in data:
            dashboard_indicator.aggregation_period = data['aggregation_period'] or None
        if 'show_legend' in data:
            dashboard_indicator.show_legend = bool(data['show_legend'])
        if 'show_grid' in data:
            dashboard_indicator.show_grid = bool(data['show_grid'])
        if 'height' in data:
            dashboard_indicator.height = int(data['height'] or 400)
        
        dashboard_indicator.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Настройки показателя обновлены'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Неверный формат данных'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def dashboard_indicator_delete(request, pk, indicator_id):
    """Удаление показателя с панели"""
    dashboard = get_object_or_404(Dashboard, pk=pk)
    dashboard_indicator = get_object_or_404(DashboardIndicator, dashboard=dashboard, pk=indicator_id)
    
    # Проверка прав
    if dashboard.created_by != request.user and not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': 'Нет прав для редактирования панели'}, status=403)
    
    indicator_name = dashboard_indicator.indicator.name
    dashboard_indicator.delete()
    
    return JsonResponse({
        'success': True,
        'message': f'Показатель "{indicator_name}" удален с панели'
    })
