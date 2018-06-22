from django import forms
from datetime import date, timedelta
from .models import *


class LoginForm(forms.Form):
    username = forms.CharField(max_length=50, label='User:')
    password = forms.CharField(label='Password: ', widget=forms.PasswordInput())


class ReportForm(forms.Form):
    td = timedelta(30)

    start_date = forms.DateField(initial=date.today()-td, widget=forms.SelectDateWidget())
    end_date = forms.DateField(initial=date.today(), widget=forms.SelectDateWidget())


class SimulateForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(SimulateForm, self).__init__(*args, **kwargs)

        for key in self.fields:
            self.fields[key].required = False

    class Meta:
        model = Stock
        fields = ['algorithm', 'stance']

    td = timedelta(30)

    start_date = forms.DateField(initial=date.today()-td, widget=forms.SelectDateWidget())
    end_date = forms.DateField(initial=date.today(), widget=forms.SelectDateWidget())
