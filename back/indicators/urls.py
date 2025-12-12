from django.urls import path
from . import views

app_name = 'indicators'

urlpatterns = [
    path('', views.index, name='index'),
    path('create/', views.indicator_create, name='indicator_create'),
    path('<int:pk>/', views.indicator_detail, name='indicator_detail'),
    path('<int:pk>/generate/', views.generate_data, name='generate_data'),
    path('units/', views.units_list, name='units_list'),
    path('units/create-ajax/', views.unit_create_ajax, name='unit_create_ajax'),
]

