from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor
from django_apscheduler.jobstores import register_events, DjangoJobStore
from app.scheduled_job import *
from bot.scheduled_job import mailing
from bot.services.redis_service import save_langs_to_redis
from asgiref.sync import async_to_sync

executors = {
    'default': ThreadPoolExecutor(20),
    'processpool': ProcessPoolExecutor(5),
}

job_defaults = {
    'coalesce': False,
    'max_instances': 1,
    'misfire_grace_time': 300,
}


class jobs:
    scheduler = BlockingScheduler(timezone='Asia/Tashkent', executors=executors, job_defaults=job_defaults)
    scheduler.add_jobstore(DjangoJobStore(), 'djangojobstore')
    register_events(scheduler)
    # scheduler.add_job(, 'interval', minutes=5)
    scheduler.add_job(
        async_to_sync(mailing.send_message), 
        'interval', minutes=5)
    scheduler.add_job(save_langs_to_redis, 'interval', minutes=20)
