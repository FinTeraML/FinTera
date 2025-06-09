from django.shortcuts import render

# Create your views here.

def index(request):
    """Landing page view"""
    return render(request, 'landing/index.html')
