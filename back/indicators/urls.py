from django.urls import path
from . import views

app_name = 'indicators'

urlpatterns = [
    path('', views.index, name='index'),
    path('create/', views.indicator_create, name='indicator_create'),
    path('import/', views.import_from_excel, name='import_from_excel'),
    path('import/get-sheets/', views.get_excel_sheets, name='get_excel_sheets'),
    path('import/template/create/', views.import_template_create, name='import_template_create'),
    path('import/template/<int:pk>/edit/', views.import_template_edit, name='import_template_edit'),
    path('import/template/<int:pk>/delete/', views.import_template_delete, name='import_template_delete'),
    path('<int:pk>/', views.indicator_detail, name='indicator_detail'),
    path('<int:pk>/generate/', views.generate_data, name='generate_data'),
    path('units/', views.units_list, name='units_list'),
    path('units/create-ajax/', views.unit_create_ajax, name='unit_create_ajax'),
    path('clear-data/', views.clear_data, name='clear_data'),
]

