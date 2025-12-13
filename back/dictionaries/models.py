from django.db import models
from django.core.exceptions import ValidationError


class Dictionary(models.Model):
    """Справочник"""
    name = models.CharField('Название справочника', max_length=200, unique=True)
    code = models.SlugField(
        'Код справочника',
        max_length=100,
        unique=True,
        help_text='Уникальный идентификатор (например: factories)'
    )
    description = models.TextField('Описание', blank=True)
    is_active = models.BooleanField('Активен', default=True)
    created_at = models.DateTimeField('Создан', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлен', auto_now=True)
    
    class Meta:
        verbose_name = 'Справочник'
        verbose_name_plural = 'Справочники'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class DictionaryItem(models.Model):
    """Элемент справочника"""
    dictionary = models.ForeignKey(
        Dictionary,
        on_delete=models.CASCADE,
        verbose_name='Справочник',
        related_name='items'
    )
    name = models.CharField('Наименование', max_length=200)
    description = models.TextField('Описание', blank=True)
    code = models.CharField(
        'Код элемента',
        max_length=100,
        blank=True,
        help_text='Опциональный код для программной идентификации'
    )
    sort_order = models.IntegerField(
        'Порядок сортировки',
        default=0,
        help_text='Для сортировки элементов в списке'
    )
    is_active = models.BooleanField('Активен', default=True)
    created_at = models.DateTimeField('Создан', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлен', auto_now=True)
    
    class Meta:
        verbose_name = 'Элемент справочника'
        verbose_name_plural = 'Элементы справочника'
        ordering = ['sort_order', 'name']
        indexes = [
            models.Index(fields=['dictionary', 'is_active']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['dictionary', 'code'],
                condition=models.Q(code__gt=''),
                name='unique_dictionary_item_code'
            )
        ]
    
    def __str__(self):
        return f"{self.dictionary.name}: {self.name}"
    
    def clean(self):
        """Валидация"""
        # Если код указан, проверяем уникальность в рамках справочника
        if self.code:
            existing = DictionaryItem.objects.filter(
                dictionary=self.dictionary,
                code=self.code
            ).exclude(pk=self.pk)
            if existing.exists():
                raise ValidationError({
                    'code': f'Элемент с кодом "{self.code}" уже существует в этом справочнике'
                })
