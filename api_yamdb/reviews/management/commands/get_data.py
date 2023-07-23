import csv
import os

from django.core.management.base import BaseCommand
from django.conf import settings
from django.db.utils import IntegrityError

from reviews import models


FILE_NAMES_CLASSES = {
    'users.csv': models.User,
    'category.csv': models.Category,
    'genre.csv': models.Genre,
    'titles.csv': models.Title,
    'genre_title.csv': models.TitleGenre,
    'review.csv': models.Review,
    'comments.csv': models.Comment,
}
FIELDS = {
    'category': (models.Category, 'category'),
    'genre_id': (models.Genre, 'genre'),
    'title_id': (models.Title, 'title'),
    'author': (models.User, 'author'),
    'review_id': (models.Review, 'review'),
}


def open_csv_file(file_name):
    csv_path = os.path.join(settings.CSV_FILES_DIR, file_name)
    try:
        with open(csv_path, encoding='utf-8') as file:
            return tuple(csv.reader(file))
    except FileNotFoundError:
        print(f'Файл {file_name} не найден.')


def get_object_data(fields, data):
    object_data = dict(zip(fields, data))
    for field in tuple(object_data.keys()):
        if field in FIELDS:
            new_field = FIELDS[field][1]
            object_data[new_field] = object_data.pop(field)
            object_data[new_field] = FIELDS[field][0].objects.get(
                id=object_data[new_field]
            )
    return object_data


class Command(BaseCommand):
    help = 'Load csv files to database'

    def handle(self, *args, **options):
        for file_name, class_ in FILE_NAMES_CLASSES.items():
            print(f'Заполнение модели {class_.__name__}')
            fields, *data = open_csv_file(file_name)
            try:
                for row in data:
                    object_data = get_object_data(fields, row)
                    class_.objects.create(**object_data)
                print(f'Модель {class_.__name__} заполнена успешно')
            except (ValueError, IntegrityError, TypeError) as error:
                print(
                    f'Ошибка при заполнении {class_.__name__}: {error}.'
                    f'\nНеверные данные: {row}.'
                )
