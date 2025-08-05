from django import forms
from moderation.models import  Subscriptions

class SubscriptionForm(forms.ModelForm):
    email = forms.CharField(max_length=64, widget=forms.TextInput(attrs={'placeholder': 'Email',  'name':'emailaddress', 'id': 'profile-email', 'class':'form-control'}))

    class Meta:
        model = Subscriptions
        fields = ['email',]