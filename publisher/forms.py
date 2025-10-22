from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import WordPressSite, PublishedPost
from django.core.validators import FileExtensionValidator


# forms.py

from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from .models import WordPressSite, PublishedPost,ContentStage

class MultipleFileInput(forms.ClearableFileInput):
    """Custom widget for multiple file uploads"""
    allow_multiple_selected = True

class MultipleFileField(forms.FileField):
    """Custom field for multiple file uploads"""
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result


class CustomLoginForm(AuthenticationForm):
    """Custom login form with Bootstrap styling"""
    username = forms.CharField(
        max_length=254,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Username',
            'autofocus': True
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password'
        })
    )
    
    error_messages = {
        'invalid_login': "Please enter a correct username and password.",
        'inactive': "This account is inactive.",
    }


class WordPressSiteForm(forms.ModelForm):
    """Form for adding/editing WordPress sites"""
    class Meta:
        model = WordPressSite
        fields = ['name', 'url', 'username', 'app_password']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., My Blog',
                'required': True
            }),
            'url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://yourdomain.com',
                'required': True
            }),
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'WordPress username',
                'required': True
            }),
            'app_password': forms.PasswordInput(attrs={
                'class': 'form-control',
                'placeholder': 'Application password',
                'required': True,
                'help_text': 'Generate this in WordPress under Users → Profile → Application Passwords'
            }),
        }
        labels = {
            'name': 'Site Name',
            'url': 'WordPress URL',
            'username': 'WordPress Username',
            'app_password': 'Application Password',
        }
        help_texts = {
            'url': 'Full URL including https://',
            'app_password': 'Generate in WordPress: Users → Profile → Application Passwords',
        }
    
    def clean_url(self):
        """Ensure URL is properly formatted"""
        url = self.cleaned_data.get('url')
        if url:
            # Remove trailing slash if present
            url = url.rstrip('/')
            # Ensure it starts with http:// or https://
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
        return url
    
    def clean_app_password(self):
        """Remove spaces from app password (WordPress adds spaces for readability)"""
        app_password = self.cleaned_data.get('app_password')
        if app_password:
            # Remove all spaces (WordPress formats passwords with spaces)
            app_password = app_password.replace(' ', '')
        return app_password


