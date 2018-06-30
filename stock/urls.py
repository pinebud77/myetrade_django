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
    path('get_history/', views.get_history_page),
    path('logout/', views.logout_page),
    path('login/', views.login_page),
    path('', views.index, name='index'),
]