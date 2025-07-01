import matplotlib
matplotlib.use('Agg')
import yfinance as yf
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from xgboost import XGBRegressor
from lightgbm import LGBMRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import matplotlib.pyplot as plt
import io, base64
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from .models import PredictionRecord, MLModel
from django.db.models import Avg
import torch
import torch.nn as nn
from sklearn.preprocessing import MinMaxScaler

def calculate_rsi(prices, period=14):
    """RSI hesaplama"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_macd(prices, fast=12, slow=26, signal=9):
    """MACD hesaplama"""
    ema_fast = prices.ewm(span=fast).mean()
    ema_slow = prices.ewm(span=slow).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal).mean()
    return macd_line, signal_line

def calculate_bollinger_bands(prices, period=20, std_dev=2):
    """Bollinger Bands hesaplama"""
    sma = prices.rolling(window=period).mean()
    std = prices.rolling(window=period).std()
    upper_band = sma + (std * std_dev)
    lower_band = sma - (std * std_dev)
    return upper_band, lower_band

class LSTMModel(nn.Module):
    def __init__(self, input_size, hidden_size=50, num_layers=1):
        super(LSTMModel, self).__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
        self.fc = nn.Linear(hidden_size, 1)
    def forward(self, x):
        out, _ = self.lstm(x)
        out = self.fc(out[:, -1, :])
        return out

def get_stock_forecast(request):
    if request.method == "POST":
        prediction_type = request.POST.get("prediction_type", "single")
        investment = float(request.POST.get("investment", 1000))
        forecast_days = int(request.POST.get("forecast_days", 7))
        model_name = request.POST.get("model")
        gosterge = request.POST.getlist("gosterge")
        
        if prediction_type == "portfolio":
            import json
            portfolio_json = request.POST.get("portfolio_json", "[]")
            try:
                portfolio = json.loads(portfolio_json)
                if not portfolio or sum([float(x['weight']) for x in portfolio]) != 100:
                    return render(request, "automl/forecast_result.html", {"error": "Ağırlıkların toplamı 100 olmalı ve en az bir hisse olmalı!"})
            except Exception:
                return render(request, "automl/forecast_result.html", {"error": "Portföy formatı hatalı!"})
        else:
            ticker = request.POST.get("ticker")
            portfolio = [{"ticker": ticker, "weight": 100.0}]
        
        portfoy_sonuclari = []
        toplam_beklenen_kar = 0
        toplam_beklenen_getiri = 0
        toplam_rmse = 0
        toplam_mae = 0
        toplam_accuracy = 0
        basarili_hisse_var = False
        
        for p in portfolio:
            tkr = p['ticker']
            weight = float(p['weight'])
            
            try:
                veri = yf.download(tkr, period="1y")
            except Exception as e:
                portfoy_sonuclari.append({
                    "ticker": tkr,
                    "weight": weight,
                    "rmse": "-",
                    "mae": "-",
                    "accuracy": "-",
                    "predicted_return": "-",
                    "expected_profit": "-",
                    "error": f"{tkr} için veri çekilemedi: {str(e)}"
                })
                continue
                
            # Veri kontrolü
            if veri is None or veri.empty or 'Close' not in veri.columns:
                portfoy_sonuclari.append({
                    "ticker": tkr,
                    "weight": weight,
                    "rmse": "-",
                    "mae": "-",
                    "accuracy": "-",
                    "predicted_return": "-",
                    "expected_profit": "-",
                    "error": f"{tkr} için veri bulunamadı veya geçersiz."
                })
                continue
                
            # Close fiyatlarını kontrol et
            close_prices = veri['Close'].dropna()
            if len(close_prices) < 30:  # En az 30 günlük veri gerekli
                portfoy_sonuclari.append({
                    "ticker": tkr,
                    "weight": weight,
                    "rmse": "-",
                    "mae": "-",
                    "accuracy": "-",
                    "predicted_return": "-",
                    "expected_profit": "-",
                    "error": f"{tkr} için yeterli veri yok (en az 30 günlük veri gerekli)."
                })
                continue
            
            df = veri[['Close']].reset_index()
            
            # Teknik göstergeler - sadece gerekli olanları ekle
            try:
                if "SMA" in gosterge:
                    df["SMA_10"] = df["Close"].rolling(window=10).mean()
                if "EMA" in gosterge:
                    df["EMA_10"] = df["Close"].ewm(span=10, adjust=False).mean()
                if "RSI" in gosterge:
                    df["RSI"] = calculate_rsi(df["Close"])
                if "MACD" in gosterge:
                    macd_line, signal_line = calculate_macd(df["Close"])
                    df["MACD"] = macd_line
                if "Bollinger Bands" in gosterge:
                    upper_band, lower_band = calculate_bollinger_bands(df["Close"])
                    df["BB_upper"] = upper_band
                    df["BB_lower"] = lower_band
                if "Volatility" in gosterge:
                    df["Volatility"] = df["Close"].rolling(window=10).std()
                    
                # Lag features
                for i in range(1, 6):
                    df[f'lag_{i}'] = df['Close'].shift(i)
                    
                df['target'] = df['Close']
                df.dropna(inplace=True)
                
                # Veri yeterliliği kontrolü
                if df.empty or len(df) < 20:  # En az 20 satır gerekli
                    portfoy_sonuclari.append({
                        "ticker": tkr,
                        "weight": weight,
                        "rmse": "-",
                        "mae": "-",
                        "accuracy": "-",
                        "predicted_return": "-",
                        "expected_profit": "-",
                        "error": f"{tkr} için yeterli veri yok (en az 20 satır gerekli). Daha az gösterge seçmeyi deneyin."
                    })
                    continue
                    
                basarili_hisse_var = True
                
                # Feature columns
                feature_cols = [f'lag_{i}' for i in range(1, 6)]
                if "RSI" in gosterge and "RSI" in df.columns:
                    feature_cols.append("RSI")
                if "MACD" in gosterge and "MACD" in df.columns:
                    feature_cols.append("MACD")
                if "Bollinger Bands" in gosterge and "BB_upper" in df.columns:
                    feature_cols.append("BB_upper")
                    feature_cols.append("BB_lower")
                if "Volatility" in gosterge and "Volatility" in df.columns:
                    feature_cols.append("Volatility")
                    
                X = df[feature_cols]
                y = df['target']
                
                # Son veri kontrolü
                if len(X) < 20 or len(y) < 20:
                    portfoy_sonuclari.append({
                        "ticker": tkr,
                        "weight": weight,
                        "rmse": "-",
                        "mae": "-",
                        "accuracy": "-",
                        "predicted_return": "-",
                        "expected_profit": "-",
                        "error": f"{tkr} için modelleme için yeterli veri yok (en az 20 satır gerekli)."
                    })
                    continue
                    
                # NaN değerleri temizle
                X = X.fillna(method='ffill').fillna(method='bfill')
                y = y.fillna(method='ffill').fillna(method='bfill')
                
                # Hala NaN varsa o satırları kaldır
                mask = ~(X.isna().any(axis=1) | y.isna())
                X = X[mask]
                y = y[mask]
                
                if len(X) < 20:
                    portfoy_sonuclari.append({
                        "ticker": tkr,
                        "weight": weight,
                        "rmse": "-",
                        "mae": "-",
                        "accuracy": "-",
                        "predicted_return": "-",
                        "expected_profit": "-",
                        "error": f"{tkr} için NaN temizleme sonrası yeterli veri kalmadı."
                    })
                    continue
                
                # X artık DataFrame olmalı, numpy array değil
                if hasattr(X, 'columns'):
                    X.columns = range(X.shape[1])
                
                # Train-test split öncesi son kontrol
                if len(X) < 10:
                    portfoy_sonuclari.append({
                        "ticker": tkr,
                        "weight": weight,
                        "rmse": "-",
                        "mae": "-",
                        "accuracy": "-",
                        "predicted_return": "-",
                        "expected_profit": "-",
                        "error": f"{tkr} için train-test split için yeterli veri yok."
                    })
                    continue
                
                # Test size'ı veri miktarına göre ayarla
                test_size = min(0.2, len(X) // 5)  # En az 5 satır train için
                if test_size < 0.1:
                    test_size = 0.1
                    
                X_train, X_test, y_train, y_test = train_test_split(X, y, shuffle=False, test_size=test_size)
                
                # Model eğitimi
                if model_name == "LinearRegression":
                    model = LinearRegression()
                    model.fit(X_train, y_train)
                    preds = model.predict(X_test)
                elif model_name == "RandomForest":
                    model = RandomForestRegressor(n_estimators=100, random_state=42)
                    model.fit(X_train, y_train)
                    preds = model.predict(X_test)
                elif model_name == "LightGBM":
                    model = LGBMRegressor(n_estimators=100, random_state=42)
                    model.fit(X_train, y_train)
                    preds = model.predict(X_test)
                elif model_name == "XGBoost":
                    model = XGBRegressor(n_estimators=100, random_state=42)
                    model.fit(X_train, y_train)
                    preds = model.predict(X_test)
                elif model_name == "LSTM":
                    try:
                        scaler = MinMaxScaler()
                        X_scaled = scaler.fit_transform(X)
                        # y'nin numpy array olduğundan emin ol
                        if hasattr(y, 'to_numpy'):
                            y_numpy = y.to_numpy()
                        else:
                            y_numpy = np.array(y)
                        y_scaled = scaler.fit_transform(y_numpy.reshape(-1, 1))
                        
                        seq_length = min(10, len(X_scaled) // 4)  # Veri miktarına göre ayarla
                        if seq_length < 5:
                            seq_length = 5
                            
                        def create_sequences(dataX, dataY, seq_length):
                            xs, ys = [], []
                            for i in range(len(dataX) - seq_length):
                                xs.append(dataX[i:i+seq_length])
                                ys.append(dataY[i+seq_length])
                            return np.array(xs), np.array(ys)
                            
                        X_seq, y_seq = create_sequences(X_scaled, y_scaled, seq_length)
                        
                        if len(X_seq) < 10:
                            portfoy_sonuclari.append({
                                "ticker": tkr,
                                "weight": weight,
                                "rmse": "-",
                                "mae": "-",
                                "accuracy": "-",
                                "predicted_return": "-",
                                "expected_profit": "-",
                                "error": f"{tkr} için LSTM için yeterli sequence verisi yok."
                            })
                            continue
                            
                        split = int(len(X_seq) * 0.8)
                        X_train_seq, X_test_seq = X_seq[:split], X_seq[split:]
                        y_train_seq, y_test_seq = y_seq[:split], y_seq[split:]
                        
                        X_train_torch = torch.tensor(X_train_seq, dtype=torch.float32)
                        y_train_torch = torch.tensor(y_train_seq, dtype=torch.float32)
                        X_test_torch = torch.tensor(X_test_seq, dtype=torch.float32)
                        
                        input_size = X_train_seq.shape[2]
                        lstm_model = LSTMModel(input_size)
                        criterion = nn.MSELoss()
                        optimizer = torch.optim.Adam(lstm_model.parameters(), lr=0.01)
                        
                        lstm_model.train()
                        for epoch in range(10):
                            optimizer.zero_grad()
                            output = lstm_model(X_train_torch)
                            loss = criterion(output, y_train_torch)
                            loss.backward()
                            optimizer.step()
                            
                        lstm_model.eval()
                        with torch.no_grad():
                            preds_scaled = lstm_model(X_test_torch).numpy()
                        preds = scaler.inverse_transform(preds_scaled)
                        y_test = scaler.inverse_transform(y_test_seq)
                        preds = preds.flatten()
                        y_test = y_test.flatten()
                    except Exception as e:
                        portfoy_sonuclari.append({
                            "ticker": tkr,
                            "weight": weight,
                            "rmse": "-",
                            "mae": "-",
                            "accuracy": "-",
                            "predicted_return": "-",
                            "expected_profit": "-",
                            "error": f"{tkr} için LSTM modeli eğitilemedi: {str(e)}"
                        })
                        continue
                else:
                    model = LinearRegression()
                    model.fit(X_train, y_train)
                    preds = model.predict(X_test)
                
                # Metrik hesaplama
                rmse = np.sqrt(mean_squared_error(y_test, preds))
                mae = mean_absolute_error(y_test, preds)
                accuracy = r2_score(y_test, preds) * 100
                
                # Model ve tahmin kaydını veritabanına kaydet
                try:
                    # MLModel kaydı oluştur veya mevcut olanı bul
                    ml_model, created = MLModel.objects.get_or_create(
                        name=f"{model_name}_{tkr}",
                        defaults={
                            'is_active': True
                        }
                    )
                    
                    # PredictionRecord kaydı oluştur
                    prediction_record = PredictionRecord.objects.create(
                        ticker=tkr,
                        model=model_name,
                        rmse=rmse,
                        mae=mae,
                        ml_model=ml_model
                    )
                except Exception as e:
                    print(f"Veritabanı kayıt hatası: {e}")
                
                # Tahmin hesaplama
                n = min(forecast_days, len(y_test))
                y_test_arr = np.array(y_test)
                preds_arr = np.array(preds)
                y_test_last = y_test_arr[-n:]
                preds_last = preds_arr[-n:]
                
                if len(y_test_last) > 1 and len(preds_last) > 1:
                    try:
                        predicted_return = (preds_last[-1] - preds_last[0]) / preds_last[0]
                        expected_profit = investment * (weight/100) * predicted_return
                    except Exception:
                        predicted_return = expected_profit = 0
                else:
                    predicted_return = expected_profit = 0
                    
                portfoy_sonuclari.append({
                    "ticker": tkr,
                    "weight": weight,
                    "rmse": rmse,
                    "mae": mae,
                    "accuracy": accuracy,
                    "predicted_return": predicted_return,
                    "expected_profit": expected_profit,
                })
                
                toplam_beklenen_kar += expected_profit
                toplam_beklenen_getiri += predicted_return * (weight/100)
                toplam_rmse += rmse * (weight/100)
                toplam_mae += mae * (weight/100)
                toplam_accuracy += accuracy * (weight/100)
                
            except Exception as e:
                portfoy_sonuclari.append({
                    "ticker": tkr,
                    "weight": weight,
                    "rmse": "-",
                    "mae": "-",
                    "accuracy": "-",
                    "predicted_return": "-",
                    "expected_profit": "-",
                    "error": f"{tkr} için işlem sırasında hata: {str(e)}"
                })
                continue
                
        if not basarili_hisse_var:
            return render(request, "automl/forecast_result.html", {"error": "Seçilen hisseler için yeterli veri bulunamadı. Lütfen farklı hisseler seçin."})
            
        context = {
            "portfoy_sonuclari": portfoy_sonuclari,
            "toplam_beklenen_kar": toplam_beklenen_kar,
            "toplam_beklenen_getiri": toplam_beklenen_getiri,
            "toplam_rmse": toplam_rmse,
            "toplam_mae": toplam_mae,
            "toplam_accuracy": toplam_accuracy,
            "investment": investment,
            "forecast_days": forecast_days,
        }
        return render(request, "automl/forecast_result.html", context)
    else:
        return render(request, "automl/forecast_result.html", {})

def index(request):
    tickers = ["GOOG", "AAPL", "MSFT", "TSLA", "NVDA"]
    modeller = ["LinearRegression", "RandomForest", "LightGBM", "XGBoost", "LSTM"]
    gosterge_secimi = ["SMA", "EMA", "RSI", "MACD", "Bollinger Bands", "Volatility"]
    
    # Gerçek veriler
    toplam_tahmin = PredictionRecord.objects.count()
    toplam_model = MLModel.objects.count()
    aktif_model = MLModel.objects.filter(is_active=True).count()
    
    # Son tahminler
    son_tahminler = PredictionRecord.objects.order_by('-created_at')[:5]
    
    # Son modeller
    son_modeller = MLModel.objects.order_by('-created_at')[:5]
    
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
        "tickers": tickers,
        "modeller": modeller,
        "gosterge_secimi": gosterge_secimi,
        "toplam_tahmin": toplam_tahmin,
        "toplam_model": toplam_model,
        "aktif_model": aktif_model,
        "son_tahminler": son_tahminler,
        "son_modeller": son_modeller,
        "best_accuracy": f"{best_accuracy:.2f}%",
        "best_model_name": best_model_name,
    }
    return render(request, "automl/index.html", context)

def models_list(request):
    """Modeller listesi sayfası"""
    # Tüm modelleri getir
    models = MLModel.objects.all().order_by('-created_at')
    
    # Model türlerine göre gruplama ve model türü ekleme
    model_types = {}
    for model in models:
        model_type = model.name.split('_')[0] if '_' in model.name else 'Unknown'
        model.model_type = model_type  # Model nesnesine tür ekle
        
        # Son kullanım tarihini bul
        last_prediction = PredictionRecord.objects.filter(ml_model=model).order_by('-created_at').first()
        model.last_used = last_prediction.created_at if last_prediction else None
        
        if model_type not in model_types:
            model_types[model_type] = 0
        model_types[model_type] += 1
    
    # Model istatistikleri
    total_models = models.count()
    active_models = models.filter(is_active=True).count()
    inactive_models = models.filter(is_active=False).count()
    
    # Son tahminler
    recent_predictions = PredictionRecord.objects.all().order_by('-created_at')[:10]
    
    context = {
        'models': models,
        'total_models': total_models,
        'active_models': active_models,
        'inactive_models': inactive_models,
        'model_types': model_types,
        'recent_predictions': recent_predictions,
    }
    
    return render(request, "automl/models_list.html", context)

def toggle_model_status(request, model_id):
    """Model durumunu değiştir (aktif/pasif)"""
    if request.method == 'POST':
        try:
            import json
            data = json.loads(request.body)
            is_active = data.get('is_active', False)
            
            model = MLModel.objects.get(id=model_id)
            model.is_active = is_active
            model.save()
            
            return JsonResponse({'success': True})
        except MLModel.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Model bulunamadı'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Geçersiz istek'})

def delete_model(request, model_id):
    """Modeli sil"""
    if request.method == 'DELETE':
        try:
            model = MLModel.objects.get(id=model_id)
            model.delete()
            return JsonResponse({'success': True})
        except MLModel.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Model bulunamadı'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Geçersiz istek'})
