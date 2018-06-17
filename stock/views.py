import logging
from . import main
from . import load_history

from django.contrib.auth import authenticate, login, logout
from django.template import RequestContext, loader, Context
from django.shortcuts import render_to_response, redirect
from django.shortcuts import render
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from .forms import *


def check_fields_in_post(fields, post):
    for field in fields:
        if field not in post:
            logging.error('no ' + field + 'in the request')
            return False

    return True


def index(request):
    context_dict = {
        'user': request.user,
    }

    return render(request, 'stock/index.html', context_dict)


def login_page(request):
    if request.method == 'POST':
        fields = ('username', 'password')
        if not check_fields_in_post(fields, request.POST):
            t = loader.get_template('stock/error.txt')
            c = Context({})
            return HttpResponse(t.render(c), content_type='text/plain')

        username = request.POST['username']
        password = request.POST['password']

        user = authenticate(username=username, password=password)
        if not user:
            return render_to_response('stock/nouser.html')
        if not user.is_active:
            return render_to_response('stock/inact_user.html')

        login(request, user)

        logging.info('user logged in: ' + username)
        return redirect('/stock/summary/')

    else:
        form = LoginForm()
        return render(request, 'stock/', {'form': form})


def logout_page(request):
    logout(request)
    return redirect('/stock/')


def load_data_page(request):
    if not request.user.is_authenticated:
        return redirect('/stock/')

    load_history.load_data()

    return render(request, 'stock/success.txt', {})


@csrf_exempt
def run_page(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')

    if ip != '127.0.0.1':
        return render(request, 'stock/error.txt', {})

    main.run()

    return render(request, 'stock/success.txt', {})


def simulate_page(request):
    if not request.user.is_authenticated:
        return redirect('/stock/')

    main.simulate()

    return render(request, 'stock/success.txt', {})
