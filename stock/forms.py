from django import forms


class LoginForm(forms.Form):
    username = forms.CharField(max_length=50, label='User:')
    password = forms.CharField(label='Password: ', widget=forms.PasswordInput())