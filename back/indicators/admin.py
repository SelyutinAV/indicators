from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from django import forms
from datetime import date, timedelta
from .models import Unit, Indicator, IndicatorValue, ImportTemplate, UserDictionaryFilter, IndicatorDictionary
from .generators import generate_test_values
from .formula_parser import validate_formula_dependencies, parse_formula


class IndicatorValueInline(admin.TabularInline):
    """Инлайн для отображения значений показателя"""
    model = IndicatorValue
    extra = 0
    readonly_fields = ['created_at']
    fields = ['date', 'value', 'created_at']
    ordering = ['-date']


class IndicatorAdminForm(forms.ModelForm):
    """Форма для админки показателя с дополнительными полями для генерации"""
    generate_start_date = forms.DateField(
        label='Начальная дата для генерации',
        required=False,
        initial=date.today() - timedelta(days=30),
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    generate_end_date = forms.DateField(
        label='Конечная дата для генерации',
        required=False,
        initial=date.today(),
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    generate_data = forms.BooleanField(
        label='Сгенерировать тестовые данные',
        required=False,
        help_text='Отметьте и сохраните, чтобы сгенерировать тестовые данные'
    )

    class Meta:
        model = Indicator
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        indicator_type = cleaned_data.get('indicator_type')
        formula = cleaned_data.get('formula')
        
        # Валидация формулы
        if indicator_type == 'aggregate' and formula:
            # Создаем временный объект для валидации
            temp_indicator = Indicator(
                name=cleaned_data.get('name', 'temp'),
                indicator_type=indicator_type,
                formula=formula
            )
            if self.instance.pk:
                temp_indicator.id = self.instance.pk
            
            is_valid, errors = validate_formula_dependencies(temp_indicator)
            if not is_valid:
                raise forms.ValidationError({
                    'formula': '; '.join(errors)
                })
        
        return cleaned_data


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    """Админка для единиц измерения"""
    list_display = ['name', 'symbol', 'description_short']
    search_fields = ['name', 'symbol']
    list_filter = ['name']
    
    def description_short(self, obj):
        return obj.description[:50] + '...' if len(obj.description) > 50 else obj.description
    description_short.short_description = 'Описание'


@admin.register(Indicator)
class IndicatorAdmin(admin.ModelAdmin):
    """Админка для показателей"""
    form = IndicatorAdminForm
    list_display = [
        'name',
        'indicator_type_display',
        'unit',
        'has_formula',
        'values_count',
        'last_value_date',
        'actions_column'
    ]
    list_filter = ['indicator_type', 'unit', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at', 'formula_help', 'dependencies_list']
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'description', 'indicator_type', 'unit')
        }),
        ('Пороговые значения для оценки качества', {
            'fields': ('direction', 'unacceptable_value', 'acceptable_value', 'good_value'),
            'description': 'Укажите направление показателя и пороговые значения для определения качества. Для растущего: недопустимое < приемлемое < хорошее. Для снижающегося: хорошее < приемлемое < недопустимое.'
        }),
        ('Генерация тестовых данных', {
            'fields': ('min_value', 'max_value', 'generate_start_date', 'generate_end_date', 'generate_data'),
            'description': 'Укажите минимальное и максимальное значение для генерации тестовых данных. Затем укажите диапазон дат и отметьте чекбокс для генерации.',
            'classes': ('collapse',)
        }),
        ('Формула (только для агрегатных показателей)', {
            'fields': ('formula', 'formula_help', 'dependencies_list'),
            'description': 'Используйте названия показателей в квадратных скобках, например: [Показатель1] + [Показатель2] / [Показатель3]'
        }),
        ('Служебная информация', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    inlines = [IndicatorValueInline]
    
    def indicator_type_display(self, obj):
        colors = {
            'atomic': 'green',
            'aggregate': 'blue'
        }
        color = colors.get(obj.indicator_type, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_indicator_type_display()
        )
    indicator_type_display.short_description = 'Тип'
    
    def has_formula(self, obj):
        if obj.indicator_type == 'aggregate':
            return '✓' if obj.formula else '✗'
        return '-'
    has_formula.short_description = 'Формула'
    
    def values_count(self, obj):
        count = obj.values.count()
        if count > 0:
            url = reverse('admin:indicators_indicatorvalue_changelist')
            return format_html(
                '<a href="{}?indicator__id__exact={}">{}</a>',
                url,
                obj.id,
                count
            )
        return count
    values_count.short_description = 'Кол-во значений'
    
    def last_value_date(self, obj):
        last_value = obj.values.order_by('-date').first()
        if last_value:
            return last_value.date
        return '-'
    last_value_date.short_description = 'Последнее значение'
    
    def formula_help(self, obj):
        if obj.indicator_type == 'aggregate':
            return format_html(
                '<div style="background: #f0f0f0; padding: 10px; border-radius: 5px;">'
                '<strong>Примеры формул:</strong><br>'
                '[Показатель1] + [Показатель2]<br>'
                '[Показатель1] * 100 / [Показатель2]<br>'
                '([Показатель1] + [Показатель2]) / 2<br>'
                '</div>'
            )
        return ''
    formula_help.short_description = 'Справка по формулам'
    
    def dependencies_list(self, obj):
        if obj.indicator_type == 'aggregate' and obj.formula:
            dependencies = parse_formula(obj.formula)
            if dependencies:
                html = '<strong>Зависимости:</strong><ul>'
                for dep in dependencies:
                    try:
                        dep_obj = Indicator.objects.get(name=dep)
                        url = reverse('admin:indicators_indicator_change', args=[dep_obj.id])
                        html += f'<li><a href="{url}">{dep}</a></li>'
                    except Indicator.DoesNotExist:
                        html += f'<li style="color: red;">{dep} (не найден)</li>'
                html += '</ul>'
                return format_html(html)
            return 'Нет зависимостей'
        return ''
    dependencies_list.short_description = 'Зависимости'
    
    def actions_column(self, obj):
        if obj.pk and obj.min_value and obj.max_value:
            url = reverse('admin:indicators_indicator_change', args=[obj.pk])
            return format_html(
                '<a href="{}#generation" class="button">Генерировать данные</a>',
                url
            )
        return '-'
    actions_column.short_description = 'Действия'
    
    def save_model(self, request, obj, form, change):
        """Переопределяем сохранение для генерации данных"""
        generate_data = form.cleaned_data.get('generate_data', False)
        generate_start_date = form.cleaned_data.get('generate_start_date')
        generate_end_date = form.cleaned_data.get('generate_end_date')
        
        # Сохраняем объект
        super().save_model(request, obj, form, change)
        
        # Генерируем данные, если запрошено
        if generate_data and generate_start_date and generate_end_date:
            if obj.min_value and obj.max_value:
                try:
                    count = generate_test_values(obj, generate_start_date, generate_end_date)
                    self.message_user(
                        request,
                        f'Успешно сгенерировано {count} значений для показателя "{obj.name}"',
                        level='success'
                    )
                except Exception as e:
                    self.message_user(
                        request,
                        f'Ошибка при генерации данных: {str(e)}',
                        level='error'
                    )
            else:
                self.message_user(
                    request,
                    'Для генерации данных необходимо указать min_value и max_value',
                    level='warning'
                )


@admin.register(IndicatorValue)
class IndicatorValueAdmin(admin.ModelAdmin):
    """Админка для значений показателей"""
    list_display = ['indicator', 'date', 'value', 'created_at']
    list_filter = ['indicator', 'date', 'created_at']
    search_fields = ['indicator__name']
    date_hierarchy = 'date'
    ordering = ['-date', 'indicator']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('indicator')


@admin.register(ImportTemplate)
class ImportTemplateAdmin(admin.ModelAdmin):
    """Админка для шаблонов импорта"""
    list_display = ['name', 'indicator_column', 'start_row', 'sheet_name', 'default_unit', 'created_at', 'updated_at']
    list_filter = ['created_at', 'updated_at', 'default_unit']
    search_fields = ['name', 'description', 'sheet_name']
    readonly_fields = ['created_at', 'updated_at', 'created_by']
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'description')
        }),
        ('Настройки парсинга', {
            'fields': ('sheet_name', 'indicator_column', 'start_row', 'default_unit')
        }),
        ('Служебная информация', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:  # Если создается новый объект
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(UserDictionaryFilter)
class UserDictionaryFilterAdmin(admin.ModelAdmin):
    """Админка для фильтров пользователей по справочникам"""
    list_display = ['user', 'dictionary', 'is_required', 'items_count']
    list_filter = ['is_required', 'dictionary']
    search_fields = ['user__username', 'user__email', 'dictionary__name']
    filter_horizontal = ['items']
    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'dictionary', 'is_required')
        }),
        ('Элементы справочника', {
            'fields': ('items',),
            'description': 'Выберите элементы справочника для фильтрации. Если пусто и обязательный фильтр включен - пользователь не видит данные по этому справочнику.'
        }),
    )
    
    def items_count(self, obj):
        return obj.items.count()
    items_count.short_description = 'Кол-во элементов'


@admin.register(IndicatorDictionary)
class IndicatorDictionaryAdmin(admin.ModelAdmin):
    """Админка для связи показателей со справочниками"""
    list_display = ['indicator', 'dictionary', 'is_required']
    list_filter = ['is_required', 'dictionary']
    search_fields = ['indicator__name', 'dictionary__name']
    list_editable = ['is_required']
