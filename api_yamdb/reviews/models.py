from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core import validators
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

ROLES = (
    ('admin', 'Администратор'),
    ('moderator', 'Модератор'),
    ('user', 'Пользователь')
)


class User(AbstractUser):
    email = models.EmailField('Почта', max_length=254, unique=True)
    bio = models.TextField('Биография', blank=True)
    role = models.CharField(
        'Роль',
        max_length=20,
        choices=ROLES,
        default='user'
    )
    confirmation_code = models.CharField(
        'Код подтверждения',
        max_length=settings.CONFIRMATION_CODE_LENGTH,
        blank=True,
    )

    @property
    def is_admin(self):
        return self.role == ('admin' or self.is_superuser or self.is_staff)

    @property
    def is_moderator(self):
        return self.role == 'moderator'


class Category(models.Model):
    name = models.CharField('Название', max_length=256)
    slug = models.SlugField(
        'Cлаг',
        max_length=50,
        unique=True,
        validators=[validators.RegexValidator(
            regex=r'^[-a-zA-Z0-9_]+$',
            message='Слаг содержит недопустимые символы'
        )]
    )

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'

    def __str__(self) -> str:
        return self.name


class Genre(models.Model):
    name = models.CharField('Название', max_length=256)
    slug = models.SlugField(
        'Cлаг',
        max_length=50,
        unique=True,
        validators=[validators.RegexValidator(
            regex=r'^[-a-zA-Z0-9_]+$',
            message='Слаг содержит недопустимые символы'
        )]
    )

    class Meta:
        verbose_name = 'Жанр'
        verbose_name_plural = 'Жанры'

    def __str__(self):
        return self.name


class Title(models.Model):
    name = models.CharField('Название', max_length=256)
    year = models.IntegerField('Год выпуска')
    description = models.TextField('Описание', blank=True, null=True)
    category = models.ForeignKey(
        Category,
        verbose_name='Категория',
        related_name='titles',
        on_delete=models.SET_NULL,
        null=True
    )
    genre = models.ManyToManyField(
        Genre,
        verbose_name='Жанр',
        through='TitleGenre',
        related_name='titles',
    )

    class Meta:
        verbose_name = 'Произведение'
        verbose_name_plural = 'Произведения'

    def __str__(self):
        return self.name


class TitleGenre(models.Model):
    genre = models.ForeignKey(
        Genre,
        on_delete=models.CASCADE,
        verbose_name='Жанр'
    )
    title = models.ForeignKey(
        Title,
        on_delete=models.CASCADE,
        verbose_name='Произведение'
    )

    class Meta:
        verbose_name = 'Жанры произведения'
        verbose_name_plural = 'Жанр произведения'
        ordering = ('id',)

    def __str__(self):
        return f'{self.title} - {self.genre}'


class Review(models.Model):
    title = models.ForeignKey(
        Title,
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name='Произведение'
    )
    text = models.TextField('Текст')
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name='Автор'
    )
    score = models.SmallIntegerField(
        'Оценка',
        validators=[
            MinValueValidator(1),
            MaxValueValidator(10),
        ]
    )
    pub_date = models.DateTimeField('Дата публикации', auto_now_add=True)

    def __str__(self):
        return (
            f'Оценка пользователя {self.author.username} '
            f'на произведение {self.title.name}'
        )

    class Meta:
        verbose_name = 'Отзыв'
        verbose_name_plural = 'Отзывы'

        constraints = [
            models.UniqueConstraint(
                fields=('title', 'author'),
                name='unique_review'
            )
        ]


class Comment(models.Model):
    text = models.TextField('Текст')
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name='Автор'
    )
    review = models.ForeignKey(
        Review,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name='Ревью'
    )
    pub_date = models.DateTimeField('Дата публикации', auto_now_add=True)

    def __str__(self):
        return (
            f'Комментарий пользователя {self.author.username} '
            f'на оценку {self.review}'
        )

    class Meta:
        verbose_name = 'Комментарий'
        verbose_name_plural = 'Комментарии'
