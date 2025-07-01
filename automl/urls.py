# automl/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('stock-data/', views.get_stock_data, name='get_stock_data'),
]
