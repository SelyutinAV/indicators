from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.exceptions import ValidationError
from .models import Dictionary, DictionaryItem


def dictionaries_list(request):
    """Список всех справочников"""
    dictionaries = Dictionary.objects.filter(is_active=True).prefetch_related('items')
    
    # Поиск
    search_query = request.GET.get('search', '')
    if search_query:
        dictionaries = dictionaries.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(code__icontains=search_query)
        )
    
    # Пагинация
    paginator = Paginator(dictionaries, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'total_count': dictionaries.count(),
    }
    return render(request, 'dictionaries/list.html', context)


def dictionary_detail(request, pk):
    """Детальная страница справочника с элементами"""
    dictionary = get_object_or_404(Dictionary, pk=pk)
    
    # Получаем элементы справочника
    items = dictionary.items.filter(is_active=True).order_by('sort_order', 'name')
    
    # Поиск по элементам
    search_query = request.GET.get('search', '')
    if search_query:
        items = items.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(code__icontains=search_query)
        )
    
    # Пагинация элементов
    paginator = Paginator(items, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'dictionary': dictionary,
        'page_obj': page_obj,
        'search_query': search_query,
    }
    return render(request, 'dictionaries/detail.html', context)


def dictionary_create(request):
    """Создание нового справочника"""
    if request.method == 'POST':
        name = request.POST.get('name')
        code = request.POST.get('code')
        description = request.POST.get('description', '')
        
        try:
            dictionary = Dictionary.objects.create(
                name=name,
                code=code,
                description=description
            )
            messages.success(request, f'Справочник "{dictionary.name}" успешно создан')
            return redirect('dictionaries:detail', pk=dictionary.pk)
        except Exception as e:
            messages.error(request, f'Ошибка при создании справочника: {str(e)}')
    
    return render(request, 'dictionaries/create.html')


def dictionary_item_create(request, dictionary_pk):
    """Создание элемента справочника"""
    dictionary = get_object_or_404(Dictionary, pk=dictionary_pk)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        code = request.POST.get('code', '')
        description = request.POST.get('description', '')
        sort_order = int(request.POST.get('sort_order', 0))
        
        try:
            item = DictionaryItem(
                dictionary=dictionary,
                name=name,
                code=code,
                description=description,
                sort_order=sort_order
            )
            item.full_clean()
            item.save()
            messages.success(request, f'Элемент "{item.name}" успешно добавлен')
            return redirect('dictionaries:detail', pk=dictionary.pk)
        except ValidationError as e:
            for field, errors in e.error_dict.items():
                for error in errors:
                    messages.error(request, f'{field}: {error.message}')
        except Exception as e:
            messages.error(request, f'Ошибка при создании элемента: {str(e)}')
    
    context = {
        'dictionary': dictionary,
    }
    return render(request, 'dictionaries/item_create.html', context)


def dictionary_item_edit(request, pk):
    """Редактирование элемента справочника"""
    item = get_object_or_404(DictionaryItem, pk=pk)
    
    if request.method == 'POST':
        item.name = request.POST.get('name')
        item.code = request.POST.get('code', '')
        item.description = request.POST.get('description', '')
        item.sort_order = int(request.POST.get('sort_order', 0))
        
        try:
            item.full_clean()
            item.save()
            messages.success(request, f'Элемент "{item.name}" успешно обновлен')
            return redirect('dictionaries:detail', pk=item.dictionary.pk)
        except ValidationError as e:
            for field, errors in e.error_dict.items():
                for error in errors:
                    messages.error(request, f'{field}: {error.message}')
        except Exception as e:
            messages.error(request, f'Ошибка при обновлении: {str(e)}')
    
    context = {
        'item': item,
        'dictionary': item.dictionary,
    }
    return render(request, 'dictionaries/item_edit.html', context)


def dictionary_delete(request, pk):
    """Удаление справочника"""
    dictionary = get_object_or_404(Dictionary, pk=pk)
    
    if request.method == 'POST':
        dictionary_name = dictionary.name
        dictionary.delete()
        messages.success(request, f'Справочник "{dictionary_name}" успешно удален')
        return redirect('dictionaries:list')
    
    context = {
        'dictionary': dictionary,
    }
    return render(request, 'dictionaries/delete.html', context)


def dictionary_item_delete(request, pk):
    """Удаление элемента справочника"""
    item = get_object_or_404(DictionaryItem, pk=pk)
    dictionary_pk = item.dictionary.pk
    
    if request.method == 'POST':
        item.delete()
        messages.success(request, 'Элемент успешно удален')
        return redirect('dictionaries:detail', pk=dictionary_pk)
    
    context = {
        'item': item,
    }
    return render(request, 'dictionaries/item_delete.html', context)


@require_http_methods(["GET"])
def dictionary_items_api(request, dictionary_pk):
    """API для получения элементов справочника (для AJAX)"""
    dictionary = get_object_or_404(Dictionary, pk=dictionary_pk)
    items = dictionary.items.filter(is_active=True).order_by('sort_order', 'name')
    
    data = [{
        'id': item.id,
        'name': item.name,
        'code': item.code,
        'description': item.description,
    } for item in items]
    
    return JsonResponse({'items': data})
