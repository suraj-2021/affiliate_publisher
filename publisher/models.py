from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.contrib.postgres.search import SearchVector
from django.db.models import Q,Count
import json

class WordPressSite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wordpress_sites')
    name = models.CharField(max_length=100)
    url = models.URLField(help_text="WordPress site URL (e.g., https://example.com)")
    username = models.CharField(max_length=100)
    app_password = models.CharField(max_length=255, help_text="WordPress application password")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ['user', 'url']

    def __str__(self):
        return f"{self.name} ({self.url})"



class ContentStage(models.Model):
    """Define the 6 stages of affiliate content"""
    STAGE_CHOICES = [
        ('stage1', 'Stage 1 - Foundational Pillars'),
        ('stage2', 'Stage 2 - Conversion Content (Reviews & Buying Guides)'),
        ('stage3', 'Stage 3 - Supporting Content (Topic Clusters)'),
        ('stage4', 'Stage 4 - Authority & Community Content'),
        ('stage5', 'Stage 5 - Ecosystem Expansion & Monetization'),
        ('stage6', 'Stage 6 - Advanced Funnel & Brand Building'),
    ]
    
    stage_id = models.CharField(max_length=10, choices=STAGE_CHOICES, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField()
    word_count_min = models.IntegerField(default=2000)
    word_count_target = models.IntegerField(default=2500)
    
    # Content characteristics
    focus_keywords = models.TextField(help_text="Common focus areas for this stage")
    content_style = models.TextField(help_text="Writing style guidelines")
    monetization_focus = models.CharField(max_length=50, default='affiliate')
    
    # Stage-specific prompt
    system_prompt = models.TextField(help_text="Custom Claude prompt for this stage")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['stage_id']
    
    def __str__(self):
        return self.name


class PublishedPost(models.Model):
    """Enhanced model with internal linking support"""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('preview', 'Preview'),
        ('published', 'Published'),
        ('failed', 'Failed'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='published_posts')
    wordpress_site = models.ForeignKey('WordPressSite', on_delete=models.SET_NULL, null=True)
    title = models.CharField(max_length=255, db_index=True)  # Index for faster searches
    topic = models.CharField(max_length=200, db_index=True)
    prompt = models.TextField(blank=True)
    affiliate_links = models.TextField(blank=True, help_text="One link per line")
    content = models.TextField()
    edited_content = models.TextField(blank=True)
    html_content = models.TextField(blank=True)
    
    # New fields for internal linking
    keywords = models.TextField(blank=True, help_text="Extracted keywords for matching")
    internal_links = models.JSONField(default=dict, blank=True)  # Store internal links used
    link_to_this_count = models.IntegerField(default=0)  # How many posts link to this
    main_category = models.CharField(max_length=100, blank=True, db_index=True)
    
    wordpress_post_id = models.CharField(max_length=50, blank=True)
    wordpress_url = models.URLField(blank=True, db_index=True)  # Index for quick lookups
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    error_message = models.TextField(blank=True)
    published_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # SEO and tracking
    meta_description = models.TextField(max_length=160, blank=True)
    focus_keyword = models.CharField(max_length=100, blank=True, db_index=True)

    content_stage = models.CharField(
        max_length=10,
        choices=ContentStage.STAGE_CHOICES,
        default='stage1',
        help_text="Content stage this post belongs to"
    )
    
    # Stage-specific metrics
    pillar_post = models.BooleanField(default=False, help_text="Is this a pillar post?")
    conversion_focused = models.BooleanField(default=False)
    community_engagement_score = models.IntegerField(default=0)


    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status', '-published_at']),
            models.Index(fields=['topic', 'main_category']),
        ]

    def __str__(self):
        return f"{self.title} - {self.status}"
    
    def get_related_posts(self, limit=5):
        """Find related posts based on topic and keywords"""
        if not self.keywords:
            return PublishedPost.objects.none()
        
        keywords_list = self.keywords.lower().split(',')
        
        # Build query for related posts
        query = Q(status='published') & Q(user=self.user) & ~Q(id=self.id)
        
        # Match by topic similarity
        for keyword in keywords_list[:5]:  # Use top 5 keywords
            keyword = keyword.strip()
            if keyword:
                query |= Q(topic__icontains=keyword) | Q(keywords__icontains=keyword)
        
        # Also match by category if available
        if self.main_category:
            query |= Q(main_category=self.main_category)
        
        related = PublishedPost.objects.filter(query).distinct()
        
        # Score and sort by relevance
        scored_posts = []
        for post in related[:20]:  # Limit initial set
            score = 0
            post_keywords = post.keywords.lower().split(',')
            
            # Score based on keyword overlap
            for kw in keywords_list:
                if kw.strip() in post_keywords:
                    score += 2
                if kw.strip() in post.topic.lower():
                    score += 3
            
            # Boost score for same category
            if post.main_category == self.main_category:
                score += 5
            
            scored_posts.append((score, post))
        
        # Sort by score and return top matches
        scored_posts.sort(key=lambda x: x[0], reverse=True)
        return [post for score, post in scored_posts[:limit]]

