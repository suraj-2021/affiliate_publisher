from django.contrib import admin
from .models import (
    WordPressSite, PublishedPost, UploadedImage,
    InternalLinkRule, LinkingProfile,ContentStage, 
    UserContentStrategy
)
@admin.register(WordPressSite)
class WordPressSiteAdmin(admin.ModelAdmin):
    list_display = ['name', 'url', 'user', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'url', 'user__username']


@admin.register(UploadedImage)
class UploadedImageAdmin(admin.ModelAdmin):
    list_display = ['post', 'image', 'wordpress_media_id', 'uploaded_at']
    list_filter = ['uploaded_at']


@admin.register(InternalLinkRule)
class InternalLinkRuleAdmin(admin.ModelAdmin):
    list_display = ['keyword', 'target_post', 'user', 'priority', 'is_active']
    list_filter = ['is_active', 'priority', 'created_at']
    search_fields = ['keyword', 'target_post__title']
    list_editable = ['priority', 'is_active']

@admin.register(LinkingProfile)
class LinkingProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'auto_link_enabled', 'max_internal_links', 'vary_anchor_text']
    list_filter = ['auto_link_enabled', 'vary_anchor_text']



@admin.register(ContentStage)
class ContentStageAdmin(admin.ModelAdmin):
    list_display = ['stage_id', 'name', 'word_count_target', 'monetization_focus']
    list_editable = ['word_count_target']
    ordering = ['stage_id']

@admin.register(UserContentStrategy)
class UserContentStrategyAdmin(admin.ModelAdmin):
    list_display = ['user', 'current_stage', 'primary_niche', 'get_total_posts']
    list_filter = ['current_stage', 'created_at']
    
    def get_total_posts(self, obj):
        return sum([
            obj.stage1_posts, obj.stage2_posts, obj.stage3_posts,
            obj.stage4_posts, obj.stage5_posts, obj.stage6_posts
        ])
    get_total_posts.short_description = 'Total Posts'

# Update PublishedPost admin to show stage
@admin.register(PublishedPost)
class PublishedPostAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'content_stage', 'pillar_post', 'status', 'published_at']
    list_filter = ['content_stage', 'pillar_post', 'conversion_focused', 'status']
    search_fields = ['title', 'topic']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'title', 'topic', 'wordpress_site')
        }),
        ('Stage & Strategy', {
            'fields': ('content_stage', 'pillar_post', 'conversion_focused')
        }),
        ('Content', {
            'fields': ('content', 'edited_content', 'keywords')
        }),
        ('Publishing', {
            'fields': ('status', 'wordpress_url', 'published_at')
        }),
    )