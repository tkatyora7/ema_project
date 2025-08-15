from django.urls import path
from . import views
from .views import dht22_data, mq4_data, mq135_data



urlpatterns=[
    path('',views.sign_in , name='login'),
    path('logout',views.signout , name='logout'),
    path('dashboard/ema/', views.ema_dashboard, name='ema_dashboard'),
    path('dashboard/policy/', views.policy_dashboard, name='policy_dashboard'),
    path('system-health/', views.system_health, name='system_health'),
    path('dht22_api/', dht22_data),
    path('mq4_api/', mq4_data),
    path('mq135_api/', mq135_data)
    
]

