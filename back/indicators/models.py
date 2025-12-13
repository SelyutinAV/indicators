from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal
import re
from dictionaries.models import Dictionary, DictionaryItem


class Unit(models.Model):
    """Единица измерения"""
    name = models.CharField('Название', max_length=100, unique=True)
    symbol = models.CharField('Символ', max_length=20, unique=True)
    description = models.TextField('Описание', blank=True)

    class Meta:
        verbose_name = 'Единица измерения'
        verbose_name_plural = 'Единицы измерения'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.symbol})"


class Indicator(models.Model):
    """Показатель"""
    INDICATOR_TYPE_CHOICES = [
        ('atomic', 'Атомарный'),
        ('aggregate', 'Агрегатный'),
    ]

    name = models.CharField('Название', max_length=200)
    description = models.TextField('Описание', blank=True)
    indicator_type = models.CharField(
        'Тип показателя',
        max_length=20,
        choices=INDICATOR_TYPE_CHOICES,
        default='atomic'
    )
    unit = models.ForeignKey(
        Unit,
        on_delete=models.PROTECT,
        verbose_name='Единица измерения',
        related_name='indicators'
    )
    
    # Поля для генерации тестовых данных
    min_value = models.DecimalField(
        'Минимальное значение',
        max_digits=20,
        decimal_places=4,
        null=True,
        blank=True,
        help_text='Минимальное значение для генерации тестовых данных'
    )
    max_value = models.DecimalField(
        'Максимальное значение',
        max_digits=20,
        decimal_places=4,
        null=True,
        blank=True,
        help_text='Максимальное значение для генерации тестовых данных'
    )
    
    # Поле для формулы (только для агрегатных показателей)
    formula = models.TextField(
        'Формула',
        blank=True,
        help_text='Формула для расчета агрегатного показателя. Используйте названия показателей в квадратных скобках, например: [Показатель1] + [Показатель2] / [Показатель3]. Для агрегации за период используйте функции: SUM([Показатель], \'month\'), AVG([Показатель], \'quarter\') и т.д.'
    )
    
    # Направление показателя
    DIRECTION_CHOICES = [
        ('increasing', 'Растущий'),
        ('decreasing', 'Снижающийся'),
    ]
    
    direction = models.CharField(
        'Направление',
        max_length=20,
        choices=DIRECTION_CHOICES,
        default='increasing',
        help_text='Растущий - зеленый при росте выше хорошего значения, Снижающийся - зеленый при снижении ниже хорошего значения'
    )
    
    # Тип значения показателя
    VALUE_TYPE_CHOICES = [
        ('integer', 'Целое'),
        ('decimal', 'Дробное'),
    ]
    
    value_type = models.CharField(
        'Тип значения',
        max_length=20,
        choices=VALUE_TYPE_CHOICES,
        default='decimal',
        help_text='Целое - значения округляются до целых чисел, Дробное - значения могут быть дробными'
    )
    
    # Пороговые значения для оценки качества
    unacceptable_value = models.DecimalField(
        'Недопустимое значение',
        max_digits=20,
        decimal_places=4,
        null=True,
        blank=True,
        help_text='При переходе за это значение индикатор будет красным'
    )
    
    acceptable_value = models.DecimalField(
        'Приемлемое значение',
        max_digits=20,
        decimal_places=4,
        null=True,
        blank=True,
        help_text='Промежуточное значение (желтый индикатор)'
    )
    
    good_value = models.DecimalField(
        'Хорошее значение',
        max_digits=20,
        decimal_places=4,
        null=True,
        blank=True,
        help_text='При переходе за это значение индикатор будет зеленым'
    )
    
    # Справочники для разреза показателя (через промежуточную модель)
    dictionaries = models.ManyToManyField(
        Dictionary,
        through='IndicatorDictionary',
        verbose_name='Справочники',
        blank=True,
        help_text='Справочники, в разрезе которых ведется показатель'
    )
    
    aggregate_by_dimensions = models.BooleanField(
        'Агрегировать в разрезе справочников',
        default=False,
        help_text='Для агрегатных показателей: если включено, агрегирует только значения с одинаковыми комбинациями справочников. Если выключено, агрегирует все значения независимо от справочников.'
    )
    
    created_at = models.DateTimeField('Создан', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлен', auto_now=True)

    class Meta:
        verbose_name = 'Показатель'
        verbose_name_plural = 'Показатели'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.get_indicator_type_display()})"

    def clean(self):
        """Валидация модели"""
        if self.indicator_type == 'aggregate' and not self.formula:
            raise ValidationError({
                'formula': 'Для агрегатного показателя необходимо указать формулу'
            })
        
        if self.indicator_type == 'atomic' and self.formula:
            raise ValidationError({
                'formula': 'Атомарный показатель не может иметь формулу'
            })
        
        if self.min_value is not None and self.max_value is not None:
            if self.min_value >= self.max_value:
                raise ValidationError({
                    'max_value': 'Максимальное значение должно быть больше минимального'
                })
        
        # Валидация пороговых значений
        if all([self.unacceptable_value is not None, 
               self.acceptable_value is not None, 
               self.good_value is not None]):
            
            if self.direction == 'increasing':
                # Для растущего: unacceptable < acceptable < good
                if not (self.unacceptable_value < self.acceptable_value < self.good_value):
                    raise ValidationError({
                        'good_value': 'Для растущего показателя должно быть: недопустимое < приемлемое < хорошее'
                    })
            else:
                # Для снижающегося: good < acceptable < unacceptable
                if not (self.good_value < self.acceptable_value < self.unacceptable_value):
                    raise ValidationError({
                        'unacceptable_value': 'Для снижающегося показателя должно быть: хорошее < приемлемое < недопустимое'
                    })

    def get_value_status(self, value):
        """Определяет статус значения (green/yellow/red)"""
        if not all([self.unacceptable_value is not None, 
                   self.acceptable_value is not None, 
                   self.good_value is not None]):
            return None  # Пороговые значения не заданы
        
        if self.direction == 'increasing':
            # Растущий: чем больше, тем лучше
            if value >= self.good_value:
                return 'green'
            elif value >= self.acceptable_value:
                return 'yellow'
            else:
                return 'red'
        else:
            # Снижающийся: чем меньше, тем лучше
            if value <= self.good_value:
                return 'green'
            elif value <= self.acceptable_value:
                return 'yellow'
            else:
                return 'red'

    def get_indicators_in_formula(self):
        """Извлекает список показателей, используемых в формуле"""
        if not self.formula:
            return []
        
        # Ищем все вхождения [Название показателя]
        pattern = r'\[([^\]]+)\]'
        matches = re.findall(pattern, self.formula)
        return [match.strip() for match in matches]
    
    def get_dependencies(self):
        """
        Возвращает QuerySet показателей, от которых зависит данный показатель.
        Для агрегатных показателей возвращает все показатели, используемые в формуле.
        Для атомарных показателей возвращает пустой QuerySet.
        """
        if not self.formula or self.indicator_type != 'aggregate':
            return Indicator.objects.none()
        
        from .formula_parser import parse_formula
        indicator_names = parse_formula(self.formula)
        
        if not indicator_names:
            return Indicator.objects.none()
        
        return Indicator.objects.filter(name__in=indicator_names)

    def validate_formula(self):
        """Валидация формулы на циклические зависимости"""
        if not self.formula:
            return True, []
        
        visited = set()
        errors = []
        
        def check_dependencies(indicator, path):
            if indicator.id in visited:
                return True
            
            visited.add(indicator.id)
            path = path + [indicator.name]
            
            indicators_in_formula = indicator.get_indicators_in_formula()
            
            for indicator_name in indicators_in_formula:
                try:
                    dep_indicator = Indicator.objects.get(name=indicator_name)
                    if dep_indicator.id == self.id:
                        errors.append(f"Циклическая зависимость: {' -> '.join(path)} -> {self.name}")
                        return False
                    if dep_indicator.id in [p.id for p in path if hasattr(p, 'id')]:
                        errors.append(f"Циклическая зависимость обнаружена")
                        return False
                    if not check_dependencies(dep_indicator, path):
                        return False
                except Indicator.DoesNotExist:
                    errors.append(f"Показатель '{indicator_name}' не найден в формуле")
                    return False
            
            return True
        
        return check_dependencies(self, []), errors
    
    def save(self, *args, **kwargs):
        """Переопределяем save для автоматического добавления справочников из зависимостей"""
        # Сохраняем сначала, чтобы получить ID
        super().save(*args, **kwargs)
        
        # Для агрегатных показателей автоматически добавляем справочники из зависимостей
        if self.indicator_type == 'aggregate':
            dependencies = self.get_dependencies()
            for dep_indicator in dependencies:
                # Добавляем справочники дочернего показателя
                for dictionary in dep_indicator.dictionaries.all():
                    # Используем get_or_create для промежуточной модели
                    IndicatorDictionary.objects.get_or_create(
                        indicator=self,
                        dictionary=dictionary,
                        defaults={'is_required': False}
                    )


