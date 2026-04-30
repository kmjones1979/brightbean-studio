from django.urls import path

from apps.ai import views

app_name = "ai"

urlpatterns = [
    path("settings/", views.settings_page, name="settings"),
]
