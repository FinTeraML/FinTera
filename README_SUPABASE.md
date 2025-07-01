# 🚀 Supabase Entegrasyonu - FinTera

Bu rehber, FinTera projesini Supabase ile entegre etmek için adım adım talimatları içerir.

## 📋 İçindekiler

1. [Supabase Kurulumu](#supabase-kurulumu)
2. [Veritabanı Şeması](#veritabanı-şeması)
3. [Django Entegrasyonu](#django-entegrasyonu)
4. [Kullanım Örnekleri](#kullanım-örnekleri)
5. [Güvenlik](#güvenlik)

## 🎯 Supabase Kurulumu

### 1. Supabase Projesi Oluşturma

1. [Supabase](https://supabase.com) sitesine gidin
2. "Start your project" butonuna tıklayın
3. GitHub ile giriş yapın
4. Yeni proje oluşturun:
   - **Organization**: Kendi organizasyonunuzu seçin
   - **Name**: `fintera-ml`
   - **Database Password**: Güçlü bir şifre belirleyin
   - **Region**: Size en yakın bölgeyi seçin

### 2. Proje Ayarları

Proje oluşturulduktan sonra:

1. **Settings > API** bölümüne gidin
2. Şu bilgileri not edin:
   - **Project URL**: `https://your-project-ref.supabase.co`
   - **anon public key**: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`

### 3. Environment Variables

Proje kök dizininde `.env` dosyası oluşturun:

```env
# Supabase Configuration
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Django Configuration
SECRET_KEY=your-django-secret-key
DEBUG=True
```

## 🗄️ Veritabanı Şeması

### 1. SQL Şemasını Çalıştırma

1. Supabase Dashboard'da **SQL Editor**'e gidin
2. `FinTeraML/supabase_sql.sql` dosyasındaki SQL kodunu kopyalayın
3. SQL Editor'de çalıştırın

### 2. Tablo Yapısı

#### ML Models Tablosu
```sql
CREATE TABLE ml_models (
    id BIGINT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    model_type VARCHAR(100),
    parameters JSONB DEFAULT '{}',
    performance_metrics JSONB DEFAULT '{}'
);
```

#### Prediction Records Tablosu
```sql
CREATE TABLE prediction_records (
    id BIGINT PRIMARY KEY,
    ticker VARCHAR(20) NOT NULL,
    model VARCHAR(100) NOT NULL,
    rmse DECIMAL(10, 6),
    mae DECIMAL(10, 6),
    accuracy DECIMAL(5, 4),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ml_model_id BIGINT REFERENCES ml_models(id),
    prediction_data JSONB DEFAULT '{}'
);
```

## 🔧 Django Entegrasyonu

### 1. Gerekli Paketleri Yükleme

```bash
pip install supabase python-dotenv
```

### 2. Supabase Konfigürasyonu

`FinTeraML/supabase_config.py` dosyası otomatik olarak oluşturuldu. Bu dosya:

- Supabase client'ını başlatır
- Veri senkronizasyonu sağlar
- CRUD işlemleri yapar

### 3. Kullanım Örnekleri

#### Model Senkronizasyonu
```python
from FinTeraML.supabase_config import sync_models_to_supabase

# Django modellerini Supabase'e senkronize et
success = sync_models_to_supabase()
if success:
    print("✅ Modeller başarıyla senkronize edildi")
else:
    print("❌ Senkronizasyon hatası")
```

#### Veri Alma
```python
from FinTeraML.supabase_config import get_models_from_supabase

# Supabase'den modelleri al
models = get_models_from_supabase()
for model in models:
    print(f"Model: {model['name']}")
```

## 🎮 Kullanım Örnekleri

### 1. Otomatik Senkronizasyon

`automl/views.py` dosyasında model oluşturulduğunda otomatik senkronizasyon:

```python
from FinTeraML.supabase_config import sync_models_to_supabase

def get_stock_forecast(request):
    # ... mevcut kod ...
    
    # Model kaydedildikten sonra
    if model:
        # Supabase'e senkronize et
        sync_models_to_supabase()
    
    return render(request, "automl/forecast_result.html", context)
```

### 2. Dashboard'da Supabase Verilerini Gösterme

```python
from FinTeraML.supabase_config import get_models_from_supabase, get_predictions_from_supabase

def dashboard(request):
    # Supabase'den veri al
    supabase_models = get_models_from_supabase()
    supabase_predictions = get_predictions_from_supabase()
    
    context = {
        'supabase_models': supabase_models,
        'supabase_predictions': supabase_predictions,
    }
    
    return render(request, "landing/dashboard.html", context)
```

### 3. Real-time Veri Güncelleme

Supabase'in real-time özelliğini kullanarak:

```javascript
// Frontend'de real-time dinleme
const supabase = createClient('YOUR_SUPABASE_URL', 'YOUR_SUPABASE_KEY')

// Model değişikliklerini dinle
supabase
  .channel('ml_models')
  .on('postgres_changes', { event: '*', schema: 'public', table: 'ml_models' }, payload => {
    console.log('Model değişikliği:', payload)
    // UI'ı güncelle
  })
  .subscribe()
```

## 🔒 Güvenlik

### 1. Row Level Security (RLS)

Supabase'de RLS aktif. Güvenlik politikaları:

```sql
-- Sadece okuma izni (herkese açık)
CREATE POLICY "Allow public read access" ON ml_models
    FOR SELECT USING (true);

-- Sadece authenticated kullanıcılar yazabilir
CREATE POLICY "Allow authenticated insert" ON ml_models
    FOR INSERT WITH CHECK (auth.role() = 'authenticated');
```

### 2. Environment Variables

Hassas bilgileri `.env` dosyasında saklayın:

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
```

### 3. API Key Güvenliği

- **anon key**: Public, client-side kullanım için
- **service_role key**: Server-side, admin işlemleri için (güvenli tutun)

## 📊 Monitoring ve Analytics

### 1. Supabase Dashboard

- **Table Editor**: Verileri görüntüleme ve düzenleme
- **Logs**: API çağrılarını izleme
- **Analytics**: Performans metrikleri

### 2. Custom Queries

```sql
-- Model performans istatistikleri
SELECT 
    model_type,
    COUNT(*) as total_models,
    AVG(CAST(performance_metrics->>'accuracy' AS DECIMAL)) as avg_accuracy
FROM ml_models
GROUP BY model_type;
```

## 🚀 Deployment

### 1. Production Environment

```env
# Production .env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-production-key
DEBUG=False
SECRET_KEY=your-production-secret
```

### 2. Heroku/Vercel Deployment

```bash
# Environment variables'ları set et
heroku config:set SUPABASE_URL=https://your-project.supabase.co
heroku config:set SUPABASE_KEY=your-key
```

## 🔧 Troubleshooting

### Yaygın Hatalar

1. **Connection Error**:
   - URL ve key'leri kontrol edin
   - Network bağlantısını kontrol edin

2. **Permission Denied**:
   - RLS politikalarını kontrol edin
   - API key'in doğru olduğundan emin olun

3. **Table Not Found**:
   - SQL şemasını çalıştırdığınızdan emin olun
   - Tablo isimlerini kontrol edin

### Debug Mode

```python
# Debug için
import logging
logging.basicConfig(level=logging.DEBUG)

from FinTeraML.supabase_config import init_supabase
client = init_supabase()
print(f"Client initialized: {client is not None}")
```

## 📈 Sonraki Adımlar

1. **Authentication**: Supabase Auth entegrasyonu
2. **Real-time**: WebSocket bağlantıları
3. **Storage**: Model dosyalarını Supabase Storage'da saklama
4. **Edge Functions**: Serverless fonksiyonlar
5. **Analytics**: Detaylı performans analizi

---

## 🎉 Başarı!

Artık FinTera projeniz Supabase ile entegre! Verileriniz güvenli, ölçeklenebilir ve real-time olarak erişilebilir durumda.

**İhtiyacınız olan başka bir şey var mı?** 🤔 