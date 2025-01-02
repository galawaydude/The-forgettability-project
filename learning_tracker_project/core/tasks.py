from celery import shared_task
from django.contrib.sites.models import Site
from .notifications import get_items_for_review, send_review_reminder

@shared_task
def send_review_reminders():
    """
    Celery task to send review reminders to all users with due items.
    This task will be scheduled to run periodically.
    """
    # Get the site domain for email links
    site_domain = Site.objects.get_current().domain
    
    # Get items grouped by user
    user_items = get_items_for_review()
    
    # Send reminders to each user
    for user, items in user_items.items():
        if user.email:  # Only send if user has email
            try:
                send_review_reminder(user, items, site_domain)
            except Exception as e:
                # Log the error but continue with other users
                print(f"Failed to send reminder to {user.email}: {str(e)}")
    
    return f"Sent reminders to {len(user_items)} users"