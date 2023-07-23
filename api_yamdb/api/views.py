import string
import random

from django.conf import settings
from django.core.mail import send_mail
from django.db.models import Avg
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, mixins, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.filters import SearchFilter
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import AccessToken

from . import permissions, serializers
from reviews import models
from .filters import TitleFilter


class CreateDestroyListViewSet(
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet
):
    filter_backends = (filters.SearchFilter,)
    search_fields = ('name',)
    lookup_field = 'slug'
    permission_classes = (permissions.AdminOrReadOnly,)


@api_view(['POST'])
@permission_classes((AllowAny,))
def get_token(request):
    serializer = serializers.TokenSerializer(data=request.data)
    if serializer.is_valid():
        username = serializer.validated_data.get('username')
        confirmation_code = serializer.validated_data.get('confirmation_code')
        user = get_object_or_404(models.User, username=username)
        if user.confirmation_code == confirmation_code:
            token = AccessToken.for_user(user)
            return Response({'token': str(token)}, status=status.HTTP_200_OK)
        return Response(
            {'confirmation_code': 'Неверный код подтверждения'},
            status=status.HTTP_400_BAD_REQUEST
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CategoryViewSet(CreateDestroyListViewSet):
    queryset = models.Category.objects.all().order_by('id')
    serializer_class = serializers.CategorySerializer


class GenreViewSet(CreateDestroyListViewSet):
    queryset = models.Genre.objects.all().order_by('id')
    serializer_class = serializers.GenreSerializer


class TitleViewSet(viewsets.ModelViewSet):
    queryset = models.Title.objects.annotate(
        rating=Avg('reviews__score')
    ).order_by('id')
    permission_classes = (permissions.AdminOrReadOnly,)
    filter_backends = (DjangoFilterBackend,)
    filterset_class = TitleFilter

    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
            return serializers.TitleReadSerializer
        return serializers.TitleWriteSerializer


@api_view(['POST'])
@permission_classes((AllowAny,))
def signup(request):
    serializer = serializers.SignupSerializer(data=request.data)
    if models.User.objects.filter(
        username=request.data.get('username'),
        email=request.data.get('email')
    ).exists():
        return Response(request.data, status=status.HTTP_200_OK)
    if serializer.is_valid():
        new_code = ''.join(random.choices(
            string.ascii_uppercase + string.digits,
            k=settings.CONFIRMATION_CODE_LENGTH
        ))
        serializer.save(confirmation_code=new_code)
        send_mail(
            subject='Код подтверждения',
            message=f'Ваш код подтверждения: {new_code}',
            from_email='yamdb@yandex.ru',
            recipient_list=[serializer.validated_data.get('email')],
            fail_silently=False,
        )
        return Response(request.data, status=status.HTTP_200_OK)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserViewSet(viewsets.ModelViewSet):
    queryset = models.User.objects.all().order_by('id')
    serializer_class = serializers.AdminUserSerializer
    permission_classes = (permissions.AdminOnly,)
    lookup_field = 'username'
    filter_backends = (SearchFilter,)
    search_fields = ('username',)
    http_method_names = ('get', 'post', 'head', 'patch', 'delete')

    @action(
        detail=False,
        methods=('GET', 'PATCH'),
        permission_classes=(IsAuthenticated,),
        url_path='me',
        url_name='me'
    )
    def user_me(self, request):
        serializer = serializers.UserSerializer(request.user)
        if request.method == 'PATCH':
            if request.user.is_admin:
                serializer = serializers.AdminUserSerializer(
                    request.user,
                    data=request.data,
                    partial=True
                )
            else:
                serializer = serializers.UserSerializer(
                    request.user,
                    data=request.data,
                    partial=True
                )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.data)


class CommentViewSet(viewsets.ModelViewSet):
    pagination_class = LimitOffsetPagination
    serializer_class = serializers.CommentSerializer
    permission_classes = (permissions.AdminModeratorAuthorPermission,)

    def get_queryset(self):
        review_id = self.kwargs.get('review_id')
        review = get_object_or_404(models.Review, id=review_id)
        return review.comments.all()

    def perform_create(self, serializer):
        review_id = self.kwargs.get('review_id')
        review = get_object_or_404(models.Review, id=review_id)
        serializer.save(author=self.request.user, review=review)


class ReviewViewSet(viewsets.ModelViewSet):
    pagination_class = LimitOffsetPagination
    permission_classes = (permissions.AdminModeratorAuthorPermission,)
    serializer_class = serializers.ReviewSerializer

    def perform_create(self, serializer):
        title_id = self.kwargs.get('title_id')
        serializer.save(author=self.request.user, title_id=title_id)

    def get_queryset(self):
        title_id = self.kwargs.get('title_id')
        review_queryset = models.Review.objects.filter(title=title_id)
        return review_queryset
