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
    
    def calculate_retention(self, time):
        """
        Implements Ebbinghaus' Forgetting Curve: R(t) = e^(-t/β)
        """
        beta = self.get_decay_constant()
        return math.exp(-time / beta)

    def get_decay_constant(self):
        """
        Calculate β (beta) based on user performance
        """
        reviews = self.review_set.all()
        if not reviews.exists():
            return 1.0
        
        success_rate = self.calculate_success_rate()
        return 1.0 * (success_rate / 100)  # Adjust beta based on performance

    def calculate_success_rate(self):
        """
        Calculate overall success rate S
        """
        reviews = self.review_set.all()
        if not reviews.exists():
            return 100  # Initial optimistic rate
        
        successful_reviews = reviews.filter(performance_rating__gte=4).count()
        return (successful_reviews / reviews.count()) * 100

    def get_initial_interval(self):
        """
        Initial interval assignment based on type and difficulty
        """
        intervals = {
            'Q': {  # Questions
                'E': 1.0,    # 1 day
                'M': 0.8,    # 0.8 days
                'H': 0.6     # 0.6 days
            },
            'C': {  # Concepts
                'E': 1.2,    # 1.2 days
                'M': 1.0,    # 1 day
                'H': 0.8     # 0.8 days
            }
        }
        return intervals[self.item_type][self.difficulty]

    def get_performance_multiplier(self, is_correct):
        """
        Get interval multiplier M based on performance and difficulty
        """
        if not is_correct:
            return 1.0  # Reset or minimal growth for incorrect responses
        
        multipliers = {
            'E': 2.0,  # Easy items
            'M': 1.8,  # Medium items
            'H': 1.6   # Hard items
        }
        return multipliers[self.difficulty]

    def calculate_next_review(self):
        current_time = timezone.now()
        last_review = self.review_set.order_by('-review_date').first()
        
        # For new items
        if not last_review:
            if self.created_at.date() == current_time.date():
                initial_interval = self.get_initial_interval()
                return self.created_at + timezone.timedelta(days=initial_interval)
            return current_time

        # Get review history
        reviews = self.review_set.all()
        review_count = reviews.count()
        
        # Calculate previous interval
        if review_count > 1:
            prev_review = reviews.order_by('-review_date')[1]
            I_prev = (last_review.review_date - prev_review.review_date).days
        else:
            I_prev = self.get_initial_interval()

        # Get performance from last review
        is_correct = last_review.performance_rating >= 4
        
        # Calculate base multiplier
        M = self.get_performance_multiplier(is_correct)
        
        # Adjust multiplier based on aggregate performance
        success_rate = self.calculate_success_rate()
        k = 0.5  # Sensitivity constant
        M_aggregate = 1 + k * (success_rate / 100)
        M = M * M_aggregate

        # Calculate next interval using the forgetting curve
        R_threshold = 0.8  # Desired retention threshold (80%)
        beta = self.get_decay_constant()
        
        # Calculate interval using the inverse of the forgetting curve
        # t = -β * ln(R_threshold)
        base_interval = I_prev * M
        retention_interval = -beta * math.log(R_threshold)
        
        # Take the minimum to ensure retention stays above threshold
        I_next = min(base_interval, retention_interval)
        
        # Apply exponential growth cap
        max_interval = 60  # Maximum interval of 60 days
        I_next = min(I_next, max_interval)
        
        # Calculate next review date
        t_next = last_review.review_date + timezone.timedelta(days=I_next)
        
        return t_next

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

    def update_review_metrics(self, performance_rating):
        """
        Update review metrics after a review is completed
        """
        self.review_count += 1
        self.last_review = timezone.now()
        
        # Update success rate based on performance
        is_successful = performance_rating >= 4
        success_rate = self.calculate_success_rate()
        
        # Recalculate next review date based on performance
        next_review = self.calculate_next_review()
        
        self.save()
        return next_review

class Review(models.Model):
    learning_item = models.ForeignKey(LearningItem, on_delete=models.CASCADE)
    review_date = models.DateTimeField(auto_now_add=True)
    performance_rating = models.IntegerField(
        choices=[(i, str(i)) for i in range(1, 6)]
    )
    notes = models.TextField(blank=True)
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        if is_new:
            # Update learning item metrics when a new review is added
            self.learning_item.update_review_metrics(self.performance_rating)