from django.db import models
from django.contrib.auth.models import User
from datetime import datetime, timedelta
import math
from django.utils import timezone

class LearningItem(models.Model):
    ITEM_TYPES = (
        ('Q', 'Question'),
        ('C', 'Concept'),
    )
    
    DIFFICULTY_LEVELS = (
        ('E', 'Easy'),
        ('M', 'Medium'),
        ('H', 'Hard'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    item_type = models.CharField(max_length=1, choices=ITEM_TYPES)
    difficulty = models.CharField(max_length=1, choices=DIFFICULTY_LEVELS)
    description = models.TextField()
    references = models.TextField(blank=True)
    
    # For Questions
    question_link = models.URLField(blank=True)
    question_image = models.ImageField(upload_to='questions/', blank=True)
    
    # Learning Progress
    created_at = models.DateTimeField(auto_now_add=True)
    last_review = models.DateTimeField(auto_now_add=True)
    review_count = models.IntegerField(default=0)
    
    def get_difficulty_modifier(self):
        return {
            'E': 1.2,
            'M': 1.0,
            'H': 0.8
        }[self.difficulty]
    
    def calculate_next_review(self):
        last_review = self.review_set.order_by('-review_date').first()
        
        if not last_review:
            # If never reviewed, set next review to today
            return timezone.now()
        
        last_review_date = last_review.review_date
        if not last_review_date.tzinfo:
            last_review_date = timezone.make_aware(last_review_date)
            
        # Calculate next review based on spaced repetition
        days_to_add = 1  # Default to 1 day
        review_count = self.review_set.count()
        
        if review_count == 1:
            days_to_add = 3
        elif review_count == 2:
            days_to_add = 7
        elif review_count == 3:
            days_to_add = 14
        elif review_count == 4:
            days_to_add = 30
        else:
            days_to_add = 60
            
        return last_review_date + timezone.timedelta(days=days_to_add)

    def get_review_status(self):
        next_review = self.calculate_next_review()
        current_time = timezone.now()
        
        if not next_review:
            return {
                'status': 'new',
                'message': 'Not reviewed yet'
            }
        elif current_time < next_review:
            return {
                'status': 'upcoming',
                'message': f'Due on {next_review.strftime("%b %d, %Y")}'
            }
        else:
            days_overdue = (current_time - next_review).days
            return {
                'status': 'overdue',
                'message': f'Overdue by {days_overdue} days'
            }

class Review(models.Model):
    learning_item = models.ForeignKey(LearningItem, on_delete=models.CASCADE)
    review_date = models.DateTimeField(auto_now_add=True)
    performance_rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    notes = models.TextField(blank=True)