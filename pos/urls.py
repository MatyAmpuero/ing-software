# pos/urls.py
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from ventas.forms import LoginForm
from ventas.views import CustomPasswordResetView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('ventas.urls')),
    path('accounts/', include('django.contrib.auth.urls')),
    # RESET PASSWORD
    path(
        'password-reset/',
        CustomPasswordResetView.as_view(),
        name='password_reset'
    ),
    path(
        'password-reset/done/',
        auth_views.PasswordResetDoneView.as_view(
            template_name='ventas/password_reset_done.html'
        ),
        name='password_reset_done'
    ),
    path(
        'reset/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='ventas/password_reset_confirm.html'
        ),
        name='password_reset_confirm'
    ),
    path(
        'reset/done/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='ventas/password_reset_complete.html'
        ),
        name='password_reset_complete'
    ),
    # LOGIN / LOGOUT
    path(
        'login/',
        auth_views.LoginView.as_view(
            template_name='ventas/login.html',
            authentication_form=LoginForm
        ),
        name='login'
    ),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
]

