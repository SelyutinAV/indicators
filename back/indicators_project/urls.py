"""
URL configuration for indicators_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from django.conf import settings
from django.conf.urls.static import static

def redirect_to_frontend(request):
    """Редирект на фронтенд"""
    return redirect('indicators:index')

# Настройка заголовков админки
admin.site.site_header = 'Система управления показателями'
admin.site.site_title = 'Управление показателями'
admin.site.index_title = 'Панель управления'

urlpatterns = [
    path('', redirect_to_frontend, name='home'),
    path('indicators/', include('indicators.urls')),
    path('admin/', admin.site.urls),
]

# Подключение статических файлов в режиме разработки
if settings.DEBUG:
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns
    urlpatterns += staticfiles_urlpatterns()
