from django import forms
from datetime import date, timedelta


class LoginForm(forms.Form):
    username = forms.CharField(max_length=50, label='User:')
    password = forms.CharField(label='Password: ', widget=forms.PasswordInput())


class ReportForm(forms.Form):
    td = timedelta(7)

    start_date = forms.DateField(initial=date.today()-td)
    end_date = forms.DateField(initial=date.today())
