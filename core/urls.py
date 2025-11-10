from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('about/', views.about, name='about'),
    path('presentation/', views.presentation, name='presentation'),
    path('api/load-more-vacancies/', views.load_more_vacancies, name='load_more_vacancies'),
]