class IndicatorDictionary(models.Model):
    """Промежуточная модель для связи Indicator-Dictionary с настройками обязательности"""
    indicator = models.ForeignKey(
        Indicator,
        on_delete=models.CASCADE,
        verbose_name='Показатель'
    )
    dictionary = models.ForeignKey(
        Dictionary,
        on_delete=models.CASCADE,
        verbose_name='Справочник'
    )
    is_required = models.BooleanField(
        'Обязательность разреза',
        default=False,
        help_text='Если включено, каждое значение должно иметь элементы этого справочника. Если выключено, значения могут быть без элементов этого справочника.'
    )
    
    class Meta:
        verbose_name = 'Справочник показателя'
        verbose_name_plural = 'Справочники показателя'
        unique_together = ['indicator', 'dictionary']
        ordering = ['indicator', 'dictionary']
    
    def __str__(self):
        required_str = "обязательный" if self.is_required else "опциональный"
        return f"{self.indicator.name} - {self.dictionary.name} ({required_str})"


class IndicatorValue(models.Model):
    """Значение показателя на определенную дату"""
    indicator = models.ForeignKey(
        Indicator,
        on_delete=models.CASCADE,
        verbose_name='Показатель',
        related_name='values'
    )
    date = models.DateField('Дата')
    value = models.DecimalField(
        'Значение',
        max_digits=20,
        decimal_places=4
    )
    dictionary_items = models.ManyToManyField(
        DictionaryItem,
        verbose_name='Элементы справочников',
        blank=True,
        help_text='Элементы справочников для этого значения (разрез)'
    )
    created_at = models.DateTimeField('Создано', auto_now_add=True)

    class Meta:
        verbose_name = 'Значение показателя'
        verbose_name_plural = 'Значения показателей'
        ordering = ['-date', 'indicator']
        # Уникальность определяется комбинацией indicator + date + dictionary_items
        # Это будет обрабатываться через промежуточную модель или логику в save()

    def __str__(self):
        dimension_str = ""
        if self.dictionary_items.exists():
            items = ", ".join([str(item) for item in self.dictionary_items.all()])
            dimension_str = f" ({items})"
        return f"{self.indicator.name}: {self.value} на {self.date}{dimension_str}"
    
    def get_status_color(self):
        """Возвращает цвет статуса для этого значения"""
        return self.indicator.get_value_status(self.value)
    
    def get_dimension_display(self):
        """Возвращает строковое представление разреза"""
        if not self.dictionary_items.exists():
            return "—"
        # Получаем элементы справочников (prefetch должен быть сделан на уровне запроса в views)
        items = list(self.dictionary_items.all())
        # Группируем по справочникам
        by_dict = {}
        for item in items:
            dict_name = item.dictionary.name
            if dict_name not in by_dict:
                by_dict[dict_name] = []
            by_dict[dict_name].append(item.name)
        
        parts = []
        for dict_name, item_names in sorted(by_dict.items()):
            parts.append(f"{dict_name}: {', '.join(item_names)}")
        
        return "; ".join(parts)


