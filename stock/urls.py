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

from django.urls import path
from django.conf.urls import url
from . import views


urlpatterns = [
    url(r'report_range/(?P<s_year>.{4})(?P<s_month>.{2})(?P<s_day>.{2})'
        r'-(?P<e_year>.{4})(?P<e_month>.{2})(?P<e_day>.{2})',
        views.report_range_page),
    path('graph/', views.graph_page),
    path('test/', views.test_page),
    path('learn/', views.learn_page),
    path('report/', views.report_page),
    path('simulate/', views.simulate_page),
    path('loaddata/', views.load_data_page),
    path('run/', views.run_page),
    path('logout/', views.logout_page),
    path('login/', views.login_page),
    path('', views.index, name='index'),
]