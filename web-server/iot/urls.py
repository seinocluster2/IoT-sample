from django.urls import include, path
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required

from . import views

app_name = 'iot'

urlpatterns = [
    path('iot', login_required(views.IndexView.as_view()), name = 'index'),
    path('accounts/login/', auth_views.LoginView.as_view(template_name = 'iot/login.html'), name = 'login'),
    path('iot/reload', login_required(views.reload), name = 'reload'),
    path('iot/switch', login_required(views.switch), name = 'switch')
]