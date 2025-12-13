from django.core.management.base import BaseCommand
from django.db import transaction
from indicators.models import IndicatorValue, Indicator, Unit, ImportTemplate


class Command(BaseCommand):
    help = 'Очищает всю базу данных приложения indicators (все модели)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--noinput',
            '--no-input',
            action='store_true',
            help='Автоматически подтверждает удаление без запроса',
        )

    def handle(self, *args, **options):
        noinput = options['noinput']
        
        # Подсчитываем количество записей
        units_count = Unit.objects.count()
        indicators_count = Indicator.objects.count()
        values_count = IndicatorValue.objects.count()
        templates_count = ImportTemplate.objects.count()
        
        total_count = units_count + indicators_count + values_count + templates_count
        
        if total_count == 0:
            self.stdout.write(
                self.style.WARNING('База данных уже пуста. Нечего удалять.')
            )
            return
        
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.WARNING('ВНИМАНИЕ: Очистка всей базы данных'))
        self.stdout.write('='*60)
        self.stdout.write(f'Единицы измерения: {units_count}')
        self.stdout.write(f'Показатели: {indicators_count}')
        self.stdout.write(f'Значения показателей: {values_count}')
        self.stdout.write(f'Шаблоны импорта: {templates_count}')
        self.stdout.write(f'ВСЕГО записей: {total_count}')
        self.stdout.write('='*60 + '\n')
        
        if not noinput:
            confirm = input('Вы уверены? Введите "yes" для подтверждения: ')
            if confirm.lower() != 'yes':
                self.stdout.write(
                    self.style.ERROR('Операция отменена.')
                )
                return
        
        try:
            with transaction.atomic():
                # Удаляем в правильном порядке (учитывая связи)
                deleted_values = IndicatorValue.objects.all().delete()
                deleted_templates = ImportTemplate.objects.all().delete()
                deleted_indicators = Indicator.objects.all().delete()
                deleted_units = Unit.objects.all().delete()
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'\n✓ Успешно удалено:\n'
                        f'  - Значения показателей: {deleted_values[0]}\n'
                        f'  - Шаблоны импорта: {deleted_templates[0]}\n'
                        f'  - Показатели: {deleted_indicators[0]}\n'
                        f'  - Единицы измерения: {deleted_units[0]}\n'
                        f'  - ВСЕГО: {total_count} записей'
                    )
                )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'\n✗ Ошибка при удалении: {str(e)}')
            )
            raise


