from django.urls import path
from . import views

urlpatterns = [
    path('cloud-activity/', views.cloud_activity_api, name='api_cloud_activity'),
    path('trending/', views.trending_api, name='api_trending'),
    path('cloud-status/', views.cloud_status_api, name='api_cloud_status'),
    path('ai-insights/', views.ai_insights_api, name='api_ai_insights'),
]
