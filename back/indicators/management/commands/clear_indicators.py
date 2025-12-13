from django.core.management.base import BaseCommand
from django.db import transaction
from indicators.models import Indicator, IndicatorValue


class Command(BaseCommand):
    help = 'Очищает реестр показателей (Indicator) и все связанные значения (IndicatorValue)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--noinput',
            '--no-input',
            action='store_true',
            help='Автоматически подтверждает удаление без запроса',
        )

    def handle(self, *args, **options):
        noinput = options['noinput']
        
        indicators_count = Indicator.objects.count()
        values_count = IndicatorValue.objects.count()
        total_count = indicators_count + values_count
        
        if indicators_count == 0:
            self.stdout.write(
                self.style.WARNING('Показатели отсутствуют. Нечего удалять.')
            )
            return
        
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.WARNING('Очистка реестра показателей'))
        self.stdout.write('='*60)
        self.stdout.write(f'Показателей: {indicators_count}')
        self.stdout.write(f'Значений показателей: {values_count}')
        self.stdout.write(f'ВСЕГО записей: {total_count}')
        self.stdout.write('='*60 + '\n')
        self.stdout.write(
            self.style.WARNING(
                'Внимание: Будут удалены все показатели и связанные с ними значения!'
            )
        )
        self.stdout.write('Единицы измерения (Unit) и шаблоны импорта НЕ будут удалены.\n')
        
        if not noinput:
            confirm = input('Вы уверены? Введите "yes" для подтверждения: ')
            if confirm.lower() != 'yes':
                self.stdout.write(
                    self.style.ERROR('Операция отменена.')
                )
                return
        
        try:
            with transaction.atomic():
                # Сначала удаляем значения (они будут удалены каскадно, 
                # но лучше явно для правильного подсчета)
                deleted_values = IndicatorValue.objects.all().delete()
                
                # Затем удаляем показатели
                deleted_indicators = Indicator.objects.all().delete()
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'\n✓ Успешно удалено:\n'
                        f'  - Значения показателей: {deleted_values[0]}\n'
                        f'  - Показатели: {deleted_indicators[0]}\n'
                        f'  - ВСЕГО: {total_count} записей'
                    )
                )
                self.stdout.write(
                    self.style.SUCCESS(
                        '\n✓ Единицы измерения и шаблоны импорта сохранены.'
                    )
                )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'\n✗ Ошибка при удалении: {str(e)}')
            )
            raise


