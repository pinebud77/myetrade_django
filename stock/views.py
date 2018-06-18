import logging
import csv
from . import main
from . import load_history
from .forms import *
from .models import *
from django.contrib.auth import authenticate, login, logout
from django.template import loader, Context
from django.shortcuts import render_to_response, redirect
from django.shortcuts import render
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime
from os.path import realpath, dirname, join, basename



CUR_DIR = dirname(realpath(__file__))


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
        return redirect('/stock/report/')

    else:
        form = LoginForm()
        return render(request, 'stock/', {'form': form})


def logout_page(request):
    logout(request)
    return redirect('/stock/')


def reportrange_page(request, s_year, s_month, s_day, e_year, e_month, e_day):
    if not request.user.is_authenticated:
        return redirect('/stock/')

    start_dt = datetime(year=int(s_year), month=int(s_month), day=int(s_day),
                        hour=0, minute=0, second=0)
    end_dt = datetime(year=int(e_year), month=int(e_month), day=int(e_day),
                        hour=23, minute=59, second=59)

    report_list = []

    account_id_list = []
    symbol_list = []

    for account in Account.objects.all():
        account_id_list.append(account.account_id)

    for stock in Stock.objects.all():
        if str(stock.symbol) not in symbol_list:
            symbol_list.append(str(stock.symbol))

    prev_line = (0.0, ) * (1 + len(account_id_list) + len(symbol_list))
    base_values = [0.0, ] * (len(account_id_list) + len(symbol_list))
    for day_report in DayReport.objects.filter(date__gt=start_dt, date__lt=end_dt).order_by('date'):
        line = list()
        line.append('%d/%d/%d' % (day_report.date.month, day_report.date.day, day_report.date.year))
        col = 1
        for account_id in account_id_list:
            if account_id == day_report.account_id:
                val = float(day_report.net_value)
            else:
                val = prev_line[col]
            if base_values[col - 1] == 0.0 and val != 0.0:
                base_values[col - 1] = val
            if base_values[col - 1]:
                line.append(val / base_values[col - 1])
            else:
                line.append(0.0)
            col += 1
        for symbol in symbol_list:
            try:
                quote = Quote.objects.filter(symbol=symbol, date__lt=day_report.date).order_by('-date')[0]
                val = float(quote.price)
            except IndexError:
                try:
                    quote = SimQuote.objects.filter(symbol=symbol, date__lt=day_report.date).order_by('-date')[0]
                    val = float(quote.price)
                except IndexError:
                    val = prev_line[col]
            if base_values[col - 1] == 0.0 and val != 0.0:
                base_values[col - 1] = val
            if base_values[col - 1]:
                line.append(val / base_values[col - 1])
            else:
                line.append(0.0)
            col += 1

        line_tuple = tuple(line)
        report_list.append(line_tuple)
        prev_line = line_tuple

    filename = 'report_%d%2.2d%2.2d_%d%2.2d%2.2d.csv' % (start_dt.year, start_dt.month, start_dt.day,
                                                         end_dt.year, end_dt.month, end_dt.day)
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="%s"' % filename

    writer = csv.writer(response)
    header = ['date']
    for account in account_id_list:
        header.append('account:%d' % account)
    for symbol in symbol_list:
        header.append(symbol)
    writer.writerow(header)

    for line in report_list:
        writer.writerow(line)

    return response


def report_page(request):
    if not request.user.is_authenticated:
        return redirect('/stock/')

    if request.method == 'POST':
        start_date = request.POST['start_date']
        end_date = request.POST['end_date']

        return redirect('/stock/reportrange/%s-%s' % (start_date, end_date))
    else:
        form = ReportForm()
        return render(request, 'stock/report.html', {'form': form})


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