class ContentGenerationForm(forms.Form):
      
    content_stage = forms.ChoiceField(
        choices=ContentStage.STAGE_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-control form-control-lg',
            'id': 'contentStage',
            'onchange': 'updateStageGuidance()'
        }),
        initial='stage1',
        label='Content Stage',
        help_text='Select which stage of your content strategy this post belongs to'
        )
    

        # PROPER IMAGE FIELD
    images = MultipleFileField(
        required=False,
        label='Upload Images',
        help_text='Select multiple images (JPG, PNG, GIF, WebP) - Max 5MB each',
        validators=[
            FileExtensionValidator(
                allowed_extensions=['jpg', 'jpeg', 'png', 'gif', 'webp']
            )
        ],
        widget=MultipleFileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*',
            'multiple': True,
            'id': 'imageUpload'
        })
    )
    
    # Image handling options
    auto_insert_images = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'id': 'autoInsertImages'
        }),
        label='Auto-insert images into content',
        help_text='Automatically place images throughout the content'
        )
    
    featured_image_index = forms.IntegerField(
        required=False,
        initial=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'id': 'featuredImageIndex',
            'min': 0,
            'max': 10
        }),
        label='Featured Image',
        help_text='Which image to use as featured (0 = first image)'
    )
    
    image_alt_text = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'id': 'imageAltText',
            'placeholder': 'Image 1: Alt text here\nImage 2: Alt text here'
        }),
        label='Image Alt Text (SEO)',
        help_text='One alt text per line, matching image order'
    )
    
    word_count = forms.IntegerField(
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'id': 'wordCount',
            'step': 500,
            'min': 500,
            'max': 10000
        }),
        label='Target Word Count',
        initial=2500
        )
    
    
   
    
    word_count = forms.IntegerField(
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'id': 'wordCount',
            'step': 500
        }),
        label='Target Word Count',
        initial=2500
    )
    
    content_style = forms.ChoiceField(
        choices=[
            ('authoritative', 'Authoritative Expert'),
            ('friendly', 'Friendly Advisor'),
            ('technical', 'Technical Specialist'),
            ('conversational', 'Conversational Guide'),
            ('analytical', 'Data-Driven Analyst'),
        ],
        widget=forms.Select(attrs={
            'class': 'form-control',
            'id': 'contentStyle',
        }
        ),
        initial='authoritative',
        label='Writing Tone',
    )
    
    pillar_post = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'id': 'pillarPost'
        }),
        label='Mark as Pillar Post',
        help_text='Pillar posts are comprehensive, cornerstone content pieces'
    )
    
    conversion_focused = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'id': 'conversionFocused'
        }),
        label='Conversion Focused',
        help_text='Optimize for affiliate conversions'
    )
    
    include_comparison_table = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'id': 'comparisonTable'
        }),
        label='Include Product Comparison Table'
    )
    
    include_buyers_guide = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'id': 'buyersGuide'
        }),
        label='Include Buyer\'s Guide Section'
    )


    """Form for generating content with Claude AI"""
    wordpress_site = forms.ModelChoiceField(
        queryset=WordPressSite.objects.none(),
        widget=forms.Select(attrs={
            'class': 'form-control',
            'required': True
        }),
        label='Select WordPress Site',
        empty_label='-- Choose a site --'
    )
    
    topic = forms.CharField(
        max_length=500,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., Best Running Shoes for Beginners 2024',
            'required': True
        }),
        label='Content Topic',
        help_text='Enter the main topic or title for your content'
    )
    
    prompt = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 5,
        }),
        label='Additional Instructions (Optional)',
        help_text='Provide any specific guidance for content generation',
        initial="""Target audience: first-time DSLR buyers who are beginners in photography.  
    Angle: focus on affordable and easy-to-use cameras under $700 in 2025.  
    Style: friendly, storytelling, include comparisons with pros/cons.  
    SEO keywords: "best beginner DSLR 2025", "budget DSLR for photography", "affordable DSLR camera".  
    Extra: add a small section on mistakes beginners should avoid when buying a camera."""
    )
    
    affiliate_links = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Enter affiliate links (one per line):\n'
                          'https://amazon.com/product1\n'
                          'https://affiliate.site/product2'
        }),
        label='Affiliate Links (Optional)',
        help_text='Add affiliate links to be incorporated into the content (one per line)'
    )


    include_internal_links = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'id': 'includeInternalLinks'
        }),
        label='Auto-add internal links to related posts',
        help_text='Automatically link to your previous relevant content for better SEO and user experience'
        )

    link_to_recent = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label='Include links from last 30 days',
        help_text='Prioritize linking to your recent content'
        )
    wordpress_site = forms.ModelChoiceField(
        queryset=WordPressSite.objects.none(),
        widget=forms.Select(attrs={
            'class': 'form-control',
            'required': True,
            'id': 'wordpressSite'
        }),
        empty_label="-- Select a WordPress site --",
        label='Target WordPress Site',
        help_text='Where to publish this content'
    )
    
    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['wordpress_site'].queryset = WordPressSite.objects.filter(
            user=user,
            is_active=True
        )
    
    def clean_images(self):
        """Validate uploaded images"""
        images = self.files.getlist('images')
        
        if len(images) > 10:
            raise forms.ValidationError('Maximum 10 images allowed')
        
        for image in images:
            if image.size > 5 * 1024 * 1024:  # 5MB
                raise forms.ValidationError(f'{image.name} is too large. Max size is 5MB')
        
        return images
    
    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['wordpress_site'].queryset = WordPressSite.objects.filter(
            user=user, is_active=True
        )
        
        # Add custom validation message if no sites
        if not self.fields['wordpress_site'].queryset.exists():
            self.fields['wordpress_site'].help_text = 'Please add a WordPress site first'
        
        if 'initial' in kwargs and 'content_stage' in kwargs['initial']:
            stage = kwargs['initial']['content_stage']
            word_counts = {
                'stage1': 3000,  # Pillar content
                'stage2': 2500,  # Reviews
                'stage3': 1500,  # Supporting
                'stage4': 2000,  # Authority
                'stage5': 1500,  # Ecosystem
                'stage6': 2000,  # Brand
            }
            self.fields['word_count'].initial = word_counts.get(stage, 2500)
    def clean_affiliate_links(self):
        """Validate and clean affiliate links"""
        links = self.cleaned_data.get('affiliate_links', '')
        if links:
            # Split by newlines and clean each link
            cleaned_links = []
            for link in links.split('\n'):
                link = link.strip()
                if link:
                    # Basic URL validation
                    if not link.startswith(('http://', 'https://')):
                        link = 'https://' + link
                    cleaned_links.append(link)
            return '\n'.join(cleaned_links)
        return links
    
    def clean(self):
        """Additional form validation"""
        cleaned_data = super().clean()
        
        # Ensure at least topic is provided
        topic = cleaned_data.get('topic')
        if not topic:
            raise forms.ValidationError('Topic is required to generate content')
        
        return cleaned_data
    
    


