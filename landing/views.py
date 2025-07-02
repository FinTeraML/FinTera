from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from automl.models import MLModel, PredictionRecord
from django.utils import timezone

# Create your views here.

def index(request):
    """Landing page view"""
    return render(request, 'landing/index.html')

@login_required
def dashboard(request):
    """Dashboard view with analytics"""
    # Gerçek veriler
    toplam_tahmin = PredictionRecord.objects.count()
    toplam_model = MLModel.objects.count()
    aktif_model = MLModel.objects.filter(is_active=True).count()
    
    # Son tahminler
    son_tahminler = PredictionRecord.objects.order_by('-created_at')[:5]
    
    # En iyi model accuracy'si
    best_accuracy = 0
    best_model_name = "Henüz test edilmedi"
    
    if toplam_tahmin > 0:
        # Son 10 tahminden en iyi accuracy'yi bul
        recent_predictions = PredictionRecord.objects.order_by('-created_at')[:10]
        for pred in recent_predictions:
            # R² score hesaplama (accuracy proxy)
            if pred.rmse > 0:
                # Basit bir accuracy hesaplama (RMSE'ye dayalı)
                accuracy = max(0, 100 - (pred.rmse / 100))  # RMSE'yi normalize et
                if accuracy > best_accuracy:
                    best_accuracy = accuracy
                    best_model_name = pred.model
    
    context = {
        "toplam_tahmin": toplam_tahmin,
        "toplam_model": toplam_model,
        "aktif_model": aktif_model,
        "son_tahminler": son_tahminler,
        "best_accuracy": f"{best_accuracy:.2f}%",
        "best_model_name": best_model_name,
    }
    return render(request, "landing/dashboard.html", context)
