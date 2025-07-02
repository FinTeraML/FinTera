from django.db import models

# Create your models here.

class MLModel(models.Model):
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    # user = models.ForeignKey('auth.User', on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return self.name

class PredictionRecord(models.Model):
    ticker = models.CharField(max_length=10)
    model = models.CharField(max_length=50)
    rmse = models.FloatField()
    mae = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)
    ml_model = models.ForeignKey(MLModel, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"{self.ticker} - {self.model} ({self.created_at.date()})"
