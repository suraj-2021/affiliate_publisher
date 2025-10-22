import os
import json
from django.urls import reverse
import uuid
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import Q, Count
from PIL import Image

from .models import (
    WordPressSite, PublishedPost, UploadedImage,
    InternalLinkRule, LinkingProfile, UserContentStrategy, ContentStage
)
from .forms import (
    CustomLoginForm, WordPressSiteForm,
    ContentGenerationForm, ContentEditForm
)
from .claude_service import ClaudeService
from .wordpress_service import WordPressService
from .internal_linking_service import InternalLinkingService

from django.contrib.auth import login as auth_login


def login_view(request):
    if request.method == 'POST':
        form = CustomLoginForm(request, data=request.POST)
        if form.is_valid():
            auth_login(request, form.get_user())  # use aliased login function
            return redirect('publisher:dashboard')
    else:
        form = CustomLoginForm()
    return render(request, 'login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required(login_url='publisher:login')
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
@require_POST
def ajax_stage_suggestions(request):
    """Get topic suggestions for a specific stage based on user's niche"""
    data = json.loads(request.body)
    stage = data.get('stage', 'stage1')
    
    # Get user's strategy to determine niche
    strategy, _ = UserContentStrategy.objects.get_or_create(user=request.user)
    user_niche = strategy.primary_niche or 'general'
    
    # Get existing topics from user's content to infer niche if not set
    existing_topics = list(PublishedPost.objects.filter(
        user=request.user,
        content_stage=stage
    ).values_list('topic', flat=True)[:5])
    
    # Generate niche-aware suggestions
    stage_suggestions = generate_stage_suggestions(stage, user_niche, existing_topics)
    
    # Get generic stage templates as fallback
    stage_templates = get_stage_templates(stage)
    
    return JsonResponse({
        'suggestions': stage_suggestions,
        'existing_topics': existing_topics,
        'stage_templates': stage_templates,  # Generic patterns they can adapt
        'stage_info': {
            'recommended_word_count': get_stage_word_count(stage),
            'content_style': get_stage_style(stage),
        }
    })


def generate_stage_suggestions(stage, niche, existing_topics):
    """Generate niche-appropriate suggestions for each stage"""
    
    # Niche-specific suggestion patterns
    niche_patterns = {
        'fitness': {
            'stage1': [
                'Complete Guide to {exercise_type}',
                'Everything You Need to Know About {fitness_topic}',
                'The Ultimate {workout_type} Guide for Beginners',
                'Comprehensive {equipment} Buying Guide',
                '{nutrition_topic}: The Complete Resource',
            ],
            'stage2': [
                'Best {equipment} Under ${price} ({year})',
                '{brand} {product} Review',
                '{product_a} vs {product_b}: Which Should You Buy?',
                'Top 10 {products} for {specific_goal}',
                'Best Budget {equipment} Under ${price}',
            ],
            'stage3': [
                'How to {achieve_goal}',
                'Why Does My {problem} Happen?',
                'Fix {common_issue}',
                'How to Choose the Right {parameter}',
                'What is {concept} and Do You Need It?',
            ],
        },
        'gaming': {
            'stage1': [
                'Complete Guide to Gaming Laptops in 2025',
                'Everything You Need to Know About Mechanical Keyboards',
                'The Ultimate PC Building Guide for Beginners',
                'Comprehensive Gaming Monitor Buying Guide',
                'Gaming Chair Ergonomics: The Complete Resource',
            ],
            'stage2': [
                'Best Gaming Laptops Under $1500 (2025)',
                'Razer DeathAdder V3 Pro Review',
                'RTX 4070 vs RTX 4060 Ti: Which Should You Buy?',
                'Top 10 Gaming Headsets for Competitive FPS',
                'Best Budget Gaming Keyboards Under $100',
            ],
            'stage3': [
                'How to Reduce Input Lag in Competitive Gaming',
                'Why Does My Gaming Laptop Overheat?',
                'Fix Discord Audio Issues While Gaming',
                'How to Choose the Right DPI for Gaming',
                'What is G-Sync and Do You Need It?',
            ],
        },
        'finance': {
            'stage1': [
                'Complete Guide to Personal Finance in 2025',
                'Everything You Need to Know About Investing',
                'The Ultimate Retirement Planning Guide',
                'Comprehensive Credit Score Improvement Guide',
                'Emergency Fund: The Complete Resource',
            ],
            'stage2': [
                'Best Investment Apps Under $10/month (2025)',
                'Vanguard vs Fidelity: Which Should You Choose?',
                'Top 10 High-Yield Savings Accounts',
                'Best Budget Investment Platforms',
                'Robinhood vs E*TRADE Review',
            ],
            'stage3': [
                'How to Pay Off Credit Card Debt Fast',
                'Why Does My Credit Score Keep Dropping?',
                'Fix Common 401(k) Mistakes',
                'How to Choose the Right Investment Strategy',
                'What is Dollar-Cost Averaging?',
            ],
        }
    }
    
    # Get patterns for user's niche, fallback to generic
    patterns = niche_patterns.get(niche, niche_patterns.get('general', []))
    
    if patterns and stage in patterns:
        return patterns[stage]
    else:
        # Generate dynamic suggestions based on existing content
        return generate_dynamic_suggestions(stage, existing_topics)


def generate_dynamic_suggestions(stage, existing_topics):
    """Generate suggestions based on user's existing content patterns"""
    if not existing_topics:
        return get_stage_templates(stage)
    
    # Extract common themes from existing topics
    common_words = extract_common_themes(existing_topics)
    
    # Stage-specific suggestion templates
    templates = {
        'stage1': [
            f'Complete Guide to {theme}' for theme in common_words[:3]
        ] + [f'Everything About {theme}' for theme in common_words[3:5]],
        
        'stage2': [
            f'Best {theme} Under $500' for theme in common_words[:2]
        ] + [f'{theme} Review and Comparison' for theme in common_words[2:5]],
        
        'stage3': [
            f'How to Choose the Right {theme}' for theme in common_words[:2]
        ] + [f'Common {theme} Problems and Solutions' for theme in common_words[2:5]],
        
        'stage4': [
            f'The Future of {theme}' for theme in common_words[:2]
        ] + [f'Why {theme} is Changing Everything' for theme in common_words[2:4]],
        
        'stage5': [
            f'{theme} for Specific Use Cases' for theme in common_words[:2]
        ] + [f'Advanced {theme} Strategies' for theme in common_words[2:4]],
        
        'stage6': [
            f'My Journey with {theme}' for theme in common_words[:2]
        ] + [f'Behind the Scenes: {theme}' for theme in common_words[2:4]],
    }
    
    return templates.get(stage, [])[:5]  # Return up to 5 suggestions


def get_stage_templates(stage):
    """Generic templates users can adapt to any niche"""
    templates = {
        'stage1': [
            'Complete Guide to [Your Main Topic]',
            'Everything You Need to Know About [Topic]',
            'The Ultimate [Topic] Guide for Beginners',
            'Comprehensive [Product Category] Buying Guide',
            '[Topic]: The Complete Resource',
        ],
        'stage2': [
            'Best [Products] Under $[Price] (2025)',
            '[Brand] [Product] Review',
            '[Product A] vs [Product B]: Which Should You Buy?',
            'Top 10 [Products] for [Specific Goal]',
            'Best Budget [Products] Under $[Price]',
        ],
        'stage3': [
            'How to [Achieve Goal]',
            'Why Does My [Problem] Happen?',
            'Fix [Common Issue]',
            'How to Choose the Right [Parameter]',
            'What is [Concept] and Do You Need It?',
        ],
        'stage4': [
            'The Future of [Your Industry]',
            'Why [Trend] is Changing Everything',
            'The Rise of [New Development]',
            'How [Technology] is Transforming [Industry]',
            'The [Impact] of [Change] on [Audience]',
        ],
        'stage5': [
            '[Products] for [Specific Use Case]',
            '[Topic] for [Niche Audience]',
            'Advanced [Topic] Strategies',
            '[Products] for [Specific Situations]',
            'Specialized [Topic] Guide',
        ],
        'stage6': [
            'My Journey Building a [Niche] Brand',
            'Exclusive: Behind the Scenes at [Your Business]',
            'Premium Member Guide: [Advanced Topic]',
            'Community Spotlight: [User Success Stories]',
            'Partnership Announcement: [Collaboration]',
        ],
    }
    
    return templates.get(stage, templates['stage1'])


def extract_common_themes(topics):
    """Extract common themes/words from existing topics"""
    import re
    from collections import Counter
    
    # Clean and extract meaningful words
    words = []
    for topic in topics:
        # Remove common stop words and extract meaningful terms
        clean_words = re.findall(r'\b[A-Za-z]{4,}\b', topic.lower())
        words.extend([w for w in clean_words if w not in {
            'best', 'guide', 'complete', 'ultimate', 'review', 'under',
            'need', 'know', 'about', 'with', 'your', 'this', 'that'
        }])
    
    # Get most common themes
    common = Counter(words).most_common(10)
    return [word.title() for word, count in common if count > 1]

@login_required
@require_POST
def ajax_update_strategy(request):
    """Update user's content strategy preferences"""
    data = json.loads(request.body)
    
    strategy, _ = UserContentStrategy.objects.get_or_create(user=request.user)
    
    if 'current_stage' in data:
        strategy.current_stage = data['current_stage']
    if 'primary_niche' in data:
        strategy.primary_niche = data['primary_niche']
    if 'target_audience' in data:
        strategy.target_audience = data['target_audience']
    if 'preferred_tone' in data:
        strategy.preferred_tone = data['preferred_tone']
    
    strategy.save()
    
    return JsonResponse({
        'success': True,
        'message': 'Strategy updated successfully'
    })


def get_stage_word_count(stage):
    """Get recommended word count for stage"""
    counts = {
        'stage1': 3000,
        'stage2': 2500,
        'stage3': 1500,
        'stage4': 2000,
        'stage5': 1500,
        'stage6': 2000,
    }
    return counts.get(stage, 2000)


def get_stage_style(stage):
    """Get recommended writing style for stage"""
    styles = {
        'stage1': 'authoritative',
        'stage2': 'persuasive',
        'stage3': 'instructional',
        'stage4': 'analytical',
        'stage5': 'specific',
        'stage6': 'personal',
    }
    return styles.get(stage, 'authoritative')


@login_required
def stage_details(request, stage_id):
    """Detailed view for a specific stage"""
    strategy, _ = UserContentStrategy.objects.get_or_create(user=request.user)
    
    # Get all posts for this stage
    posts = PublishedPost.objects.filter(
        user=request.user,
        content_stage=stage_id
    ).order_by('-created_at')
    
    # Get stage info
    stage_info = {
        'stage1': {
            'name': 'Foundational Pillars',
            'description': "Cornerstone content that establishes your site's authority. These are deep, evergreen guides covering broad gaming topics that serve as hubs for internal linking and long-term SEO value.",
            'best_practices': [
                'Target broad, evergreen topics',
                'Aim for 3000+ but < 4500 words with in-depth coverage',
                'Include structured headings and internal links',
                'Design for long-term relevance and authority',
            ],
            'examples': [
                'Ultimate Guide to Gaming Laptops',
                'Complete PC Building Tutorial for Beginners',
                'Everything You Need to Know About Mechanical Keyboards',
            ],
        },
        'stage2': {
            'name': 'Conversion Content (Reviews & Buying Guides)',
            'description': 'Focused on driving affiliate revenue by helping readers make confident purchase decisions. Includes reviews, comparisons, and best-of lists with balanced insights.',
            'best_practices': [
                'Write honest, balanced reviews',
                'Include pros, cons, and real-world use cases',
                'Use comparison tables and buyer-focused recommendations',
                'Naturally integrate affiliate links without overselling',
            ],
            'examples': [
                'Best Gaming Chairs Under $300',
                'Top 10 Gaming Monitors for Esports in 2025',
                'Razer vs Logitech: Which Gaming Mouse Should You Buy?',
            ],
        },
        'stage3': {
            'name': 'Supporting Content (Topic Clusters)',
            'description': 'Articles that target long-tail keywords and answer specific gamer questions. These posts drive steady traffic and link back to pillar and conversion content.',
            'best_practices': [
                'Target long-tail queries (how-to, why, what)',
                'Keep articles 1200–2000 words for focus',
                'Interlink with pillar and buying guides',
                'Provide actionable steps and clear answers',
            ],
            'examples': [
                'How to Reduce Lag in Online Games',
                'Best Settings for 144Hz Monitors',
                'How to Clean and Maintain Your Gaming Keyboard',
            ],
        },
        'stage4': {
            'name': 'Authority & Community Content',
            'description': 'Content that elevates your brand as part of the gaming community. Covers trends, cultural discussions, and expert-level insights to boost E-E-A-T and engagement.',
            'best_practices': [
                'Cover emerging trends and cultural topics',
                'Use data, expert quotes, or case studies',
                'Encourage comments and discussions',
                'Aim for shareability and backlinks',
            ],
            'examples': [
                'The Rise of Cloud Gaming: What It Means for PC Gamers',
                'Why Esports Training Rivals Traditional Sports',
                'The Future of VR Gaming in 2025 and Beyond',
            ],
        },
        'stage5': {
            'name': 'Ecosystem Expansion & Monetization Scaling',
            'description': 'Scaling content output and diversifying revenue streams. Beyond affiliate links, this stage explores ads, sponsorships, and digital products.',
            'best_practices': [
                'Identify content gaps and cover all subtopics',
                'Expand into multiple monetization models',
                'Offer digital resources (checklists, eBooks, guides)',
                'Keep content practical and utility-driven',
            ],
            'examples': [
                'How to Boost FPS in Apex Legends Without Upgrading Hardware',
                'Best Streaming Gear for Gamers on a Budget',
                'Downloadable Gaming Setup Checklist (Free Resource)',
            ],
        },
        'stage6': {
            'name': 'Advanced Funnel & Brand Building',
            'description': 'Building a loyal audience and brand beyond SEO. Includes funnels, newsletters, video platforms, and partnerships to future-proof growth.',
            'best_practices': [
                'Launch an email newsletter with lead magnets',
                'Create video or streaming content (YouTube/Twitch)',
                'Develop community spaces (Discord, forums)',
                'Build sponsorships and long-term brand deals',
            ],
            'examples': [
                'Weekly Gamer Digest Newsletter',
                'Exclusive Discord Community for PC Builders',
                'Ultimate PC Build Guide PDF (Lead Magnet)',
            ],
        },
    }
    
    context = {
        'stage_id': stage_id,
        'stage_info': stage_info.get(stage_id, {}),
        'posts': posts,
        'post_count': posts.count(),
        'total_words': sum(len(p.content.split()) for p in posts),
        'strategy': strategy,
    }
    
    return render(request, 'stage_details.html', context)


@login_required
def generate_content(request):
    """Generate content with stage-based approach"""
    
    # Get or create user's content strategy
    strategy, created = UserContentStrategy.objects.get_or_create(
        user=request.user
    )
    
    if request.method == 'POST':
        form = ContentGenerationForm(request.user, request.POST, request.FILES)
        if form.is_valid():
           
            # Handle image uploads first
            uploaded_images = []
            image_urls = []
            alt_texts = form.cleaned_data.get('image_alt_text', '').split('\n')
            
            images = request.FILES.getlist('images')
            for i, image in enumerate(images):
                # Process and optimize image
                processed_image = process_uploaded_image(image)
                
                # Save to media directory
                image_path = save_uploaded_image(processed_image, request.user)
                
                # Get alt text
                alt_text = alt_texts[i] if i < len(alt_texts) else f"Image {i+1}"
                
                uploaded_images.append({
                    'path': image_path,
                    'url': default_storage.url(image_path),
                    'alt_text': alt_text.strip(),
                    'original_name': image.name
                })
                
                image_urls.append(default_storage.url(image_path))
            
            content_stage = request.GET.get('stage') or 'stage1'
            
            # Get internal links if enabled
            linking_service = InternalLinkingService(request.user)
            internal_links = []
            
            if form.cleaned_data.get('include_internal_links', True):
                # Prioritize links based on stage
                if content_stage in ['stage1', 'stage2']:
                    # Link to other pillar content
                    relevant_posts = PublishedPost.objects.filter(
                        user=request.user,
                        status='published',
                        pillar_post=True
                    ).exclude(id=request.POST.get('post_id'))[:3]
                else:
                    # Link to pillar and related content
                    relevant_posts = linking_service.find_relevant_posts(
                        topic=form.cleaned_data['topic'],
                        content=form.cleaned_data.get('prompt', ''),
                        limit=5
                    )
                
                internal_links = [
                    {
                        'title': post.title,
                        'url': post.wordpress_url,
                        'id': post.id
                    }
                    for post in relevant_posts if post.wordpress_url
                ]
            
            # Generate content with Claude
            claude = ClaudeService()
            result = claude.generate_affiliate_content(
                topic=form.cleaned_data['topic'],
                prompt=form.cleaned_data.get('prompt'),
                affiliate_links=form.cleaned_data.get('affiliate_links'),
                content_stage=content_stage,
                word_count=form.cleaned_data.get('word_count', 2500),
                internal_links=internal_links
            )
            
            if result['success']:
                # Get the generated content
                base_content = result['content']
                
                # Apply image insertion if needed
                final_content = base_content
                if uploaded_images and form.cleaned_data.get('auto_insert_images'):
                    final_content = insert_images_into_content(base_content, uploaded_images)
                
                # Apply internal linking for pillar content only (stage-specific enhancement)
                if content_stage in ['stage1', 'stage2'] and internal_links:
                    final_content, inserted_links = linking_service.auto_insert_internal_links(
                        final_content,
                        form.cleaned_data['topic']
                    )
                
                # Create post with stage information
                post = PublishedPost.objects.create(
                    user=request.user,
                    wordpress_site=form.cleaned_data['wordpress_site'],
                    title=result['title'],
                    topic=form.cleaned_data['topic'],
                    prompt=form.cleaned_data.get('prompt', ''),
                    affiliate_links=form.cleaned_data.get('affiliate_links', ''),
                    content=result['content'],  # Original generated content
                    edited_content=final_content,  # Content with images and links
                    html_content=final_content,  # HTML version for publishing
                    keywords=result.get('keywords', ''),
                    content_stage=content_stage,
                    pillar_post=form.cleaned_data.get('pillar_post', False),
                    conversion_focused=form.cleaned_data.get('conversion_focused', False),
                    status='preview'
                )
                
                # Save image records
                featured_index = form.cleaned_data.get('featured_image_index', 0)
                for i, img_data in enumerate(uploaded_images):
                    img_instance = UploadedImage.objects.create(
                        post=post,
                        image=img_data['path'],
                        alt_text=img_data['alt_text'],
                        is_featured=(i == featured_index),
                        wordpress_media_id='',
                        wordpress_url=''
                    )
                
                # Update stage count in user strategy
                strategy.increment_stage_count(content_stage)
                
                messages.success(request, f"Content generated successfully with {len(uploaded_images)} images!")
                return redirect('publisher:edit_content', pk=post.pk)
            else:
                messages.error(request, f"Generation failed: {result['error']}")
    else:
        form = ContentGenerationForm(request.user)
    
    # Get stage statistics
    stage_counts = strategy.get_stage_progress()
    
    # Calculate recommendations
    recommended_stage = calculate_recommended_stage(stage_counts)
    
    # Get related posts for context
    related_posts = PublishedPost.objects.filter(
        user=request.user,
        status='published'
    ).order_by('-published_at')[:10]
    
    # Calculate progress
    total_posts = sum(stage_counts.values())
    posts_this_month = PublishedPost.objects.filter(
        user=request.user,
        created_at__month=timezone.now().month
    ).count()
    
    # Overall progress (simple calculation)
    target_total = 60  # Rough target for all stages
    overall_progress = min(100, int((total_posts / target_total) * 100))

    context = {
        'form': form,
        'stage_counts': stage_counts,
        'recommended_stage': recommended_stage,
        'related_posts': related_posts,
        'total_posts': total_posts,
        'posts_this_month': posts_this_month,
        'overall_progress': overall_progress,
        'strategy': strategy,
    }
    
    return render(request, 'generate.html', context)


def process_uploaded_image(image_file):
    """Process and optimize uploaded image"""
    try:
        # Open image with Pillow
        img = Image.open(image_file)
        
        # Convert RGBA to RGB if necessary
        if img.mode in ('RGBA', 'LA', 'P'):
            rgb_img = Image.new('RGB', img.size, (255, 255, 255))
            rgb_img.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = rgb_img
        
        # Resize if too large (max 1920px width)
        if img.width > 1920:
            ratio = 1920 / img.width
            new_size = (1920, int(img.height * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
        
        # Optimize quality
        output = ContentFile(b'')
        img.save(output, format='JPEG', quality=85, optimize=True)
        output.seek(0)
        
        return output
    except Exception as e:
        print(f"Image processing error: {e}")
        return image_file


def save_uploaded_image(image_file, user):
    """Save uploaded image to media directory"""
    # Generate unique filename
    ext = 'jpg'  # We convert everything to JPEG
    filename = f"uploads/{user.id}/{uuid.uuid4()}.{ext}"
    
    # Save to storage
    path = default_storage.save(filename, image_file)
    return path


def insert_images_into_content(content, images):
    """Replace [IMAGE: ...] placeholders with actual HTML"""
    for img in images:
        placeholder = f"[IMAGE: {img['alt_text']}]"
        
        # WordPress-compatible image HTML
        img_html = f'''
        <figure class="wp-block-image size-large">
            <img src="{img['url']}" 
                 alt="{img['alt_text']}" 
                 class="wp-image"
                 loading="lazy">
            <figcaption>{img['alt_text']}</figcaption>
        </figure>
        '''
        
        content = content.replace(placeholder, img_html, 1)  # Replace only first occurrence
    
    return content


@login_required
def publish_content(request, pk):
    """Publish content directly to WordPress"""
    post = get_object_or_404(PublishedPost, pk=pk, user=request.user)
    
    if post.wordpress_site:
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
        
        # Publish to WordPress
        wp_result = wp.create_post(
            title=post.title,
            content=post.html_content or post.edited_content or post.content,
            status='publish',
            featured_media_id=featured_media_id
        )
        
        if wp_result['success']:
            post.wordpress_post_id = str(wp_result['post_id'])
            post.wordpress_url = wp_result['url']
            post.status = 'published'
            post.published_at = timezone.now()
            post.save()
            
            messages.success(request, f"Published successfully! View at: {wp_result['url']}")
        else:
            post.status = 'failed'
            post.error_message = wp_result['error']
            post.save()
            messages.error(request, f"Publishing failed: {wp_result['error']}")
    
    return redirect('publisher:dashboard')


@login_required
def manage_internal_links(request):
    """Manage internal linking rules and preferences"""
    profile, _ = LinkingProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        # Update profile settings
        profile.auto_link_enabled = request.POST.get('auto_link_enabled') == 'on'
        profile.max_internal_links = int(request.POST.get('max_internal_links', 5))
        profile.prefer_same_category = request.POST.get('prefer_same_category') == 'on'
        profile.vary_anchor_text = request.POST.get('vary_anchor_text') == 'on'
        profile.save()
        messages.success(request, "Internal linking preferences updated!")
        return redirect('publisher:manage_internal_links')
    
    # Get existing rules
    rules = InternalLinkRule.objects.filter(user=request.user).select_related('target_post')
    
    # Get link statistics
    posts_with_most_links = PublishedPost.objects.filter(
        user=request.user,
        status='published'
    ).order_by('-link_to_this_count')[:10]
    
    context = {
        'profile': profile,
        'rules': rules,
        'popular_posts': posts_with_most_links,
    }
    return render(request, 'internal_links.html', context)


@login_required
def ajax_get_related_posts(request):
    """AJAX endpoint to get related posts for manual linking"""
    if request.method == 'POST':
        data = json.loads(request.body)
        topic = data.get('topic', '')
        content = data.get('content', '')
        
        linking_service = InternalLinkingService(request.user)
        suggestions = linking_service.get_linking_suggestions(topic, content)
        
        return JsonResponse(suggestions)
    
    return JsonResponse({'error': 'Invalid request'}, status=400)


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
            return redirect('publisher:edit_content', pk=post.pk)
        
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
                return redirect('publisher:dashboard')
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
                return redirect('publisher:manage_sites')
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
    return redirect('publisher:manage_sites')


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


@login_required
def linking_rules(request):
    """Display all linking rules"""
    rules = InternalLinkRule.objects.filter(user=request.user).select_related('target_post')
    return render(request, 'linking_rules.html', {'rules': rules})


@login_required
def add_linking_rule(request):
    """Add a new linking rule"""
    if request.method == 'POST':
        keyword = request.POST.get('keyword')
        target_post_id = request.POST.get('target_post')
        priority = request.POST.get('priority', 1)
        
        try:
            target_post = PublishedPost.objects.get(id=target_post_id, user=request.user)
            rule, created = InternalLinkRule.objects.get_or_create(
                user=request.user,
                keyword=keyword,
                target_post=target_post,
                defaults={
                    'priority': int(priority),
                    'max_usage': 3
                }
            )
            if created:
                messages.success(request, f"Linking rule for '{keyword}' created successfully!")
            else:
                messages.info(request, f"Rule for '{keyword}' already exists")
        except PublishedPost.DoesNotExist:
            messages.error(request, "Invalid post selected")
        
        return redirect('publisher:linking_rules')
    
    # GET request - show form
    posts = PublishedPost.objects.filter(user=request.user, status='published')
    return render(request, 'add_linking_rule.html', {'posts': posts})


@login_required
def edit_linking_rule(request, pk):
    """Edit an existing linking rule"""
    rule = get_object_or_404(InternalLinkRule, pk=pk, user=request.user)
    
    if request.method == 'POST':
        rule.keyword = request.POST.get('keyword', rule.keyword)
        rule.priority = int(request.POST.get('priority', rule.priority))
        rule.max_usage = int(request.POST.get('max_usage', rule.max_usage))
        rule.save()
        messages.success(request, "Rule updated successfully!")
        return redirect('publisher:linking_rules')
    
    return render(request, 'edit_linking_rule.html', {'rule': rule})


@login_required
@require_POST
def delete_linking_rule(request, pk):
    """Delete a linking rule"""
    rule = get_object_or_404(InternalLinkRule, pk=pk, user=request.user)
    rule.delete()
    messages.success(request, "Rule deleted successfully!")
    return redirect('publisher:linking_rules')


@login_required
@require_POST
def toggle_linking_rule(request, pk):
    """Toggle rule active/inactive"""
    rule = get_object_or_404(InternalLinkRule, pk=pk, user=request.user)
    rule.is_active = not rule.is_active
    rule.save()
    return JsonResponse({'status': 'success', 'is_active': rule.is_active})


@login_required
def ajax_link_suggestions(request):
    """Get link suggestions via AJAX"""
    if request.method == 'POST':
        data = json.loads(request.body)
        topic = data.get('topic', '')
        content = data.get('content', '')
        
        service = InternalLinkingService(request.user)
        suggestions = service.get_linking_suggestions(topic, content)
        
        return JsonResponse(suggestions)
    
    return JsonResponse({'error': 'Invalid request'}, status=400)


@login_required
@require_POST
def ajax_create_rule(request):
    """Create linking rule via AJAX"""
    try:
        data = json.loads(request.body)
        keyword = data.get('keyword')
        target_post_id = data.get('target_post_id')
        
        target_post = PublishedPost.objects.get(id=target_post_id, user=request.user)
        rule, created = InternalLinkRule.objects.get_or_create(
            user=request.user,
            keyword=keyword,
            target_post=target_post,
            defaults={'priority': 5, 'max_usage': 3}
        )
        
        return JsonResponse({
            'success': True,
            'created': created,
            'rule_id': rule.id
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def delete_post(request, pk):
    """Delete a post"""
    post = get_object_or_404(PublishedPost, pk=pk, user=request.user)

    post.delete()
    messages.success(request, "Post deleted successfully!")
    return redirect('publisher:dashboard')


@login_required
@require_POST
def ajax_save_draft(request):
    """Auto-save draft via AJAX"""
    try:
        data = json.loads(request.body)
        post_id = data.get('post_id')
        content = data.get('content')
        
        post = PublishedPost.objects.get(id=post_id, user=request.user)
        post.edited_content = content
        post.save(update_fields=['edited_content'])
        
        return JsonResponse({'success': True, 'saved_at': post.created_at.isoformat()})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def user_settings(request):
    """User settings and preferences"""
    profile, _ = LinkingProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        # Update settings
        profile.auto_link_enabled = request.POST.get('auto_link_enabled') == 'on'
        profile.max_internal_links = int(request.POST.get('max_internal_links', 5))
        profile.vary_anchor_text = request.POST.get('vary_anchor_text') == 'on'
        profile.save()
        
        messages.success(request, "Settings updated successfully!")
        return redirect('publisher:user_settings')
    
    return render(request, 'settings.html', {'profile': profile})


@login_required
def bulk_generate(request):
    """Bulk content generation"""
    if request.method == 'POST':
        topics = request.POST.get('topics', '').split('\n')
        site_id = request.POST.get('wordpress_site')
        
        # Process bulk generation
        for topic in topics:
            if topic.strip():
                # Create task for each topic
                # You might want to use Celery for async processing
                pass
        
        messages.success(request, f"Started generating {len(topics)} posts")
        return redirect('publisher:dashboard')
    
    sites = WordPressSite.objects.filter(user=request.user, is_active=True)
    return render(request, 'bulk_generate.html', {'sites': sites})


@login_required
def bulk_publish(request):
    """Bulk publish drafted posts"""
    if request.method == 'POST':
        post_ids = request.POST.getlist('post_ids')
        posts = PublishedPost.objects.filter(id__in=post_ids, user=request.user)
        
        published_count = 0
        for post in posts:
            # Publish each post
            # Add your WordPress publishing logic here
            published_count += 1
        
        messages.success(request, f"Published {published_count} posts")
        return redirect('publisher:dashboard')
    
    draft_posts = PublishedPost.objects.filter(user=request.user, status='draft')
    return render(request, 'bulk_publish.html', {'posts': draft_posts})


@login_required
def export_settings(request):
    """Export user settings and rules"""
    profile = LinkingProfile.objects.get(user=request.user)
    rules = InternalLinkRule.objects.filter(user=request.user)
    
    export_data = {
        'profile': {
            'auto_link_enabled': profile.auto_link_enabled,
            'max_internal_links': profile.max_internal_links,
            'vary_anchor_text': profile.vary_anchor_text,
        },
        'rules': [
            {
                'keyword': rule.keyword,
                'target_post_title': rule.target_post.title,
                'priority': rule.priority,
                'max_usage': rule.max_usage,
            }
            for rule in rules
        ]
    }
    
    response = JsonResponse(export_data, json_dumps_params={'indent': 2})
    response['Content-Disposition'] = 'attachment; filename="linking_settings.json"'
    return response


@login_required
def add_site(request):
    """Add a new WordPress site"""
    if request.method == 'POST':
        form = WordPressSiteForm(request.POST)
        if form.is_valid():
            site = form.save(commit=False)
            site.user = request.user
            site.save()
            messages.success(request, "Site added successfully!")
            return redirect('publisher:manage_sites')
    else:
        form = WordPressSiteForm()
    
    return render(request, 'add_site.html', {'form': form})


@login_required
def edit_site(request, pk):
    """Edit WordPress site"""
    site = get_object_or_404(WordPressSite, pk=pk, user=request.user)
    
    if request.method == 'POST':
        form = WordPressSiteForm(request.POST, instance=site)
        if form.is_valid():
            form.save()
            messages.success(request, "Site updated successfully!")
            return redirect('publisher:manage_sites')
    else:
        form = WordPressSiteForm(instance=site)
    
    return render(request, 'edit_site.html', {'form': form, 'site': site})


def calculate_recommended_stage(stage_counts):
    """Calculate which stage to focus on next"""
    
    # Stage targets
    targets = {
        'stage1': 8,   # 8 pillar posts
        'stage2': 15,  # 15 conversion posts
        'stage3': 25,  # 25 supporting posts
        'stage4': 10,  # 10 authority posts
        'stage5': 20,  # 20 ecosystem posts
        'stage6': 10,  # 10 brand posts
    }
    
    # Find stages that need more content
    for stage, target in targets.items():
        if stage_counts.get(stage, 0) < target:
            # Check prerequisites
            if stage == 'stage2' and stage_counts.get('stage1', 0) < 5:
                return 'stage1'  # Need more pillars first
            elif stage == 'stage3' and stage_counts.get('stage2', 0) < 10:
                return 'stage2'  # Need more conversion content first
            else:
                return stage
    
    # All stages have enough content
    return 'stage6'  # Focus on brand building


@login_required
def stage_overview(request):
    """Display overview of content stages and progress"""
    strategy, _ = UserContentStrategy.objects.get_or_create(user=request.user)
    
    # Get posts by stage
    posts_by_stage = {}
    for stage_id, stage_name in ContentStage.STAGE_CHOICES:
        posts_by_stage[stage_id] = PublishedPost.objects.filter(
            user=request.user,
            content_stage=stage_id
        ).order_by('-created_at')[:5]
    
    # Get stage descriptions
    stage_info = {
        'stage1': {
            'name': 'Foundational Pillars',
            'description': 'Cornerstone content that establishes authority',
            'target': 8,
            'icon': '📚'
        },
        'stage2': {
            'name': 'Conversion Content',
            'description': 'Reviews and buying guides that drive revenue',
            'target': 15,
            'icon': '💰'
        },
        'stage3': {
            'name': 'Supporting Content',
            'description': 'Long-tail keywords and specific questions',
            'target': 25,
            'icon': '🔍'
        },
        'stage4': {
            'name': 'Authority & Community',
            'description': 'Thought leadership and engagement',
            'target': 10,
            'icon': '🏆'
        },
        'stage5': {
            'name': 'Ecosystem Expansion',
            'description': 'Complete niche coverage',
            'target': 20,
            'icon': '🌐'
        },
        'stage6': {
            'name': 'Brand Building',
            'description': 'Premium content and funnels',
            'target': 10,
            'icon': '🚀'
        }
    }
    
    context = {
        'strategy': strategy,
        'posts_by_stage': posts_by_stage,
        'stage_info': stage_info,
        'stage_progress': strategy.get_stage_progress(),
    }
    
    return render(request, 'stage_overview.html', context)