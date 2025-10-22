from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.core.files.storage import default_storage
from django.http import JsonResponse

import os
import json

from .models import WordPressSite, PublishedPost, UploadedImage
from .forms import CustomLoginForm, WordPressSiteForm, ContentGenerationForm, ContentEditForm
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
    """Generate content and save as preview for editing"""
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
                # Create post in preview status
                post = PublishedPost.objects.create(
                    user=request.user,
                    wordpress_site=form.cleaned_data['wordpress_site'],
                    title=result['title'],
                    topic=form.cleaned_data['topic'],
                    prompt=form.cleaned_data.get('prompt', ''),
                    affiliate_links=form.cleaned_data.get('affiliate_links', ''),
                    content=result['content'],
                    edited_content=result['content'],  # Start with generated content
                    html_content=result['content'],
                    status='preview'
                )
                
                # Handle image uploads
                images = request.FILES.getlist('images')
                for image in images:
                    UploadedImage.objects.create(
                        post=post,
                        image=image
                    )
                
                messages.success(request, "Content generated! Review and edit before publishing.")
                return redirect('edit_content', pk=post.pk)
            else:
                messages.error(request, f"Content generation failed: {result['error']}")
    else:
        form = ContentGenerationForm(request.user)
    
    return render(request, 'generate.html', {'form': form})

@login_required
def edit_content(request, pk):
    """Edit generated content before publishing"""
    post = get_object_or_404(PublishedPost, pk=pk, user=request.user)
    
    if request.method == 'POST':
        if 'save_draft' in request.POST:
            # Save changes without publishing
            post.title = request.POST.get('title', post.title)
            post.edited_content = request.POST.get('content', '')
            post.html_content = request.POST.get('content', '')
            post.affiliate_links = request.POST.get('affiliate_links', '')
            post.save()
            messages.success(request, "Draft saved successfully!")
            return redirect('edit_content', pk=post.pk)
        
        elif 'publish' in request.POST:
            # Save and publish to WordPress
            post.title = request.POST.get('title', post.title)
            post.edited_content = request.POST.get('content', '')
            post.html_content = request.POST.get('content', '')
            post.affiliate_links = request.POST.get('affiliate_links', '')
            post.save()
            
            # Publish to WordPress
            wp = WordPressService(
                site_url=post.wordpress_site.url,
                username=post.wordpress_site.username,
                app_password=post.wordpress_site.app_password
            )
            
            # Upload featured image if available
            featured_media_id = None
            if post.images.exists():
                first_image = post.images.first()
                media_result = wp.upload_media(
                    first_image.image.path,
                    os.path.basename(first_image.image.name)
                )
                if media_result['success']:
                    featured_media_id = media_result['media_id']
                    first_image.wordpress_media_id = str(media_result['media_id'])
                    first_image.wordpress_url = media_result['url']
                    first_image.save()
            
            # Publish with HTML content
            wp_result = wp.create_post(
                title=post.title,
                content=post.html_content,  # Use the edited HTML content
                status='publish',
                featured_media_id=featured_media_id,
                format='standard'
            )
            
            if wp_result['success']:
                post.wordpress_post_id = str(wp_result['post_id'])
                post.wordpress_url = wp_result['url']
                post.status = 'published'
                post.published_at = timezone.now()
                post.save()
                messages.success(request, f"Published successfully! View at: {wp_result['url']}")
                return redirect('dashboard')
            else:
                post.status = 'failed'
                post.error_message = wp_result['error']
                post.save()
                messages.error(request, f"Publishing failed: {wp_result['error']}")
    
    # Get current affiliate links as list
    affiliate_links_list = [link.strip() for link in post.affiliate_links.split('\n') if link.strip()]
    
    context = {
        'post': post,
        'affiliate_links_list': affiliate_links_list,
        'images': post.images.all(),
        'wordpress_site': post.wordpress_site,
    }
    return render(request, 'edit_content.html', context)

@login_required
def preview_content(request, pk):
    """Live preview of content as it will appear"""
    post = get_object_or_404(PublishedPost, pk=pk, user=request.user)
    return render(request, 'preview_content.html', {'post': post})

@login_required
def insert_affiliate_link(request):
    """AJAX endpoint to format and insert affiliate link"""
    if request.method == 'POST':
        data = json.loads(request.body)
        link_url = data.get('url', '')
        link_text = data.get('text', 'Check Latest Price')
        button_style = data.get('style', 'button')  # button, text, or card
        
        if button_style == 'button':
            html = f'''<div class="wp-block-buttons is-content-justification-center" style="margin:20px 0;">
                <div class="wp-block-button">
                    <a class="wp-block-button__link" href="{link_url}" target="_blank" 
                       rel="noopener noreferrer nofollow" 
                       style="background-color:#ff6b35;color:#ffffff;padding:12px 24px;border-radius:5px;">
                       {link_text}
                    </a>
                </div>
            </div>'''
        elif button_style == 'card':
            html = f'''<div class="affiliate-product-card" style="border:2px solid #e0e0e0;border-radius:8px;padding:20px;margin:20px 0;background:#f9f9f9;">
                <h3 style="color:#333;margin-top:0;">Featured Product</h3>
                <p>Check out this highly recommended option that thousands of users love.</p>
                <a href="{link_url}" target="_blank" rel="noopener noreferrer nofollow" 
                   style="display:inline-block;background:#28a745;color:white;padding:10px 20px;border-radius:5px;text-decoration:none;">
                   {link_text} →
                </a>
            </div>'''
        else:  # text link
            html = f'<a href="{link_url}" target="_blank" rel="noopener noreferrer nofollow" style="color:#0073aa;text-decoration:underline;">{link_text}</a>'
        
        return JsonResponse({'success': True, 'html': html})
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})



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
def delete(request,pk):
    post = get_object_or_404(PublishedPost,pk=pk,status='preview')
    post.delete()
    messages.success(request, f"The post by the name '{post.title}' deleted successfully!")
    return redirect('dashboard')

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