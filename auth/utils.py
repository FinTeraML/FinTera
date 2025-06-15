import random
import string
from django.core.cache import cache
from django.core.mail import send_mail
from django.conf import settings

def generate_otp():
    """Generate a 6-digit OTP"""
    return ''.join(random.choices(string.digits, k=6))

def send_otp_email(email, otp):
    """Send OTP to user's email"""
    subject = 'Verify your new email address'
    message = f'Your OTP for email verification is: {otp}\n\nThis OTP will expire in 10 minutes.'
    from_email = settings.DEFAULT_FROM_EMAIL
    recipient_list = [email]
    
    send_mail(subject, message, from_email, recipient_list)

def store_otp(email, otp):
    """Store OTP in cache with 10-minute expiration"""
    cache_key = f'email_verification_otp_{email}'
    cache.set(cache_key, otp, timeout=600)  # 600 seconds = 10 minutes

def verify_otp(email, otp):
    """Verify OTP for given email"""
    cache_key = f'email_verification_otp_{email}'
    stored_otp = cache.get(cache_key)
    
    if stored_otp and stored_otp == otp:
        cache.delete(cache_key)  # Clear OTP after successful verification
        # Set email as verified
        set_email_verified(email)
        return True
    return False

def set_email_verified(email):
    """Mark an email as verified"""
    cache_key = f'email_verified_{email}'
    cache.set(cache_key, True, timeout=3600)  # 1 hour expiration

def is_email_verified(email):
    """Check if an email is verified"""
    cache_key = f'email_verified_{email}'
    return cache.get(cache_key, False)

def clear_email_verification(email):
    """Clear email verification state"""
    cache_key = f'email_verified_{email}'
    cache.delete(cache_key) 