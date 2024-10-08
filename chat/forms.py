from django import forms

class SignUpForm(forms.Form):
    username = forms.CharField(max_length=100)
    email = forms.EmailField()

class OTPVerificationForm(forms.Form):
    otp = forms.CharField(max_length=6)

class SignInForm(forms.Form):
    email = forms.EmailField()

from .models import Feedback

class FeedbackForm(forms.ModelForm):
    class Meta:
        model = Feedback
        fields = ['message']

class ContactForm(forms.Form):
    name = forms.CharField(max_length=100)
    email = forms.EmailField()
    message = forms.CharField(widget=forms.Textarea)