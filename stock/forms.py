from django import forms
from django.utils import timezone
from .models import *


class LoginForm(forms.Form):
    username = forms.CharField(max_length=50, label='User:')
    password = forms.CharField(label='Password: ', widget=forms.PasswordInput())


class ReportForm(forms.Form):
    td = timezone.timedelta(30)

    start_date = forms.DateField(initial=timezone.now().today()-td, widget=forms.SelectDateWidget())
    end_date = forms.DateField(initial=timezone.now().today(), widget=forms.SelectDateWidget())


class SimulateForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(SimulateForm, self).__init__(*args, **kwargs)

        for key in self.fields:
            self.fields[key].required = False

    class Meta:
        model = Stock
        fields = ['algorithm', 'stance']

    td = timezone.timedelta(30)

    year_choices = []
    for year in range(2002, timezone.now().year + 1):
        year_choices.append('%d' % year)

    start_date = forms.DateField(initial=timezone.now().today()-td, widget=forms.SelectDateWidget(years=year_choices))
    end_date = forms.DateField(initial=timezone.now().today(), widget=forms.SelectDateWidget(years=year_choices))
