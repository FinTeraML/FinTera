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
    CustomSetPasswordForm, CustomPasswordChangeForm
)


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
    """Simple profile view to display user information"""
    return render(request, 'auth/profile.html', {'user': request.user})
