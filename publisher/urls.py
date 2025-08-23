from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from publisher import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.dashboard, name='dashboard'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('generate/', views.generate_content, name='generate_content'),
    path('sites/', views.manage_sites, name='manage_sites'),
    path('sites/<int:pk>/delete/', views.delete_site, name='delete_site'),
    path('sites/<int:pk>/test/', views.test_site_connection, name='test_site'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)