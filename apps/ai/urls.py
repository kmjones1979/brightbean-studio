from django.urls import path

from apps.ai import views

app_name = "ai"

urlpatterns = [
    path("settings/", views.settings_page, name="settings"),
    # Generation panel (full page + composer-embedded)
    path("generate/", views.generate_panel, name="generate_panel"),
    # Generation endpoints
    path("generate/caption/", views.generate_caption, name="generate_caption"),
    path(
        "generate/multi-platform/",
        views.generate_multi_platform,
        name="generate_multi_platform",
    ),
    # Polling endpoint
    path(
        "generation/<uuid:generation_id>/poll/",
        views.generation_poll,
        name="generation_poll",
    ),
]
