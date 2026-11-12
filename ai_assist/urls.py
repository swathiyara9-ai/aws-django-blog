from django.urls import path
from . import views

urlpatterns = [
    path('suggest/', views.suggest_view, name='ai_suggest'),
    path('tag/ensure/', views.ensure_tag_view, name='ai_ensure_tag'),
]
