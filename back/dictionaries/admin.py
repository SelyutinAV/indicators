from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import Dictionary, DictionaryItem


class DictionaryItemInline(admin.TabularInline):
    """Инлайн для отображения элементов справочника"""
    model = DictionaryItem
    extra = 1
    fields = ['name', 'code', 'description', 'sort_order', 'is_active']
    ordering = ['sort_order', 'name']


@admin.register(Dictionary)
class DictionaryAdmin(admin.ModelAdmin):
    """Админка для справочников"""
    list_display = ['name', 'code', 'items_count', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'code', 'description']
    readonly_fields = ['created_at', 'updated_at']
    prepopulated_fields = {'code': ('name',)}
    inlines = [DictionaryItemInline]
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'code', 'description', 'is_active')
        }),
        ('Служебная информация', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def items_count(self, obj):
        """Количество элементов справочника"""
        count = obj.items.count()
        url = reverse('admin:dictionaries_dictionaryitem_changelist')
        return format_html(
            '<a href="{}?dictionary__id__exact={}">{}</a>',
            url,
            obj.id,
            count
        )
    items_count.short_description = 'Количество элементов'


@admin.register(DictionaryItem)
class DictionaryItemAdmin(admin.ModelAdmin):
    """Админка для элементов справочника"""
    list_display = ['name', 'dictionary', 'code', 'sort_order', 'is_active', 'created_at']
    list_filter = ['dictionary', 'is_active', 'created_at']
    search_fields = ['name', 'code', 'description', 'dictionary__name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('dictionary', 'name', 'code', 'description')
        }),
        ('Настройки', {
            'fields': ('sort_order', 'is_active')
        }),
        ('Служебная информация', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('dictionary')
