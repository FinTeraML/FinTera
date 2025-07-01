"""
Supabase Configuration for FinTera
"""
import os
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Supabase configuration
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

# Initialize Supabase client
supabase: Client = None

def init_supabase():
    """Initialize Supabase client"""
    global supabase
    if SUPABASE_URL and SUPABASE_KEY:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        return supabase
    else:
        print("⚠️ Supabase credentials not found. Please set SUPABASE_URL and SUPABASE_KEY in .env file")
        return None

def get_supabase_client():
    """Get Supabase client instance"""
    global supabase
    if supabase is None:
        supabase = init_supabase()
    return supabase

# Database operations
def sync_models_to_supabase():
    """Sync Django models to Supabase"""
    from automl.models import MLModel, PredictionRecord
    
    client = get_supabase_client()
    if not client:
        return False
    
    try:
        # Sync ML Models
        models = MLModel.objects.all()
        for model in models:
            model_data = {
                'id': model.id,
                'name': model.name,
                'created_at': model.created_at.isoformat(),
                'is_active': getattr(model, 'is_active', True),
                'model_type': model.name.split('_')[0] if '_' in model.name else 'Unknown'
            }
            
            # Insert or update in Supabase
            result = client.table('ml_models').upsert(model_data).execute()
            print(f"✅ Synced model: {model.name}")
        
        # Sync Prediction Records
        predictions = PredictionRecord.objects.all()
        for pred in predictions:
            pred_data = {
                'id': pred.id,
                'ticker': pred.ticker,
                'model': pred.model,
                'rmse': pred.rmse,
                'mae': pred.mae,
                'accuracy': pred.accuracy,
                'created_at': pred.created_at.isoformat(),
                'ml_model_id': pred.ml_model.id if pred.ml_model else None
            }
            
            # Insert or update in Supabase
            result = client.table('prediction_records').upsert(pred_data).execute()
            print(f"✅ Synced prediction: {pred.ticker}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error syncing to Supabase: {str(e)}")
        return False

def get_models_from_supabase():
    """Get models from Supabase"""
    client = get_supabase_client()
    if not client:
        return []
    
    try:
        result = client.table('ml_models').select('*').execute()
        return result.data
    except Exception as e:
        print(f"❌ Error getting models from Supabase: {str(e)}")
        return []

def get_predictions_from_supabase():
    """Get predictions from Supabase"""
    client = get_supabase_client()
    if not client:
        return []
    
    try:
        result = client.table('prediction_records').select('*').execute()
        return result.data
    except Exception as e:
        print(f"❌ Error getting predictions from Supabase: {str(e)}")
        return [] 