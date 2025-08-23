from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

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

class PublishedPost(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('failed', 'Failed'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='published_posts')
    wordpress_site = models.ForeignKey(WordPressSite, on_delete=models.SET_NULL, null=True)
    title = models.CharField(max_length=255)
    topic = models.CharField(max_length=200)
    prompt = models.TextField(blank=True)
    affiliate_links = models.TextField(blank=True, help_text="One link per line")
    content = models.TextField()
    wordpress_post_id = models.CharField(max_length=50, blank=True)
    wordpress_url = models.URLField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    error_message = models.TextField(blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.status}"

class UploadedImage(models.Model):
    post = models.ForeignKey(PublishedPost, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='uploads/%Y/%m/%d/')
    wordpress_media_id = models.CharField(max_length=50, blank=True)
    wordpress_url = models.URLField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image for {self.post.title}"