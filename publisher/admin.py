from django.contrib import admin
from .models import WordPressSite, PublishedPost, UploadedImage

@admin.register(WordPressSite)
class WordPressSiteAdmin(admin.ModelAdmin):
    list_display = ['name', 'url', 'user', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'url', 'user__username']

@admin.register(PublishedPost)
class PublishedPostAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'wordpress_site', 'status', 'published_at']
    list_filter = ['status', 'published_at', 'created_at']
    search_fields = ['title', 'topic', 'user__username']
    readonly_fields = ['wordpress_post_id', 'wordpress_url', 'created_at']

@admin.register(UploadedImage)
class UploadedImageAdmin(admin.ModelAdmin):
    list_display = ['post', 'image', 'wordpress_media_id', 'uploaded_at']
    list_filter = ['uploaded_at']