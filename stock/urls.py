from django.urls import path
from . import views


urlpatterns = [
    path('simulate/', views.simulate_page),
    path('loaddata/', views.load_data_page),
    path('run/', views.run_page),
    path('logout/', views.logout_page),
    path('login/', views.login_page),
    path('', views.index, name='index'),
]