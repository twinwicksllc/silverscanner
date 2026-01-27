"""
Scheduler Module
Handles scheduled tasks like digest emails
"""

import logging
from datetime import datetime, time
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
from modules.notifications import EmailNotifier
from database.models import DatabaseManager

logger = logging.getLogger(__name__)

class DigestScheduler:
    """Manages scheduled digest email sending"""
    
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.email_notifier = EmailNotifier(self.db_manager)
        self.scheduler = BackgroundScheduler()
        self.cst_tz = pytz.timezone('America/Chicago')
    
    def start(self):
        """Start the scheduler with digest jobs"""
        if not self.email_notifier.enabled:
            logger.info("Email notifications disabled, digest scheduler not started")
            return
        
        # Schedule digest at 12:00 PM CST
        self.scheduler.add_job(
            self.send_digest,
            CronTrigger(hour=12, minute=0, timezone=self.cst_tz),
            id='digest_noon',
            name='Silver Digest - Noon',
            replace_existing=True
        )
        
        # Schedule digest at 8:00 PM CST
        self.scheduler.add_job(
            self.send_digest,
            CronTrigger(hour=20, minute=0, timezone=self.cst_tz),
            id='digest_evening',
            name='Silver Digest - Evening',
            replace_existing=True
        )
        
        self.scheduler.start()
        logger.info("Digest scheduler started - emails will be sent at 12:00 PM and 8:00 PM CST")
    
    def stop(self):
        """Stop the scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Digest scheduler stopped")
    
    def send_digest(self):
        """Send digest email with pending deals"""
        try:
            logger.info("Running scheduled digest job")
            
            # Get pending deals
            pending_deals = self.email_notifier.get_pending_digest_deals()
            
            if not pending_deals:
                logger.info("No pending deals for digest")
                return
            
            # Send digest
            success = self.email_notifier.send_digest_email(pending_deals)
            
            if success:
                logger.info(f"Digest sent successfully with {len(pending_deals)} deals")
            else:
                logger.error("Failed to send digest email")
                
        except Exception as e:
            logger.error(f"Error in digest job: {e}")
    
    def send_test_digest(self):
        """Send a test digest immediately (for testing)"""
        logger.info("Sending test digest")
        self.send_digest()