from django.urls import path
from . import views

app_name = 'visualization'

urlpatterns = [
    path('', views.dashboard_list, name='dashboard_list'),
    path('create/', views.dashboard_create, name='dashboard_create'),
    path('<int:pk>/', views.dashboard_detail, name='dashboard_detail'),
    path('<int:pk>/edit/', views.dashboard_edit, name='dashboard_edit'),
    path('<int:pk>/indicator/add/', views.dashboard_indicator_add, name='dashboard_indicator_add'),
    path('<int:pk>/indicator/<int:indicator_id>/update/', views.dashboard_indicator_update, name='dashboard_indicator_update'),
    path('<int:pk>/indicator/<int:indicator_id>/delete/', views.dashboard_indicator_delete, name='dashboard_indicator_delete'),
    path('api/indicator/<int:indicator_id>/data/', views.api_indicator_data, name='api_indicator_data'),
]