class ContentEditForm(forms.ModelForm):
    """Form for editing generated content before publishing"""
    class Meta:
        model = PublishedPost
        fields = ['title', 'edited_content', 'affiliate_links']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control form-control-lg',
                'placeholder': 'Post Title',
                'required': True
            }),
            'edited_content': forms.Textarea(attrs={
                'class': 'form-control content-editor',
                'rows': 20,
                'id': 'content-editor',
                'required': True
            }),
            'affiliate_links': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Affiliate links (one per line)'
            }),
        }
        labels = {
            'title': 'Post Title',
            'edited_content': 'Content',
            'affiliate_links': 'Affiliate Links',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make edited_content use html_content if available
        if self.instance and self.instance.html_content:
            self.initial['edited_content'] = self.instance.html_content
    
    def clean_edited_content(self):
        """Ensure content is not empty"""
        content = self.cleaned_data.get('edited_content')
        if not content or not content.strip():
            raise forms.ValidationError('Content cannot be empty')
        return content


class BulkActionForm(forms.Form):
    """Form for bulk actions on posts"""
    ACTION_CHOICES = [
        ('', '-- Select Action --'),
        ('publish', 'Publish Selected'),
        ('delete', 'Delete Selected'),
        ('draft', 'Save as Draft'),
    ]
    
    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        required=True,
        widget=forms.Select(attrs={
            'class': 'form-control form-control-sm',
            'style': 'width: auto; display: inline-block;'
        })
    )
    
    selected_posts = forms.MultipleChoiceField(
        required=False,
        widget=forms.CheckboxSelectMultiple
    )


class FilterForm(forms.Form):
    """Form for filtering posts in dashboard"""
    STATUS_CHOICES = [
        ('', 'All Statuses'),
        ('preview', 'Preview'),
        ('published', 'Published'),
        ('failed', 'Failed'),
        ('draft', 'Draft'),
    ]
    
    wordpress_site = forms.ModelChoiceField(
        queryset=WordPressSite.objects.none(),
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control form-control-sm',
            'style': 'width: auto;'
        }),
        empty_label='All Sites'
    )
    
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control form-control-sm',
            'style': 'width: auto;'
        })
    )
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-sm',
            'placeholder': 'Search posts...',
            'style': 'width: 200px;'
        })
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control form-control-sm',
            'type': 'date',
            'style': 'width: auto;'
        })
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control form-control-sm',
            'type': 'date',
            'style': 'width: auto;'
        })
    )
    
    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter WordPress sites to only show user's sites
        self.fields['wordpress_site'].queryset = WordPressSite.objects.filter(
            user=user
        )


class QuickPublishForm(forms.Form):
    """Simplified form for quick content creation and publishing"""
    wordpress_site = forms.ModelChoiceField(
        queryset=WordPressSite.objects.none(),
        widget=forms.Select(attrs={
            'class': 'form-control',
            'required': True
        }),
        label='WordPress Site'
    )
    
    title = forms.CharField(
        max_length=500,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Post title',
            'required': True
        })
    )
    
    content = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 10,
            'placeholder': 'Write or paste your content here...',
            'required': True
        })
    )
    
    publish_immediately = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label='Publish immediately'
    )
    
    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['wordpress_site'].queryset = WordPressSite.objects.filter(
            user=user,
            is_active=True
        )


class CustomLoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'})
    )

class WordPressSiteForm(forms.ModelForm):
    class Meta:
        model = WordPressSite
        fields = ['name', 'url', 'username', 'app_password']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://example.com'}),
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'app_password': forms.PasswordInput(attrs={'class': 'form-control'}),
        }

class ContentGenerationForm(forms.Form):
    topic = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., Best Coffee Makers 2024',
            'required': True
        })
    )
    prompt = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Optional: Additional instructions or context for the AI...'
        })
    )
    affiliate_links = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Enter affiliate links (one per line)...'
        })
    )
    images = forms.FileField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*'
        })
    )
    wordpress_site = forms.ModelChoiceField(
        queryset=WordPressSite.objects.none(),
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label="Select a WordPress site"
    )
    
    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['wordpress_site'].queryset = WordPressSite.objects.filter(
            user=user, is_active=True
        )