from django.urls import path

from apps.credentials import views

app_name = "credentials"

urlpatterns = [
    path("", views.credentials_list, name="list"),
    path("<str:platform>/", views.credentials_configure, name="configure"),
    path("<uuid:credential_id>/delete/", views.credentials_delete, name="delete"),
]
