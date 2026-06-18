
from django.urls import path
from .views import whatsapp_webhook, privacy_policy

urlpatterns = [
    path('webhook/', whatsapp_webhook),
    path('privacy-policy/', privacy_policy),
]