from django.core.management.base import BaseCommand
import logging
import signal
import sys

from app.scheduled_job.updater import jobs

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Run scheduled jobs'

    def handle(self, *args, **kwargs):
        # Start the scheduler (BlockingScheduler) — this call will block and
        # the scheduler installs signal handlers for graceful shutdown.
        try:
            logger.info('Starting scheduled jobs')
            jobs.scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            # If a shutdown signal arrives, ensure scheduler is shut down.
            try:
                jobs.scheduler.shutdown(wait=True)
            except Exception:
                logger.exception('Error while shutting down scheduler')
            logger.info('Scheduler stopped')
            # Exit with success status so supervisor won't consider this a crash
            sys.exit(0)