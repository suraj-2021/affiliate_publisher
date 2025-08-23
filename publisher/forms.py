from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import WordPressSite, PublishedPost

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
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control',
            'multiple': True,
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