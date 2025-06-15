from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import (
    LoginView, LogoutView, PasswordResetView, PasswordResetDoneView,
    PasswordResetConfirmView, PasswordResetCompleteView, PasswordChangeView,
    PasswordChangeDoneView
)
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import CreateView, View
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.sites.shortcuts import get_current_site
from django.utils.crypto import get_random_string
from .forms import (
    CustomUserCreationForm, CustomAuthenticationForm, CustomPasswordResetForm,
    CustomSetPasswordForm, CustomPasswordChangeForm, EditProfileForm
)
from django.http import JsonResponse
from .utils import generate_otp, send_otp_email, store_otp, verify_otp
from .models import EmailVerification


class RegisterView(CreateView):
    model = User
    form_class = CustomUserCreationForm
    template_name = 'auth/register.html'
    success_url = reverse_lazy('auth:login')

    def get(self, request, *args, **kwargs):
        messages.get_messages(request).used = True  # Clear existing messages
        return super().get(request, *args, **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)
        user = form.save()
        
        # Create email verification
        token = get_random_string(64)
        verification = EmailVerification.objects.create(
            user=user,
            token=token
        )
        
        # Send verification email
        current_site = get_current_site(self.request)
        subject = 'Verify your FinTera account'
        message = render_to_string('auth/email/email_verification.html', {
            'user': user,
            'domain': current_site.domain,
            'protocol': 'https' if self.request.is_secure() else 'http',
            'token': token,
        })
        
        send_mail(
            subject,
            message,
            None,  # Use DEFAULT_FROM_EMAIL from settings
            [user.email],
            fail_silently=False,
        )
        
        messages.success(
            self.request,
            'Account created successfully! Please check your email to verify your account.'
        )
        return response

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('landing:index')
        return super().dispatch(request, *args, **kwargs)


class EmailVerificationView(View):
    def get(self, request, token):
        try:
            verification = EmailVerification.objects.get(token=token)
            
            if verification.is_expired():
                messages.error(request, 'Verification link has expired. Please request a new one.')
                return redirect('auth:login')
            
            if verification.is_verified:
                messages.info(request, 'Email already verified. You can now log in.')
                return redirect('auth:login')
            
            # Mark email as verified
            verification.is_verified = True
            verification.save()
            
            messages.success(request, 'Email verified successfully! You can now log in.')
            return redirect('auth:login')
            
        except EmailVerification.DoesNotExist:
            messages.error(request, 'Invalid verification link.')
            return redirect('auth:login')


class CustomLoginView(LoginView):
    form_class = CustomAuthenticationForm
    template_name = 'auth/login.html'
    redirect_authenticated_user = True

    def get(self, request, *args, **kwargs):
        messages.get_messages(request).used = True  # Clear existing messages
        return super().get(request, *args, **kwargs)

    def form_valid(self, form):
        user = form.get_user()
        
        # Check if email is verified
        try:
            verification = EmailVerification.objects.get(user=user)
            if not verification.is_verified:
                messages.error(
                    self.request,
                    'Please verify your email address before logging in. Check your email for the verification link.'
                )
                return self.form_invalid(form)
        except EmailVerification.DoesNotExist:
            # For backward compatibility with existing users
            pass
        
        messages.success(self.request, f'Welcome back, {user.first_name or user.username}!')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Invalid username or password. Please try again.')
        return super().form_invalid(form)


class CustomLogoutView(LogoutView):
    template_name = 'auth/logout.html'

    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)


class CustomPasswordResetView(PasswordResetView):
    form_class = CustomPasswordResetForm
    template_name = 'auth/password_reset.html'
    email_template_name = 'auth/email/password_reset_email.html'
    subject_template_name = 'auth/email/password_reset_subject.txt'
    success_url = reverse_lazy('auth:password_reset_done')

    def form_valid(self, form):
        messages.success(self.request, 'Password reset email has been sent to your email address.')
        return super().form_valid(form)


class CustomPasswordResetDoneView(PasswordResetDoneView):
    template_name = 'auth/password_reset_done.html'


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    form_class = CustomSetPasswordForm
    template_name = 'auth/password_reset_confirm.html'
    success_url = reverse_lazy('auth:password_reset_complete')

    def form_valid(self, form):
        messages.success(self.request, 'Your password has been reset successfully!')
        return super().form_valid(form)


class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = 'auth/password_reset_complete.html'


class CustomPasswordChangeView(PasswordChangeView):
    form_class = CustomPasswordChangeForm
    template_name = 'auth/password_change.html'
    success_url = reverse_lazy('auth:password_change_done')

    def form_valid(self, form):
        messages.success(self.request, 'Your password has been changed successfully!')
        return super().form_valid(form)


class CustomPasswordChangeDoneView(PasswordChangeDoneView):
    template_name = 'auth/password_change_done.html'


@login_required
def profile_view(request):
    """Profile view to display user information"""
    return render(request, 'auth/profile.html', {'user': request.user})

@login_required
def edit_profile(request):
    """Handle profile editing with email verification"""
    if request.method == 'POST':
        form = EditProfileForm(request.POST, instance=request.user)
        
        if form.is_valid():
            # Check if email is being changed
            if form.cleaned_data['email'] != request.user.email:
                # Verify OTP if provided
                if not verify_otp(form.cleaned_data['email'], form.cleaned_data.get('otp_code')):
                    messages.error(request, 'Invalid or expired OTP. Please request a new one.')
                    return JsonResponse({'status': 'error', 'message': 'Invalid OTP'})
            
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return JsonResponse({'status': 'success'})
        else:
            return JsonResponse({'status': 'error', 'errors': form.errors})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

@login_required
def send_verification_otp(request):
    """Send OTP for email verification"""
    if request.method == 'POST':
        email = request.POST.get('email')
        
        if not email:
            return JsonResponse({'status': 'error', 'message': 'Email is required'})
        
        if email == request.user.email:
            return JsonResponse({'status': 'error', 'message': 'This is your current email address'})
        
        # Generate and send OTP
        otp = generate_otp()
        store_otp(email, otp)
        send_otp_email(email, otp)
        
        return JsonResponse({'status': 'success', 'message': 'OTP sent successfully'})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

@login_required
def verify_otp_view(request):
    """Verify OTP for email change"""
    if request.method == 'POST':
        email = request.POST.get('email')
        otp = request.POST.get('otp_code')
        
        if not email or not otp:
            return JsonResponse({
                'status': 'error',
                'message': 'Email and OTP are required'
            })
        
        if verify_otp(email, otp):
            return JsonResponse({
                'status': 'success',
                'message': 'OTP verified successfully'
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid or expired OTP'
            })
    
    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method'
    })