class ImportTemplate(models.Model):
    """Шаблон для импорта показателей из Excel"""
    name = models.CharField('Название шаблона', max_length=200, unique=True)
    description = models.TextField('Описание', blank=True)
    
    # Настройки парсинга
    sheet_name = models.CharField(
        'Название листа',
        max_length=100,
        blank=True,
        null=True,
        help_text='Оставьте пустым для использования первого листа'
    )
    indicator_column = models.CharField(
        'Колонка с показателями',
        max_length=10,
        default='M',
        help_text='Буква колонки (например, M)'
    )
    start_row = models.IntegerField(
        'Строка начала данных',
        default=2,
        help_text='Номер строки, с которой начинаются данные'
    )
    default_unit = models.ForeignKey(
        Unit,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Единица измерения по умолчанию',
        help_text='Если не указана, будет использована единица "Штука"'
    )
    
    created_at = models.DateTimeField('Создан', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлен', auto_now=True)
    created_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Создан пользователем'
    )
    
    class Meta:
        verbose_name = 'Шаблон импорта'
        verbose_name_plural = 'Шаблоны импорта'
        ordering = ['-updated_at']
    
    def __str__(self):
        return self.name


class UserDictionaryFilter(models.Model):
    """Предустановленные фильтры пользователя по справочникам"""
    user = models.ForeignKey(
        'auth.User',
        on_delete=models.CASCADE,
        verbose_name='Пользователь',
        related_name='dictionary_filters'
    )
    dictionary = models.ForeignKey(
        Dictionary,
        on_delete=models.CASCADE,
        verbose_name='Справочник',
        related_name='user_filters'
    )
    is_required = models.BooleanField(
        'Обязательный фильтр',
        default=True,
        help_text='Если включено, пользователь видит только выбранные элементы. Если выключено - может видеть все, но по умолчанию фильтруется.'
    )
    items = models.ManyToManyField(
        DictionaryItem,
        verbose_name='Элементы справочника',
        blank=True,
        help_text='Если пусто и is_required=True - пользователь не видит данные по этому справочнику'
    )
    
    class Meta:
        verbose_name = 'Фильтр пользователя по справочнику'
        verbose_name_plural = 'Фильтры пользователей по справочникам'
        unique_together = ['user', 'dictionary']
        ordering = ['user', 'dictionary']
    
    def __str__(self):
        items_count = self.items.count()
        required_str = "обязательный" if self.is_required else "опциональный"
        return f"{self.user.username} - {self.dictionary.name} ({required_str}, {items_count} элементов)"
