from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

app_name = 'publisher'

urlpatterns = [
    # Authentication
    path('', views.dashboard, name='dashboard'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Content Management
    path('generate/', views.generate_content, name='generate_content'),
    path('edit/<int:pk>/', views.edit_content, name='edit_content'),
    path('preview/<int:pk>/', views.preview_content, name='preview_content'),
    path('delete/<int:pk>/', views.delete_post, name='delete_post'),
    path('stage-overview/', views.stage_overview, name='stage_overview'),
    path('stage/<str:stage_id>/', views.stage_details, name='stage_details'),
    path('ajax/stage-suggestions/', views.ajax_stage_suggestions, name='ajax_stage_suggestions'),
    path('ajax/update-strategy/', views.ajax_update_strategy, name='ajax_update_strategy'),
    path('stage-overview/', views.stage_overview, name='stage_overview'),
  


  
    # WordPress Sites
    path('sites/', views.manage_sites, name='manage_sites'),
    path('sites/add/', views.add_site, name='add_site'),
    path('sites/<int:pk>/edit/', views.edit_site, name='edit_site'),
    path('sites/<int:pk>/delete/', views.delete_site, name='delete_site'),
    path('sites/<int:pk>/test/', views.test_site_connection, name='test_site'),
    
    # Internal Linking (NEW)
    path('internal-links/', views.manage_internal_links, name='manage_internal_links'),
    path('internal-links/rules/', views.linking_rules, name='linking_rules'),
    path('internal-links/rule/add/', views.add_linking_rule, name='add_linking_rule'),
    path('internal-links/rule/<int:pk>/edit/', views.edit_linking_rule, name='edit_linking_rule'),
    path('internal-links/rule/<int:pk>/delete/', views.delete_linking_rule, name='delete_linking_rule'),
    path('internal-links/rule/<int:pk>/toggle/', views.toggle_linking_rule, name='toggle_linking_rule'),
    
    # AJAX Endpoints
    path('ajax/insert-link/', views.insert_affiliate_link, name='insert_affiliate_link'),
    path('ajax/related-posts/', views.ajax_get_related_posts, name='ajax_related_posts'),
    path('ajax/save-draft/', views.ajax_save_draft, name='ajax_save_draft'),
    path('ajax/link-suggestions/', views.ajax_link_suggestions, name='ajax_link_suggestions'),
    path('ajax/create-rule/', views.ajax_create_rule, name='ajax_create_rule'),
    
    # Bulk Operations
    path('bulk/generate/', views.bulk_generate, name='bulk_generate'),
    path('bulk/publish/', views.bulk_publish, name='bulk_publish'),
    
    # Settings
    path('settings/', views.user_settings, name='user_settings'),
    path('settings/export/', views.export_settings, name='export_settings'),


]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)