class UploadedImage(models.Model):
    """Enhanced image model with better tracking"""
    post = models.ForeignKey(PublishedPost, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='uploads/%Y/%m/%d/')
    
    # Enhanced fields
    alt_text = models.CharField(max_length=255, blank=True, help_text='SEO-friendly alt text')
    caption = models.TextField(blank=True, help_text='Image caption')
    is_featured = models.BooleanField(default=False, help_text='Use as featured image')
    
    # WordPress integration
    wordpress_media_id = models.CharField(max_length=50, blank=True)
    wordpress_url = models.URLField(blank=True)
    
    # Metadata
    original_filename = models.CharField(max_length=255, blank=True)
    file_size = models.IntegerField(default=0, help_text='File size in bytes')
    width = models.IntegerField(default=0)
    height = models.IntegerField(default=0)
    
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['is_featured', '-uploaded_at']
    
    def __str__(self):
        return f"Image for {self.post.title} - {self.alt_text or 'No alt text'}"
    
    def save(self, *args, **kwargs):
        """Auto-populate image metadata"""
        if self.image:
            # Get file size
            self.file_size = self.image.size
            
            # Get dimensions
            try:
                from PIL import Image
                img = Image.open(self.image)
                self.width, self.height = img.size
            except:
                pass
        
        super().save(*args, **kwargs)
        
class InternalLinkRule(models.Model):
    """Rules for automatic internal linking"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    keyword = models.CharField(max_length=100, db_index=True)
    target_post = models.ForeignKey(PublishedPost, on_delete=models.CASCADE, related_name='link_rules')
    priority = models.IntegerField(default=1, help_text="Higher priority links are used first")
    max_usage = models.IntegerField(default=3, help_text="Max times to use this link per post")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-priority', 'keyword']
        unique_together = ['user', 'keyword', 'target_post']
    
    def __str__(self):
        return f"{self.keyword} → {self.target_post.title}"

class LinkingProfile(models.Model):
    """User preferences for internal linking"""
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    auto_link_enabled = models.BooleanField(default=True)
    max_internal_links = models.IntegerField(default=5, help_text="Max internal links per post")
    min_words_between_links = models.IntegerField(default=150)
    link_to_newer_posts = models.BooleanField(default=False, help_text="Allow linking to newer posts")
    prefer_same_category = models.BooleanField(default=True)
    auto_create_rules = models.BooleanField(default=True, help_text="Auto-create linking rules from posts")
    
    # Link text preferences
    use_exact_title = models.BooleanField(default=False)
    vary_anchor_text = models.BooleanField(default=True)
    
    def __str__(self):
        return f"Linking profile for {self.user.username}"




class UserContentStrategy(models.Model):
    """Track user's content strategy progress"""
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    current_stage = models.CharField(
        max_length=10,
        choices=ContentStage.STAGE_CHOICES,
        default='stage1'
    )
    
    # Stage progress tracking
    stage1_posts = models.IntegerField(default=0)
    stage2_posts = models.IntegerField(default=0)
    stage3_posts = models.IntegerField(default=0)
    stage4_posts = models.IntegerField(default=0)
    stage5_posts = models.IntegerField(default=0)
    stage6_posts = models.IntegerField(default=0)
    
    # Strategy preferences
    primary_niche = models.CharField(max_length=100, blank=True)
    target_audience = models.TextField(blank=True)
    preferred_tone = models.CharField(max_length=50, default='authoritative_friendly')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def get_stage_progress(self):
        """Get progress for each stage"""
        return {
            'stage1': self.stage1_posts,
            'stage2': self.stage2_posts,
            'stage3': self.stage3_posts,
            'stage4': self.stage4_posts,
            'stage5': self.stage5_posts,
            'stage6': self.stage6_posts,
        }
    
    def increment_stage_count(self, stage):
        """Increment post count for a stage"""
        field_name = f"{stage}_posts"
        if hasattr(self, field_name):
            setattr(self, field_name, getattr(self, field_name) + 1)
            self.save(update_fields=[field_name, 'updated_at'])