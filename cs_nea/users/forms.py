from django.forms import ModelForm
from .models import User

from django import forms

class LoginForm(ModelForm):
    class Meta:
        model = User
        fields = ["username", "password"]  
    
class SignupForm(ModelForm):
    class Meta:
        model = User
        fields = "__all__"
        
    def clean_username(self):
        username = self.cleaned_data.get("username")
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Username already exists")
        return username
        

