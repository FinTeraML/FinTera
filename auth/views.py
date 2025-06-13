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
from django.views.generic import CreateView
from django.contrib.auth.models import User
from .forms import (
    CustomUserCreationForm, CustomAuthenticationForm, CustomPasswordResetForm,
    CustomSetPasswordForm, CustomPasswordChangeForm, EditProfileForm
)
from django.http import JsonResponse
from .utils import generate_otp, send_otp_email, store_otp, verify_otp


class RegisterView(CreateView):
    model = User
    form_class = CustomUserCreationForm
    template_name = 'auth/register.html'
    success_url = reverse_lazy('auth:login')

    def form_valid(self, form):
        response = super().form_valid(form)
        username = form.cleaned_data.get('username')
        messages.success(self.request, f'Account created successfully for {username}! You can now log in.')
        return response

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('landing:index')
        return super().dispatch(request, *args, **kwargs)


class CustomLoginView(LoginView):
    form_class = CustomAuthenticationForm
    template_name = 'auth/login.html'
    redirect_authenticated_user = True

    def get(self, request, *args, **kwargs):
        # Clear any existing messages when loading the login page
        # This prevents logout messages from showing on the login form
        messages.get_messages(request)
        return super().get(request, *args, **kwargs)

    def form_valid(self, form):
        messages.success(self.request, f'Welcome back, {form.get_user().first_name or form.get_user().username}!')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Invalid username or password. Please try again.')
        return super().form_invalid(form)


class CustomLogoutView(LogoutView):
    template_name = 'auth/logout.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            messages.success(request, 'You have been logged out successfully.')
        return super().dispatch(request, *args, **kwargs)


class CustomPasswordResetView(PasswordResetView):
    form_class = CustomPasswordResetForm
    template_name = 'auth/password_reset.html'
    email_template_name = 'auth/password_reset_email.html'
    subject_template_name = 'auth/password_reset_subject.txt'
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
