import logging
import csv
import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt
import mpld3
from . import main
from python_simtrade import load_history
from .forms import *
from .models import *
from django.contrib.auth import authenticate, login, logout
from django.template import loader, Context
from django.shortcuts import redirect, render
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from os.path import realpath, dirname

CUR_DIR = dirname(realpath(__file__))


def get_report_list(start_date, end_date):
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

    day = timezone.timedelta(1)
    date = start_date
    while date <= end_date:
        line = list()
        line.append('%d/%d/%d' % (date.month, date.day, date.year))
        col = 1
        for account_id in account_id_list:
            try:
                day_report = DayReport.objects.filter(account_id=account_id, date=date)[0]
                val = float(day_report.net_value)
            except IndexError:
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
                history = DayHistory.objects.filter(symbol=symbol, date__lte=date).order_by('-date')[0]
                val = float(history.open)
            except IndexError:
                val = None
            if base_values[col - 1] == 0.0 and val != 1.0 and val is not None:
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
        date += day

    legends = ['date']
    for account_id in account_id_list:
        legends.append('account: %d' % account_id)
    legends += symbol_list

    return legends, report_list


def get_html_fig(legends, report_list):
    data_list = list()
    for legend in legends:
        data_list.append(list())

    for line in report_list:
        for n in range(len(line)):
            if n == 0:
                spl = line[n].split('/')
                date = timezone.datetime(year=int(spl[2]), month=int(spl[0]), day=int(spl[1])).date()
                data_list[0].append(date)
            else:
                if line[n]:
                    data_list[n].append(line[n])
                else:
                    data_list[n].append(None)

    mpl.rcParams['axes.edgecolor'] = 'black'
    mpl.rcParams['axes.facecolor'] = 'white'
    mpl.rcParams['figure.facecolor'] = 'white'
    mpl.rcParams['figure.edgecolor'] = 'white'
    mpl.rcParams['figure.autolayout'] = 'True'
    mpl.rcParams['axes.formatter.use_locale'] = 'True'
    mpl.rcParams['savefig.edgecolor'] = 'white'
    mpl.rcParams['savefig.facecolor'] = 'white'

    fig, ax = plt.subplots()

    font = {'size': 10}
    mpl.rc('font', **font)
    fig.patch.set_alpha(1)

    for n in range(1, len(data_list)):
        ax.plot_date(data_list[0], data_list[n], linestyle='solid', marker='', label=legends[n])
    ax.grid(True)
    legend = ax.legend(loc='upper left', shadow=True)
    frame = legend.get_frame()
    frame.set_facecolor('0.90')

    fig.autofmt_xdate()
    fig_html = mpld3.fig_to_html(fig)

    return fig_html


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
            return render('stock/nouser.html')
        if not user.is_active:
            return render('stock/inact_user.html')

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

    legends, report_list = get_report_list(start_dt.date(), end_dt.date())

    filename = 'report_%d%2.2d%2.2d_%d%2.2d%2.2d.csv' % (start_dt.year, start_dt.month, start_dt.day,
                                                         end_dt.year, end_dt.month, end_dt.day)
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="%s"' % filename

    writer = csv.writer(response)
    writer.writerow(legends)

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

    main.load_history(timezone.now().date())

    result = main.run()
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

        start_date = timezone.datetime(year=start_year, month=start_month, day=start_day).date()
        end_date = timezone.datetime(year=end_year, month=end_month, day=end_day).date()

        main.simulate(start_date, end_date)

        form = SimulateForm(initial={'start_date': start_date,
                                     'end_date': end_date,
                                     'algorithm': algorithm,
                                     'stance': stance})
        legends, report_list = get_report_list(start_date, end_date)
        fig_html = get_html_fig(legends, report_list)
        report_url = '%4.4d%2.2d%2.2d-%4.4d%2.2d%2.2d' % (start_date.year, start_date.month, start_date.day,
                                                          end_date.year, end_date.month, end_date.day)
        if report_list:
            body_list = list()
            body_list.append(report_list[-1][0])
            for f_value in report_list[-1][1:]:
                if f_value:
                    body_list.append('%.3f' % f_value)
                else:
                    body_list.append('')
        else:
            body_list = None

        return render(request, 'stock/simulate.html', {'form': form,
                                                       'figure': fig_html,
                                                       'report_url': report_url,
                                                       'head_list': legends,
                                                       'body_list': body_list})
    else:
        form = SimulateForm()
        return render(request, 'stock/simulate.html', {'form': form, 'figure': None})


def test_page(request):
    if not request.user.is_authenticated:
        return redirect('/stock/')

    main.load_history_wsj(timezone.now().date())

    return render(request, 'stock/success.txt', {})


def graph_page(request):
    if not request.user.is_authenticated:
        return redirect('/stock/')

    if request.method == 'POST':
        end_year = int(request.POST['end_date_year'])
        end_month = int(request.POST['end_date_month'])
        end_day = int(request.POST['end_date_day'])
        days = int(request.POST['days'])
        end_date = timezone.datetime(year=end_year, month=end_month, day=end_day)
    else:
        end_date = timezone.now().date()
        days = 30
    start_date = end_date - timezone.timedelta(days)

    initial_dict = dict()
    initial_dict['end_date'] = end_date
    initial_dict['days'] = '%d' % days
    form = GraphRangeForm(initial=initial_dict)

    legends, report_list = get_report_list(start_date, end_date)
    fig_html = get_html_fig(legends, report_list)
    report_url = '%4.4d%2.2d%2.2d-%4.4d%2.2d%2.2d' % (start_date.year, start_date.month, start_date.day,
                                                      end_date.year, end_date.month, end_date.day)
    if report_list:
        body_list = list()
        body_list.append(report_list[-1][0])
        for f_value in report_list[-1][1:]:
            if f_value:
                body_list.append('%.3f' % f_value)
            else:
                body_list.append('')
    else:
        body_list = None

    return render(request, 'stock/graph.html', {'form': form,
                                                'figure': fig_html,
                                                'report_url': report_url,
                                                'head_list': legends,
                                                'body_list': body_list})


def learn_page(request):
    if not request.user.is_authenticated:
        return redirect('/stock/')

    if request.method == 'POST':
        start_month = int(request.POST['start_date_month'])
        start_day = int(request.POST['start_date_day'])
        start_year = int(request.POST['start_date_year'])
        end_month = int(request.POST['end_date_month'])
        end_day = int(request.POST['end_date_day'])
        end_year = int(request.POST['end_date_year'])

        start_date = timezone.datetime(year=start_year, month=start_month, day=start_day).date()
        end_date = timezone.datetime(year=end_year, month=end_month, day=end_day).date()

        main.learn(start_date, end_date)

        initial_dict = dict()
        initial_dict['start_date'] = start_date
        initial_dict['end_date'] = end_date

        form = LearnForm(initial=initial_dict)
    else:
        form = LearnForm()

    return render(request, 'stock/learn.html', {'form': form})
