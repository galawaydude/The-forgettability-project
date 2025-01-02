from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.urls import reverse
from .models import LearningItem

def send_review_reminder(user, items_to_review, site_domain):
    """
    Send an email reminder for items that need review.
    
    Args:
        user: The user to send the reminder to
        items_to_review: List of items due for review
        site_domain: The domain of the website
    """
    subject = 'Learning Items Due for Review'
    
    context = {
        'user': user,
        'items_to_review': items_to_review,
        'total_items': len(items_to_review),
        'site_domain': site_domain
    }
    
    # Render email templates
    html_message = render_to_string('core/email/review_reminder.html', context)
    plain_message = render_to_string('core/email/review_reminder.txt', context)
    
    # Send email
    send_mail(
        subject=subject,
        message=plain_message,
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[user.email],
        html_message=html_message,
        fail_silently=False,
    )

def get_items_for_review():
    """
    Get all items that need review, grouped by user.
    
    Returns:
        dict: Dictionary with users as keys and their due items as values
    """
    current_time = timezone.now()
    user_items = {}
    
    # Get all items and group them by user
    for item in LearningItem.objects.select_related('user').all():
        if item.calculate_next_review() <= current_time:
            if item.user not in user_items:
                user_items[item.user] = []
            user_items[item.user].append(item)
    
    return user_items