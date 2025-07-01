from django.shortcuts import render
from django.contrib.auth.decorators import login_required

# Create your views here.

def index(request):
    """Landing page view"""
    return render(request, 'landing/index.html')

@login_required
def dashboard(request):
    """Dashboard view with analytics"""
    # Mock data for demonstration - will be replaced with real data when apps are implemented
    context = {
        'total_models': 12,
        'active_models': 8,
        'total_datasets': 25,
        'recent_datasets': 5,
        'total_backtests': 34,
        'successful_backtests': 28,
        'avg_return': 15.7,
        'best_model_accuracy': 94.2,
        'models_created_this_month': 3,
        'datasets_uploaded_this_week': 2,
        'active_backtests': 4,
    }
    return render(request, 'landing/dashboard.html', context)
