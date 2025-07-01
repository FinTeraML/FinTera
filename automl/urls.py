from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='automl_index'),
    path('forecast/', views.get_stock_forecast, name='stock_forecast'),
    path('models/', views.models_list, name='models_list'),
    path('models/<int:model_id>/toggle/', views.toggle_model_status, name='toggle_model_status'),
    path('models/<int:model_id>/delete/', views.delete_model, name='delete_model'),
]
