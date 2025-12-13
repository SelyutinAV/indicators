from django.contrib import admin
from .models import Dashboard, DashboardIndicator


class DashboardIndicatorInline(admin.TabularInline):
    """Инлайн для показателей на панели"""
    model = DashboardIndicator
    extra = 1
    fields = ['indicator', 'chart_type', 'order', 'days_back', 'aggregation_period']
    ordering = ['order']


@admin.register(Dashboard)
class DashboardAdmin(admin.ModelAdmin):
    """Админка для дашбордов"""
    list_display = ['name', 'is_public', 'order', 'created_by', 'created_at']
    list_filter = ['is_public', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [DashboardIndicatorInline]
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'description', 'is_public', 'order')
        }),
        ('Служебная информация', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(DashboardIndicator)
class DashboardIndicatorAdmin(admin.ModelAdmin):
    """Админка для показателей на панели"""
    list_display = ['dashboard', 'indicator', 'chart_type', 'order']
    list_filter = ['chart_type', 'dashboard']
    search_fields = ['dashboard__name', 'indicator__name']
