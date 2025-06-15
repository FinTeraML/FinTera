from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordResetForm, SetPasswordForm, PasswordChangeForm
from django.contrib.auth.models import User
from .utils import is_email_verified


class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)

    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "email", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add DaisyUI classes to form fields
        for fieldname in self.fields:
            self.fields[fieldname].widget.attrs.update({
                'class': 'input input-bordered w-full',
                'placeholder': self.fields[fieldname].label
            })

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        if commit:
            user.save()
        return user


class CustomAuthenticationForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add DaisyUI classes to form fields
        for fieldname in self.fields:
            self.fields[fieldname].widget.attrs.update({
                'class': 'input input-primary w-full',
                'placeholder': self.fields[fieldname].label
            })


class CustomPasswordResetForm(PasswordResetForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].widget.attrs.update({
            'class': 'input input-primary w-full',
            'placeholder': 'Email address'
        })


class CustomSetPasswordForm(SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for fieldname in self.fields:
            self.fields[fieldname].widget.attrs.update({
                'class': 'input input-primary w-full',
                'placeholder': self.fields[fieldname].label
            }) 

class CustomPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add DaisyUI classes with better visibility for dark themes
        for fieldname in self.fields:
            self.fields[fieldname].widget.attrs.update({
                'class': 'input input-primary w-full',
                'placeholder': self.fields[fieldname].label
            })

class EditProfileForm(forms.ModelForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    otp_code = forms.CharField(max_length=6, required=False, widget=forms.HiddenInput())

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add DaisyUI classes to form fields
        for fieldname in self.fields:
            if fieldname != 'otp_code':  # Don't style hidden fields
                self.fields[fieldname].widget.attrs.update({
                    'class': 'input input-bordered w-full',
                    'placeholder': self.fields[fieldname].label
                })

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email != self.instance.email:
            # Email is being changed, require server-side verification
            if not is_email_verified(email):
                raise forms.ValidationError('Please verify your new email address with the OTP code.')
        return email