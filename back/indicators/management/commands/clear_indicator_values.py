from django.core.management.base import BaseCommand
from django.db import transaction
from indicators.models import IndicatorValue


class Command(BaseCommand):
    help = 'Очищает все значения показателей (IndicatorValue)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--noinput',
            '--no-input',
            action='store_true',
            help='Автоматически подтверждает удаление без запроса',
        )

    def handle(self, *args, **options):
        noinput = options['noinput']
        
        values_count = IndicatorValue.objects.count()
        
        if values_count == 0:
            self.stdout.write(
                self.style.WARNING('Значения показателей отсутствуют. Нечего удалять.')
            )
            return
        
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.WARNING('Очистка значений показателей'))
        self.stdout.write('='*60)
        self.stdout.write(f'Найдено значений: {values_count}')
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
                deleted = IndicatorValue.objects.all().delete()
                self.stdout.write(
                    self.style.SUCCESS(
                        f'\n✓ Успешно удалено {deleted[0]} значений показателей'
                    )
                )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'\n✗ Ошибка при удалении: {str(e)}')
            )
            raise


