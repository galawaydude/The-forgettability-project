from django.db import models
from django.contrib.auth.models import User
from datetime import datetime, timedelta
import math

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
        base_strength = 24  # base strength in hours
        difficulty_mod = self.get_difficulty_modifier()
        review_mod = 1 + math.log(self.review_count + 1)
        
        strength = base_strength * difficulty_mod * review_mod
        target_retention = 0.7  # 70% retention target
        
        hours_until_review = -math.log(target_retention) * strength
        return self.last_review + timedelta(hours=hours_until_review)

class Review(models.Model):
    learning_item = models.ForeignKey(LearningItem, on_delete=models.CASCADE)
    review_date = models.DateTimeField(auto_now_add=True)
    performance_rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    notes = models.TextField(blank=True)