from django.apps import AppConfig


class bot(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'bot'

    def ready(self):
        import bot.signals
        # save bot user lang codes to redis
        from bot.services.redis_service import save_langs_to_redis
        try:
            save_langs_to_redis()
        except:
            None