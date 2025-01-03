from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from .models import LearningItem, Review
from .forms import LearningItemForm, ReviewForm
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            next_url = request.GET.get('next', 'core:dashboard')
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid username or password.')
    return render(request, 'core/login.html')

def register_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Registration successful!')
            return redirect('core:dashboard')
        else:
            messages.error(request, 'Registration failed. Please correct the errors.')
    else:
        form = UserCreationForm()
    return render(request, 'core/register.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('core:login')

@login_required
def dashboard(request):
    # Get all items for the current user
    items = LearningItem.objects.filter(user=request.user)
    current_time = timezone.now()
    
    # Initialize lists for different categories
    overdue_items = []
    due_today_items = []
    upcoming_items = []
    
    # Categorize items
    for item in items:
        next_review = item.calculate_next_review()
        
        # Ensure next_review is timezone aware
        if not next_review.tzinfo:
            next_review = timezone.make_aware(next_review)
            
        if next_review < current_time:
            overdue_items.append(item)
        elif next_review.date() == current_time.date():
            due_today_items.append(item)
        else:
            upcoming_items.append(item)
    
    context = {
        'overdue_items': overdue_items,
        'due_today_items': due_today_items,
        'upcoming_items': upcoming_items,
        'total_items': items.count(),
        'total_reviews': Review.objects.filter(learning_item__user=request.user).count(),
    }
    
    return render(request, 'core/dashboard.html', context)

@login_required
def add_item(request):
    if request.method == 'POST':
        form = LearningItemForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.user = request.user
            item.created_at = timezone.now()  # Add this line to set timezone-aware created_at
            item.save()
            messages.success(request, 'Item added successfully!')
            return redirect('core:dashboard')
    else:
        form = LearningItemForm()
    return render(request, 'core/add_item.html', {'form': form})

@login_required
def item_detail(request, pk):
    item = get_object_or_404(LearningItem, pk=pk, user=request.user)
    reviews = item.review_set.all().order_by('-review_date')
    next_review = item.calculate_next_review()
    
    # Ensure next_review is timezone aware
    if next_review and not next_review.tzinfo:
        next_review = timezone.make_aware(next_review)
    
    context = {
        'item': item,
        'reviews': reviews,
        'next_review': next_review
    }
    return render(request, 'core/item_detail.html', context)

@login_required
def edit_item(request, pk):
    item = get_object_or_404(LearningItem, pk=pk, user=request.user)
    if request.method == 'POST':
        form = LearningItemForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, 'Item updated successfully!')
            return redirect('core:item_detail', pk=pk)
    else:
        form = LearningItemForm(instance=item)
    return render(request, 'core/edit_item.html', {'form': form, 'item': item})

@login_required
def delete_item(request, pk):
    item = get_object_or_404(LearningItem, pk=pk, user=request.user)
    if request.method == 'POST':
        item.delete()
        messages.success(request, 'Item deleted successfully!')
        return redirect('core:dashboard')
    return render(request, 'core/delete_confirm.html', {'item': item})

@login_required
def review_item(request, pk):
    item = get_object_or_404(LearningItem, pk=pk, user=request.user)
    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.learning_item = item
            review.review_date = timezone.now()  # Add this line to set timezone-aware review_date
            review.save()
            messages.success(request, 'Review submitted successfully!')
            return redirect('core:dashboard')
    else:
        form = ReviewForm()
    return render(request, 'core/review_item.html', {'form': form, 'item': item})

@login_required
def search_items(request):
    query = request.GET.get('q', '')
    # Show all items by default
    items = LearningItem.objects.filter(user=request.user).order_by('-created_at')
    
    # Filter items if there's a search query
    if query:
        items = items.filter(
            Q(title__icontains=query) | 
            Q(description__icontains=query)
        )
    
    return render(request, 'core/search_results.html', {
        'items': items,
        'query': query,
        'total_items': items.count()
    })

@login_required
def stats_view(request):
    items = LearningItem.objects.filter(user=request.user)
    reviews = Review.objects.filter(learning_item__user=request.user)
    total_items = items.count()

    # Calculate statistics
    stats = {
        'total_items': total_items,
        'total_reviews': reviews.count(),
        
        # Items by type with percentages
        'items_by_type': {
            'Questions': {
                'count': items.filter(item_type='Q').count(),
                'percentage': (items.filter(item_type='Q').count() / total_items * 100) if total_items > 0 else 0
            },
            'Concepts': {
                'count': items.filter(item_type='C').count(),
                'percentage': (items.filter(item_type='C').count() / total_items * 100) if total_items > 0 else 0
            }
        },
        
        # Items by difficulty with percentages
        'items_by_difficulty': {
            'Easy': {
                'count': items.filter(difficulty='E').count(),
                'percentage': (items.filter(difficulty='E').count() / total_items * 100) if total_items > 0 else 0
            },
            'Medium': {
                'count': items.filter(difficulty='M').count(),
                'percentage': (items.filter(difficulty='M').count() / total_items * 100) if total_items > 0 else 0
            },
            'Hard': {
                'count': items.filter(difficulty='H').count(),
                'percentage': (items.filter(difficulty='H').count() / total_items * 100) if total_items > 0 else 0
            }
        },
        
        # Recent reviews
        'recent_reviews': reviews.select_related('learning_item').order_by('-review_date')[:5]
    }
    
    return render(request, 'core/stats.html', {'stats': stats})

@login_required
def profile(request):
    if request.method == 'POST':
        # Handle profile update
        user = request.user
        user.first_name = request.POST.get('first_name', '')
        user.last_name = request.POST.get('last_name', '')
        user.email = request.POST.get('email', '')
        
        # Update password if provided
        new_password = request.POST.get('new_password')
        if new_password:
            if user.check_password(request.POST.get('current_password', '')):
                user.set_password(new_password)
                messages.success(request, 'Password updated successfully!')
            else:
                messages.error(request, 'Current password is incorrect.')
                return redirect('core:profile')
        
        user.save()
        messages.success(request, 'Profile updated successfully!')
        return redirect('core:profile')
    
    # Get user statistics
    items = LearningItem.objects.filter(user=request.user)
    reviews = Review.objects.filter(learning_item__user=request.user)
    
    context = {
        'total_items': items.count(),
        'total_reviews': reviews.count(),
        'join_date': request.user.date_joined,
        'last_login': request.user.last_login,
    }
    
    return render(request, 'core/profile.html', context)