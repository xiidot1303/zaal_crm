from django.apps import AppConfig


class app(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app'
    
    def ready(self):
        # Import signal handlers to ensure they're connected
        import app.signals