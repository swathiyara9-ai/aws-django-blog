from django.contrib import admin
from .models import PostView, PostStats


@admin.register(PostView)
class PostViewAdmin(admin.ModelAdmin):
    list_display = ('post', 'user', 'visitor_hash', 'viewed_at')
    list_filter = ('viewed_at',)
    search_fields = ('post__title', 'user__username', 'visitor_hash')
    readonly_fields = ('post', 'user', 'visitor_hash', 'viewed_at')


@admin.register(PostStats)
class PostStatsAdmin(admin.ModelAdmin):
    list_display = ('post', 'score', 'views', 'likes', 'comments', 'updated_at')
    list_filter = ('updated_at',)
    search_fields = ('post__title',)
    readonly_fields = ('post', 'views', 'likes', 'comments', 'score', 'updated_at')
