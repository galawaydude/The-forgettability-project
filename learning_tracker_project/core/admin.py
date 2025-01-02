from django.contrib import admin
from .models import LearningItem, Review

@admin.register(LearningItem)
class LearningItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'item_type', 'difficulty', 'review_count', 'last_review')
    list_filter = ('item_type', 'difficulty', 'user')
    search_fields = ('title', 'description')

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('learning_item', 'review_date', 'performance_rating')
    list_filter = ('performance_rating', 'review_date')