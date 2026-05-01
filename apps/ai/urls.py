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
    path("generate/hooks/", views.generate_hooks, name="generate_hooks"),
    path("generate/cta/", views.generate_cta, name="generate_cta"),
    path("generate/hashtags/", views.generate_hashtags, name="generate_hashtags"),
    path("generate/brief-expand/", views.generate_brief_expand, name="generate_brief_expand"),
    path("generate/idea-seed/", views.generate_idea_seed, name="generate_idea_seed"),
    path("generate/reply-draft/", views.generate_reply_draft, name="generate_reply_draft"),
    # Polling endpoint
    path(
        "generation/<uuid:generation_id>/poll/",
        views.generation_poll,
        name="generation_poll",
    ),
    # Add idea_seed result to Kanban board
    path(
        "generation/<uuid:generation_id>/add-to-board/",
        views.add_ideas_to_board,
        name="add_ideas_to_board",
    ),
]
