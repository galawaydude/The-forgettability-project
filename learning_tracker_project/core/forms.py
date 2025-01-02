from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import LearningItem, Review

class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

class LearningItemForm(forms.ModelForm):
    class Meta:
        model = LearningItem
        fields = ['title', 'item_type', 'difficulty', 'description', 
                 'references', 'question_link', 'question_image']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make some fields optional
        self.fields['question_link'].required = False
        self.fields['question_image'].required = False
        self.fields['references'].required = False

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['performance_rating', 'notes']

class ItemSearchForm(forms.Form):
    SORT_CHOICES = [
        ('title', 'Title (A-Z)'),
        ('-title', 'Title (Z-A)'),
        ('created_at', 'Oldest First'),
        ('-created_at', 'Newest First'),
        ('difficulty', 'Difficulty (Easy-Hard)'),
        ('-difficulty', 'Difficulty (Hard-Easy)'),
    ]

    query = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search items...'
        })
    )
    
    item_type = forms.ChoiceField(
        choices=[('', 'All Types'), ('Q', 'Questions'), ('C', 'Concepts')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    difficulty = forms.MultipleChoiceField(
        choices=[('E', 'Easy'), ('M', 'Medium'), ('H', 'Hard')],
        required=False,
        widget=forms.CheckboxSelectMultiple
    )
    
    needs_review = forms.BooleanField(
        required=False,
        initial=False,
        label='Needs Review'
    )
    
    sort_by = forms.ChoiceField(
        choices=SORT_CHOICES,
        required=False,
        initial='-created_at',
        widget=forms.Select(attrs={'class': 'form-control'})
    )