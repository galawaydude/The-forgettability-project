from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from django.utils import timezone
from .models import LearningItem, Review
from .forms import UserRegistrationForm, LearningItemForm, ReviewForm
from datetime import datetime
from django.db.models import Q
from .forms import ItemSearchForm
from django.db.models import Avg

@login_required
def dashboard(request):
    # Get items that need review
    current_time = datetime.now()
    items = LearningItem.objects.filter(user=request.user)
    items_to_review = [
        item for item in items 
        if item.calculate_next_review() <= current_time
    ]
    
    context = {
        'items_to_review': items_to_review,
        'recent_items': items.order_by('-created_at')[:5],
        'total_items': items.count(),
        'review_count': Review.objects.filter(
            learning_item__user=request.user
        ).count(),
    }
    return render(request, 'core/dashboard.html', context)

@login_required
def add_item(request):
    if request.method == 'POST':
        form = LearningItemForm(request.POST, request.FILES)
        if form.is_valid():
            item = form.save(commit=False)
            item.user = request.user
            item.save()
            messages.success(request, 'Item added successfully!')
            return redirect('core:dashboard')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = LearningItemForm()
    return render(request, 'core/add_item.html', {'form': form})

@login_required
def item_detail(request, pk):
    item = get_object_or_404(LearningItem, pk=pk, user=request.user)
    reviews = item.review_set.all().order_by('-review_date')[:5]
    next_review = item.calculate_next_review()
    
    context = {
        'item': item,
        'reviews': reviews,
        'next_review': next_review,
        'review_count': item.review_set.count(),
    }
    return render(request, 'core/item_detail.html', context)

@login_required
def review_item(request, pk):
    item = get_object_or_404(LearningItem, pk=pk, user=request.user)
    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.learning_item = item
            review.save()
            
            # Update item's review count and last review date
            item.review_count += 1
            item.last_review = datetime.now()
            item.save()
            
            messages.success(request, 'Review completed successfully!')
            return redirect('core:dashboard')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ReviewForm()
    
    context = {
        'item': item,
        'form': form,
        'review_count': item.review_set.count(),
        'last_review': item.last_review,
    }
    return render(request, 'core/review_item.html', context)

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
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Registration successful! Welcome aboard!')
            return redirect('core:dashboard')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = UserRegistrationForm()
    return render(request, 'core/register.html', {'form': form})

@login_required
def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('core:login')

@login_required
def search_items(request):
    form = ItemSearchForm(request.GET)
    items = LearningItem.objects.filter(user=request.user)
    
    if form.is_valid():
        # Text search
        query = form.cleaned_data.get('query')
        if query:
            items = items.filter(
                Q(title__icontains=query) | 
                Q(description__icontains=query)
            )
        
        # Type filter
        item_type = form.cleaned_data.get('item_type')
        if item_type:
            items = items.filter(item_type=item_type)
        
        # Difficulty filter
        difficulties = form.cleaned_data.get('difficulty')
        if difficulties:
            items = items.filter(difficulty__in=difficulties)
        
        # Needs review filter
        if form.cleaned_data.get('needs_review'):
            current_time = timezone.now()
            items = [item for item in items if item.calculate_next_review() <= current_time]
        
        # Sorting
        sort_by = form.cleaned_data.get('sort_by')
        if sort_by:
            items = items.order_by(sort_by)
    
    return render(request, 'core/search.html', {
        'form': form,
        'items': items,
        'total_results': len(items) if isinstance(items, list) else items.count()
    })

@login_required
def stats_view(request):
    items = LearningItem.objects.filter(user=request.user)
    reviews = Review.objects.filter(learning_item__user=request.user)
    
    # Calculate statistics
    stats = {
        'total_items': items.count(),
        'total_reviews': reviews.count(),
        'items_by_type': {
            'Questions': items.filter(item_type='Q').count(),
            'Concepts': items.filter(item_type='C').count()
        },
        'items_by_difficulty': {
            'Easy': items.filter(difficulty='E').count(),
            'Medium': items.filter(difficulty='M').count(),
            'Hard': items.filter(difficulty='H').count()
        },
        'recent_reviews': reviews.order_by('-review_date')[:10],
        'avg_rating': reviews.aggregate(Avg('performance_rating'))['performance_rating__avg']
    }
    
    return render(request, 'core/stats.html', {'stats': stats})

@login_required
def delete_item(request, pk):
    item = get_object_or_404(LearningItem, pk=pk, user=request.user)
    if request.method == 'POST':
        item.delete()
        messages.success(request, 'Item deleted successfully.')
        return redirect('core:dashboard')
    return render(request, 'core/delete_confirm.html', {'item': item})

@login_required
def edit_item(request, pk):
    item = get_object_or_404(LearningItem, pk=pk, user=request.user)
    if request.method == 'POST':
        form = LearningItemForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, 'Item updated successfully!')
            return redirect('core:item_detail', pk=pk)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = LearningItemForm(instance=item)
    return render(request, 'core/edit_item.html', {'form': form, 'item': item})

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
        'avg_rating': reviews.aggregate(Avg('rating'))['rating__avg'],
        'join_date': request.user.date_joined,
        'last_login': request.user.last_login,
    }
    
    return render(request, 'core/profile.html', context)