import logging
import csv
from . import main
from python_simtrade import load_history
from .forms import *
from .models import *
from django.contrib.auth import authenticate, login, logout
from django.template import loader, Context
from django.shortcuts import render_to_response, redirect
from django.shortcuts import render
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from os.path import realpath, dirname

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


def report_range_page(request, s_year, s_month, s_day, e_year, e_month, e_day):
    if not request.user.is_authenticated:
        return redirect('/stock/')

    start_dt = timezone.datetime(year=int(s_year), month=int(s_month), day=int(s_day))
    end_dt = timezone.datetime(year=int(e_year), month=int(e_month), day=int(e_day))

    report_list = []

    account_id_list = []
    symbol_list = []

    for account in Account.objects.all().order_by('account_id'):
        account_id_list.append(account.account_id)

    for stock in Stock.objects.all().order_by('symbol'):
        if str(stock.symbol) not in symbol_list:
            symbol_list.append(str(stock.symbol))

    prev_line = (0.0, ) * (1 + len(account_id_list) + len(symbol_list))
    base_values = [0.0, ] * (len(account_id_list) + len(symbol_list))
    for day_report in DayReport.objects.filter(date__gte=start_dt.date(), date__lte=end_dt.date()).order_by('date'):
        line = list()
        line.append('%d/%d/%d' % (day_report.date.month, day_report.date.day, day_report.date.year))
        col = 1
        for account_id in account_id_list:
            if account_id == day_report.account_id:
                val = float(day_report.net_value)
            else:
                val = prev_line[col] * base_values[col - 1]
            if base_values[col - 1] == 0.0 and val != 1.0:
                base_values[col - 1] = val
            if base_values[col - 1]:
                line.append(val / base_values[col - 1])
            else:
                line.append(1.0)
            col += 1
        for symbol in symbol_list:
            try:
                history = DayHistory.objects.filter(symbol=symbol, date=day_report.date)[0]
                val = float(history.close)
            except IndexError:
                val = None
            if base_values[col - 1] == 0.0 and val != 1.0:
                base_values[col - 1] = val
            if val is None:
                line.append('')
            elif base_values[col - 1]:
                line.append(val / base_values[col - 1])
            else:
                line.append(1.0)
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
        start_month = int(request.POST['start_date_month'])
        start_day = int(request.POST['start_date_day'])
        start_year = int(request.POST['start_date_year'])
        end_month = int(request.POST['end_date_month'])
        end_day = int(request.POST['end_date_day'])
        end_year = int(request.POST['end_date_year'])

        return redirect('/stock/report_range/%4.4d%2.2d%2.2d-%4.4d%2.2d%2.2d' % (start_year, start_month, start_day,
                                                                                 end_year, end_month, end_day))
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

    result = main.run()

    if result:
        return render(request, 'stock/success.txt', {})
    else:
        return render(request, 'stock/error.txt', {})


@csrf_exempt
def get_history_page(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')

    if ip != '127.0.0.1':
        return render(request, 'stock/error.txt', {})

    result = main.load_history_wsj(timezone.now().date())

    if result:
        return render(request, 'stock/success.txt', {})
    else:
        return render(request, 'stock/error.txt', {})


def simulate_page(request):
    if not request.user.is_authenticated:
        return redirect('/stock/')

    if request.method == 'POST':
        try:
            algorithm = int(request.POST['algorithm'])
        except ValueError:
            algorithm = None
        if algorithm is not None:
            logging.info('algorithm %d' % algorithm)
            for stock in Stock.objects.all():
                stock.algorithm = algorithm
                stock.save()

        try:
            stance = int(request.POST['stance'])
        except ValueError:
            stance = None
        if stance is not None:
            logging.info('stance %d' % stance)
            for stock in Stock.objects.all():
                stock.stance = stance
                stock.save()

        start_month = int(request.POST['start_date_month'])
        start_day = int(request.POST['start_date_day'])
        start_year = int(request.POST['start_date_year'])
        end_month = int(request.POST['end_date_month'])
        end_day = int(request.POST['end_date_day'])
        end_year = int(request.POST['end_date_year'])

        return redirect('/stock/run_sim/%4.4d%2.2d%2.2d-%4.4d%2.2d%2.2d' % (start_year, start_month, start_day,
                                                                            end_year, end_month, end_day))
    else:
        form = SimulateForm()
        return render(request, 'stock/simulate.html', {'form': form})


def test_page(request):
    if not request.user.is_authenticated:
        return redirect('/stock/')

    main.load_history_wsj(timezone.now().date())

    return render(request, 'stock/success.txt', {})


def run_sim_page(request, s_year, s_month, s_day, e_year, e_month, e_day):
    if not request.user.is_authenticated:
        return redirect('/stock/')

    start_dt = timezone.datetime(year=int(s_year), month=int(s_month), day=int(s_day))
    end_dt = timezone.datetime(year=int(e_year), month=int(e_month), day=int(e_day))

    res = main.simulate(start_dt.date(), end_dt.date())

    if res:
        return redirect('/stock/report_range/%4.4d%2.2d%2.2d-%4.4d%2.2d%2.2d' %
                        (start_dt.year, start_dt.month, start_dt.day,
                         end_dt.year, end_dt.month, end_dt.day))
    else:
        return render(request, 'stock/error.txt', {})

