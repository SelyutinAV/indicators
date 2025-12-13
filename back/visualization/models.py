from django.db import models
from django.conf import settings
from indicators.models import Indicator


class Dashboard(models.Model):
    """Панель визуализации"""
    name = models.CharField('Название', max_length=200)
    description = models.TextField('Описание', blank=True)
    is_public = models.BooleanField(
        'Публичная',
        default=False,
        help_text='Если включено, панель видна всем пользователям'
    )
    order = models.IntegerField('Порядок', default=0)
    created_at = models.DateTimeField('Создан', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлен', auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        verbose_name='Создатель'
    )

    class Meta:
        verbose_name = 'Панель визуализации'
        verbose_name_plural = 'Панели визуализации'
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class DashboardIndicator(models.Model):
    """Показатель на панели"""
    CHART_TYPE_CHOICES = [
        ('line', 'Линейный график'),
        ('bar', 'Столбчатая диаграмма'),
        ('area', 'Областной график'),
        ('scatter', 'Точечная диаграмма'),
        ('pie', 'Круговая диаграмма'),
        ('gauge', 'Индикатор (gauge)'),
        ('table', 'Таблица'),
    ]
    
    AGGREGATION_PERIOD_CHOICES = [
        ('day', 'День'),
        ('week', 'Неделя'),
        ('month', 'Месяц'),
        ('quarter', 'Квартал'),
        ('year', 'Год'),
    ]

    dashboard = models.ForeignKey(
        Dashboard,
        on_delete=models.CASCADE,
        related_name='indicators',
        verbose_name='Панель'
    )
    indicator = models.ForeignKey(
        Indicator,
        on_delete=models.CASCADE,
        verbose_name='Показатель'
    )
    chart_type = models.CharField(
        'Тип графика',
        max_length=20,
        choices=CHART_TYPE_CHOICES,
        default='line'
    )
    order = models.IntegerField('Порядок', default=0)
    days_back = models.IntegerField(
        'Дней назад',
        default=30,
        help_text='Сколько дней данных показывать'
    )
    aggregation_period = models.CharField(
        'Период агрегации',
        max_length=20,
        choices=AGGREGATION_PERIOD_CHOICES,
        blank=True,
        null=True,
        default='day',
        help_text='Если указан, данные будут агрегированы по этому периоду'
    )
    show_legend = models.BooleanField('Показывать легенду', default=True)
    show_grid = models.BooleanField('Показывать сетку', default=True)
    height = models.IntegerField('Высота (px)', default=400)
    dictionary_filters = models.JSONField(
        'Фильтры по справочникам',
        default=dict,
        blank=True,
        help_text='JSON объект с фильтрами по справочникам: {"dictionary_id": [item_id1, item_id2]}'
    )
    created_at = models.DateTimeField('Создан', auto_now_add=True)

    class Meta:
        verbose_name = 'Показатель на панели'
        verbose_name_plural = 'Показатели на панели'
        ordering = ['order', 'indicator__name']
        unique_together = [['dashboard', 'indicator']]

    def __str__(self):
        return f"{self.dashboard.name} - {self.indicator.name}"
