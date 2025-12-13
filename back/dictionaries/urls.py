from django.urls import path
from . import views

app_name = 'dictionaries'

urlpatterns = [
    path('', views.dictionaries_list, name='list'),
    path('create/', views.dictionary_create, name='create'),
    path('<int:pk>/', views.dictionary_detail, name='detail'),
    path('<int:dictionary_pk>/items/create/', views.dictionary_item_create, name='item_create'),
    path('items/<int:pk>/edit/', views.dictionary_item_edit, name='item_edit'),
    path('items/<int:pk>/delete/', views.dictionary_item_delete, name='item_delete'),
    path('<int:dictionary_pk>/api/items/', views.dictionary_items_api, name='items_api'),
]


