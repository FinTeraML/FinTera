from django.db import models
from django.contrib.auth import get_user_model

class StockData(models.Model):
    symbol = models.CharField(max_length=10)
    date = models.DateField()
    open_price = models.DecimalField(max_digits=10, decimal_places=2)
    high_price = models.DecimalField(max_digits=10, decimal_places=2)
    low_price = models.DecimalField(max_digits=10, decimal_places=2)
    close_price = models.DecimalField(max_digits=10, decimal_places=2)
    volume = models.BigIntegerField()

    class Meta:
        unique_together = ('symbol', 'date')

    def __str__(self):
        return f"{self.symbol} on {self.date}"

class UserStrategy(models.Model):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    pandasta_strategy_name = models.CharField(
        max_length=50,
        help_text="Name of the pandasta indicator/strategy, e.g., 'sma', 'rsi', 'macd'"
    )
    parameters = models.JSONField(
        help_text="Parameters for the strategy, e.g., {'length': 20}"
    )

    def __str__(self):
        return f"{self.name} ({self.user.username})"
