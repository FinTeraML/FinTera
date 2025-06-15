from django import forms
from .models import UserStrategy

class UserStrategyForm(forms.ModelForm):
    class Meta:
        model = UserStrategy
        exclude = ('user',)
        widgets = {
            'name': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'description': forms.Textarea(attrs={'class': 'textarea textarea-bordered w-full', 'rows': 3}),
            'pandasta_strategy_name': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'parameters': forms.Textarea(attrs={'class': 'textarea textarea-bordered w-full', 'rows': 3, 'placeholder': 'Enter parameters as JSON, e.g., {"length": 20}'}),
        }
        help_texts = {
            'pandasta_strategy_name': "Name of the pandasta indicator/strategy, e.g., 'sma', 'rsi', 'macd'.",
            'parameters': 'Parameters for the strategy as a JSON object, e.g., {"length": 20}. Ensure keys are double-quoted.',
        }
