from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.core.files.storage import default_storage
from django.http import JsonResponse
import os

from .models import WordPressSite, PublishedPost, UploadedImage
from .forms import CustomLoginForm, WordPressSiteForm, ContentGenerationForm
from .claude_service import ClaudeService
from .wordpress_service import WordPressService

def login_view(request):
    if request.method == 'POST':
        form = CustomLoginForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect('dashboard')
    else:
        form = CustomLoginForm()
    return render(request, 'login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('login')

@login_required
def dashboard(request):
    posts = PublishedPost.objects.filter(user=request.user)[:20]
    sites = WordPressSite.objects.filter(user=request.user, is_active=True)
    
    # Get total counts from database, not from limited queryset
    total_posts = PublishedPost.objects.filter(user=request.user).count()
    published_posts = PublishedPost.objects.filter(user=request.user, status='published').count()
    failed_posts = PublishedPost.objects.filter(user=request.user, status='failed').count()
    
    context = {
        'posts': posts,
        'sites': sites,
        'total_posts': total_posts,
        'published_posts': published_posts,
        'failed_posts': failed_posts,
    }
    return render(request, 'dashboard.html', context)

@login_required
def generate_content(request):
    if request.method == 'POST':
        form = ContentGenerationForm(request.user, request.POST, request.FILES)
        if form.is_valid():
            # Generate content with Claude
            claude = ClaudeService()
            result = claude.generate_affiliate_content(
                topic=form.cleaned_data['topic'],
                prompt=form.cleaned_data.get('prompt'),
                affiliate_links=form.cleaned_data.get('affiliate_links')
            )
            
            if result['success']:
                # Create post record
                post = PublishedPost.objects.create(
                    user=request.user,
                    wordpress_site=form.cleaned_data['wordpress_site'],
                    title=result['title'],
                    topic=form.cleaned_data['topic'],
                    prompt=form.cleaned_data.get('prompt', ''),
                    affiliate_links=form.cleaned_data.get('affiliate_links', ''),
                    content=result['content'],
                    status='draft'
                )
                
                # Handle multiple image uploads
                images = request.FILES.getlist('images')
                uploaded_images = []
                for image in images:
                    img_instance = UploadedImage.objects.create(
                        post=post,
                        image=image
                    )
                    uploaded_images.append(img_instance)
                
                # Publish to WordPress
                wp_site = form.cleaned_data['wordpress_site']
                wp = WordPressService(
                    site_url=wp_site.url,
                    username=wp_site.username,
                    app_password=wp_site.app_password
                )
                
                # Upload featured image if available
                featured_media_id = None
                if uploaded_images:
                    first_image = uploaded_images[0]
                    media_result = wp.upload_media(
                        first_image.image.path,
                        os.path.basename(first_image.image.name)
                    )
                    if media_result['success']:
                        featured_media_id = media_result['media_id']
                        first_image.wordpress_media_id = str(media_result['media_id'])
                        first_image.wordpress_url = media_result['url']
                        first_image.save()
                
                # Create WordPress post
                wp_result = wp.create_post(
                    title=result['title'],
                    content=result['content'],
                    status='publish',
                    featured_media_id=featured_media_id
                )
                
                if wp_result['success']:
                    post.wordpress_post_id = str(wp_result['post_id'])
                    post.wordpress_url = wp_result['url']
                    post.status = 'published'
                    post.published_at = timezone.now()
                    messages.success(request, f"Post published successfully! View at: {wp_result['url']}")
                else:
                    post.status = 'failed'
                    post.error_message = wp_result['error']
                    messages.error(request, f"Failed to publish: {wp_result['error']}")
                
                post.save()
                return redirect('dashboard')
            else:
                messages.error(request, f"Content generation failed: {result['error']}")
    else:
        form = ContentGenerationForm(request.user)
    
    return render(request, 'generate.html', {'form': form})

@login_required
def manage_sites(request):
    if request.method == 'POST':
        form = WordPressSiteForm(request.POST)
        if form.is_valid():
            site = form.save(commit=False)
            site.user = request.user
            
            # Test connection
            wp = WordPressService(
                site_url=site.url,
                username=site.username,
                app_password=site.app_password
            )
            test_result = wp.test_connection()
            
            if test_result['success']:
                site.save()
                messages.success(request, f"WordPress site '{site.name}' added successfully!")
                return redirect('manage_sites')
            else:
                messages.error(request, f"Connection failed: {test_result['error']}")
    else:
        form = WordPressSiteForm()
    
    sites = WordPressSite.objects.filter(user=request.user)
    return render(request, 'sites.html', {'form': form, 'sites': sites})

@login_required
def delete_site(request, pk):
    site = get_object_or_404(WordPressSite, pk=pk, user=request.user)
    site.delete()
    messages.success(request, f"Site '{site.name}' deleted successfully!")
    return redirect('manage_sites')

@login_required
def test_site_connection(request, pk):
    site = get_object_or_404(WordPressSite, pk=pk, user=request.user)
    wp = WordPressService(
        site_url=site.url,
        username=site.username,
        app_password=site.app_password
    )
    result = wp.test_connection()
    return JsonResponse(result)