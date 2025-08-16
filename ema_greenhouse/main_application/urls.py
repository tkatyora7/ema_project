from django.urls import path
from . import views
from .views import sensor_data



urlpatterns=[
    path('',views.sign_in , name='login'),
    path('logout',views.signout , name='logout'),
    path('dashboard/ema/', views.ema_dashboard, name='ema_dashboard'),
    path('dashboard/policy/', views.policy_dashboard, name='policy_dashboard'),
    path('system-health/', views.system_health, name='system_health'),
    path('sensor_data_api/', sensor_data),
   
    
]

