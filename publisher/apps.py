from django.apps import AppConfig

class PublisherConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'publisher'
    
    def ready(self):
        # Import signal handlers if you have any
        pass