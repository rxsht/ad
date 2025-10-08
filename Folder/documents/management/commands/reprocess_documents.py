"""
Management-команда для пересчёта оригинальности существующих документов
"""

from django.core.management.base import BaseCommand
from documents.models import Document
from documents.tasks import process_document_plagiarism


class Command(BaseCommand):
    help = 'Пересчитать оригинальность для всех или выбранных документов через Celery'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Пересчитать все документы',
        )
        parser.add_argument(
            '--failed',
            action='store_true',
            help='Пересчитать только документы с ошибками обработки',
        )
        parser.add_argument(
            '--ids',
            type=str,
            help='Пересчитать документы с указанными ID (через запятую)',
        )

    def handle(self, *args, **options):
        queryset = Document.objects.all()
        
        if options['failed']:
            queryset = queryset.filter(processing_status='failed')
            self.stdout.write(self.style.WARNING('Пересчёт документов с ошибками...'))
        elif options['ids']:
            ids = [int(x.strip()) for x in options['ids'].split(',')]
            queryset = queryset.filter(id__in=ids)
            self.stdout.write(self.style.WARNING(f'Пересчёт документов: {ids}'))
        elif options['all']:
            self.stdout.write(self.style.WARNING('Пересчёт всех документов...'))
        else:
            self.stdout.write(self.style.ERROR('Укажите --all, --failed или --ids'))
            return
        
        count = 0
        for doc in queryset:
            # Сбрасываем статус обработки
            doc.processing_status = 'queue'
            doc.processing_error = None
            doc.result = None
            doc.save(update_fields=['processing_status', 'processing_error', 'result'])
            
            # Отправляем в Celery
            task = process_document_plagiarism.delay(doc.id)
            count += 1
            self.stdout.write(f'  Документ "{doc.name}" (ID: {doc.id}) -> Task {task.id}')
        
        self.stdout.write(self.style.SUCCESS(f'\nОтправлено {count} документов на обработку'))