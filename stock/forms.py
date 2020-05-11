#!/usr/bin/env python3

# Owen Kwon, hereby disclaims all copyright interest in the program "myetrade_django" written by Owen (Ohkeun) Kwon.

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>

from django import forms
from django.utils import timezone
from .models import *


year_choices = []
for year in range(2002, timezone.now().year + 1):
    year_choices.append('%d' % year)


class LoginForm(forms.Form):
    username = forms.CharField(max_length=50, label='User:')
    password = forms.CharField(label='Password: ', widget=forms.PasswordInput())


class ReportForm(forms.Form):
    td = timezone.timedelta(30)

    start_date = forms.DateField(initial=timezone.now().today()-td, widget=forms.SelectDateWidget(years=year_choices))
    end_date = forms.DateField(initial=timezone.now().today(), widget=forms.SelectDateWidget(years=year_choices))


class LearnForm(forms.Form):
    start_date = forms.DateField(initial=timezone.datetime(year=2002, month=1, day=1),
                                 widget=forms.SelectDateWidget(years=year_choices))
    end_date = forms.DateField(initial=timezone.datetime(year=2002, month=12, day=31),
                               widget=forms.SelectDateWidget(years=year_choices))


class SimulateForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(SimulateForm, self).__init__(*args, **kwargs)

        for key in self.fields:
            self.fields[key].required = False

    class Meta:
        model = Stock
        fields = ['in_algorithm', 'in_stance', 'out_algorithm', 'out_stance']

    td = timezone.timedelta(30)

    start_date = forms.DateField(initial=timezone.now().today()-td, widget=forms.SelectDateWidget(years=year_choices))
    end_date = forms.DateField(initial=timezone.now().today(), widget=forms.SelectDateWidget(years=year_choices))


class GraphRangeForm(forms.Form):
    end_date = forms.DateField(initial=timezone.now().today(), widget=forms.SelectDateWidget(years=year_choices))
    days = forms.IntegerField(initial=30)
