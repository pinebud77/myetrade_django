#!/usr/bin/env python3

import logging
import random
from . import models
from os.path import join, dirname, realpath
from .algorithms import TradeAlgorithm, buy_all, sell_all

try:
    import numpy as np
    import tensorflow as tf
    from tensorflow.python.saved_model import tag_constants
    no_tf = False
except ImportError:
    no_tf = True


ACTION_BUY = 0
ACTION_SELL = 1
ACTION_BUY_FAIL = 2
ACTION_SELL_FAIL = 3


logger = logging.getLogger('algorithms')
TF_STORE_FILE = join(dirname(realpath(__file__)), 'tf_model')


private_algorithm_list = []


DIRECTION_UP = 0
DIRECTION_DOWN = 1
DIRECTION_SIDE = 2


DTTT_MIN_HISTORY = 30
dttt_variables = [
    {'ud_count': 2, 'peak_count': 3, 'buy_rate': 0.6, 'days': 3},
    {'ud_count': 2, 'peak_count': 3, 'buy_rate': 0.5, 'days': 2},
    {'ud_count': 1, 'peak_count': 2, 'buy_rate': 0.4, 'days': 2},
]


class DTTTAlgorithm(TradeAlgorithm):
    name = 'DTTT'

    def trade_decision(self, stock):
        try:
            last_order = models.Order.objects.filter(symbol=stock.symbol).order_by('-dt')[0]
        except IndexError:
            last_order = None

        day_histories = models.DayHistory.objects.filter(symbol=stock.symbol).order_by('-date')[:DTTT_MIN_HISTORY]

        if len(day_histories) < DTTT_MIN_HISTORY:
            return 0

        logger.info('evaluating: %s - %d' % (stock.symbol, stock.count))

        ud_count = dttt_variables[stock.stance]['ud_count']
        peak_count = dttt_variables[stock.stance]['ud_count']
        buy_rate = dttt_variables[stock.stance]['buy_rate']
        days = dttt_variables[stock.stance]['days']

        peaks = []
        bottoms = []
        rates = []
        direction = DIRECTION_SIDE
        direction_count = 0
        for index in range(TT_MIN_HISTORY - 1):
            today = day_histories[index]
            yesterday = day_histories[index + 1]

            gap = today.high - today.low
            if gap > 0:
                rates.append(float(today.close - today.low) / gap)
            else:
                continue

            if today.close > yesterday.close:
                if direction != DIRECTION_UP:
                    if direction == DIRECTION_DOWN and direction_count >= ud_count:
                        bottoms.append(yesterday)
                    direction_count = 0
                direction_count += 1
                direction = DIRECTION_UP
            elif today.close < yesterday.close:
                if direction != DIRECTION_DOWN and direction_count >= ud_count:
                    if direction == DIRECTION_UP:
                        peaks.append(yesterday)
                    direction_count = 0
                direction_count += 1
                direction = DIRECTION_DOWN

        if not stock.count:
            for index in range(days):
                if rates[index] < buy_rate:
                    logger.debug('no buy - not enough up force')
                    return 0
            logger.debug('buy')
            return buy_all(stock)

        if len(peaks) >= peak_count + 1:
            if last_order is not None and peaks[1].date <= last_order.dt.date():
                logger.debug('position: hold - not enough data')
                return 0
            for n in range(peak_count):
                if peaks[n].close >= peaks[n + 1].close:
                    logger.debug('position: hold - there is up history')
                    return 0
            return -stock.count
        elif day_histories[0].close < day_histories[1].close:
            logger.debug('position: sell.. no peak down turn')
            return -stock.count

        return 0


TT_MIN_HISTORY = 15
tt_variables = [
    {'up_count': 3, 'down_count': 3},
    {'up_count': 2, 'down_count': 2},
    {'up_count': 1, 'down_count': 1},
]


class TrendTrendAlgorithm(TradeAlgorithm):
    name = 'TrendTrend'

    def trade_decision(self, stock):
        try:
            last_order = models.Order.objects.filter(symbol=stock.symbol).order_by('-dt')[0]
        except IndexError:
            last_order = None

        day_histories = models.DayHistory.objects.filter(symbol=stock.symbol).order_by('-date')[:TT_MIN_HISTORY]

        if len(day_histories) < TT_MIN_HISTORY:
            return 0

        logger.info('evaluating: %s - %d' % (stock.symbol, stock.count))

        up_count = tt_variables[stock.stance]['up_count']
        down_count = tt_variables[stock.stance]['down_count']

        peaks = []
        bottoms = []
        direction = DIRECTION_SIDE
        direction_count = 0
        for index in range(TT_MIN_HISTORY - 1):
            today = day_histories[index]
            yesterday = day_histories[index + 1]

            if today.close > yesterday.close:
                if direction != DIRECTION_UP:
                    if direction == DIRECTION_DOWN and direction_count >= down_count:
                        bottoms.append(yesterday)
                    direction_count = 0
                direction_count += 1
                direction = DIRECTION_UP
            elif today.close < yesterday.close:
                if direction != DIRECTION_DOWN and direction_count >= up_count:
                    if direction == DIRECTION_UP:
                        peaks.append(yesterday)
                    direction_count = 0
                direction_count += 1
                direction = DIRECTION_DOWN

        if not stock.count:
            if len(peaks) < 2 and day_histories[0].close > day_histories[1].close:
                logger.debug('position: buy no peak but increasing')
                return buy_all(stock)
            if len(bottoms) >= 2:
                if last_order is not None and bottoms[0].date <= last_order.dt.date():
                    logger.debug('position: hold - not enough data')
                    return 0
                if bottoms[0].close > bottoms[1].close:
                    logger.debug('position: buy - bottom over bottom')
                    return buy_all(stock)
            logger.debug('position: hold - no matching rule')
            return 0

        if len(peaks) < 2 and day_histories[0].close < day_histories[1].close:
            logger.debug('position: sell - no bottoms but decreasing')
            return -stock.count

        if len(peaks) >= 2:
            if last_order is not None and peaks[0].date <= last_order.dt.date():
                logger.debug('position: hold - not enough data')
                return 0
            if peaks[0].close < peaks[1].close:
                logger.debug('position: sell - peak under peak')
                return -stock.count

        return 0


OC_MIN_HISTORY = 5
oc_variables = [
    {'meaningful_rate': 0.6, 'up_repeat': 3, 'down_repeat': 3},
    {'meaningful_rate': 0.5, 'up_repeat': 2, 'down_repeat': 2},
    {'meaningful_rate': 0.4, 'up_repeat': 1, 'down_repeat': 1},
]


class OpenCloseAlgorithm(TradeAlgorithm):
    name = 'OpenClose'

    def trade_decision(self, stock):
        day_histories = models.DayHistory.objects.filter(symbol=stock.symbol).order_by('-date')[:OC_MIN_HISTORY]
        if len(day_histories) < OC_MIN_HISTORY:
            logger.error('not enough history')
            return 0

        meaningful_rate = oc_variables[stock.stance]['meaningful_rate']
        up_repeat = oc_variables[stock.stance]['up_repeat']
        down_repeat = oc_variables[stock.stance]['down_repeat']

        rates = []
        for day_history in day_histories:
            gap = (day_history.high - day_history.low)
            if gap == 0:
                continue

            rates.append((day_history.close - day_history.open) / gap)

        if not stock.count:
            for index in range(up_repeat):
                if abs(rates[index]) < meaningful_rate:
                    logger.debug('position: hold - not meaningful rate %f' % rates[index])
                    return 0
                if rates[index] < 0:
                    logger.debug('position: hold - not enough up_repeat')
                    return 0
            logger.debug('position: buy')
            return buy_all(stock)

        for index in range(down_repeat):
            if abs(rates[index]) < meaningful_rate:
                logger.debug('position: hold - not meaningful rate %f' % rates[index])
                return 0
            if rates[index] > 0:
                logger.debug('position: hold - not enough down_repeat')
                return 0

        logger.debug('position: sell')
        return -stock.count


OCT_MIN_HISTORY = 7
oct_variables = (
    {'prev_down_count': 3, 'monitor_count': 3, 'sell_rate': 0.2},
    {'prev_down_count': 2, 'monitor_count': 2, 'sell_rate': 0.0},
    {'prev_down_count': 1, 'monitor_count': 1, 'sell_rate': -0.2},
)


class OCTrendAlgorithm(TradeAlgorithm):
    name = 'OCTrend'

    def trade_decision(self, stock):
        day_histories = models.DayHistory.objects.filter(symbol=stock.symbol).order_by('-date')[:OCT_MIN_HISTORY]
        if len(day_histories) < OCT_MIN_HISTORY:
            logger.debug('not enough history')
            return 0

        prev_down_count = oct_variables[stock.stance]['prev_down_count']
        monitor_count = oct_variables[stock.stance]['monitor_count']
        sell_rate = oct_variables[stock.stance]['sell_rate']

        rates = list()
        for day_history in day_histories:
            day_gap = day_history.high - day_history.low
            if day_gap == 0.0:
                logger.debug('huh? day gap is 0?')
                continue
            open_close_gap = day_history.close - day_history.open
            rates.append(open_close_gap / day_gap)

        logger.debug(rates)

        if not stock.count:
            if rates[0] > 0:
                for index in range(1, prev_down_count + 1):
                    if rates[index] > 0:
                        logger.debug('position: hold not enough down count before up')
                        return 0
                logger.debug('position: buy')
                return buy_all(stock)

            logger.debug('position: hold - day rate negative')
            return 0

        if rates[0] < 0:
            for index in range(monitor_count):
                if rates[index] > 0:
                    return 0
            return -stock.count

        logger.debug('position: hold - day rate positive')

        return 0


dt_variables = [
    {'buy_rate': 0.0010, 'sell_rate': -0.0010, 'days': 4},     # conservative
    {'buy_rate': 0.0008, 'sell_rate': -0.0008, 'days': 2},     # moderate
    {'buy_rate': 0.0006, 'sell_rate': -0.0006, 'days': 2},     # aggresive
]


class DayTrendAlgorithm(TradeAlgorithm):
    name = 'DayTrend'

    def trade_decision(self, stock):
        logger.debug('evaluating: %s' % stock.symbol)

        buy_rate = dt_variables[stock.stance]['buy_rate']
        sell_rate = dt_variables[stock.stance]['sell_rate']
        days = dt_variables[stock.stance]['days']

        try:
            day_histories = models.DayHistory.objects.filter(symbol=stock.symbol).order_by('-date')[:days]
        except IndexError:
            return 0

        if len(day_histories) < days:
            logger.error('not enough history')
            return 0

        rates = []
        for day_history in day_histories:
            center = (day_history.high + day_history.low) / 2
            rates.append((day_history.close - center) / day_history.low)

        logger.debug('rates: ' + str(rates))

        if not stock.count:
            for rate in rates:
                if rate <= buy_rate:
                    logger.debug('no buy')
                    return 0
            logger.debug('buy')
            return buy_all(stock)

        for rate in rates:
            if rate >= sell_rate:
                logger.debug('no sell')
                return 0

        logger.debug('sell')
        return -stock.count


adt_variables = [
    {'one_buy_rate': 0.010, 'one_sell_rate': -0.010, 'buy_rate': 0.0006, 'sell_rate': -0.0000, 'days': 3},     # conservative
    {'one_buy_rate': 0.008, 'one_sell_rate': -0.008, 'buy_rate': 0.0004, 'sell_rate': -0.0000, 'days': 2},     # moderate
    {'one_buy_rate': 0.006, 'one_sell_rate': -0.006, 'buy_rate': 0.0003, 'sell_rate': -0.0000, 'days': 2},     # aggresive
]


class AggDTAlgorithm(TradeAlgorithm):
    name = 'AggDT'

    def trade_decision(self, stock):
        one_buy_rate = adt_variables[stock.stance]['one_buy_rate']
        one_sell_rate = adt_variables[stock.stance]['one_sell_rate']
        buy_rate = adt_variables[stock.stance]['buy_rate']
        sell_rate = adt_variables[stock.stance]['sell_rate']
        days = adt_variables[stock.stance]['days']

        try:
            day_histories = models.DayHistory.objects.filter(symbol=stock.symbol).order_by('-date')[:days]
        except IndexError:
            return 0

        if len(day_histories) < days:
            logger.error('not enough history')
            return 0

        rates = list()
        for day_history in day_histories:
            center = (day_history.high + day_history.low) / 2
            rates.append((day_history.close - center) / day_history.low)

        logger.debug('rates: ' + str(rates))

        if not stock.count:
            if rates[0] >= one_buy_rate:
                logger.debug('buy by one_rate')
                return buy_all(stock)
            for rate in rates:
                if rate <= buy_rate:
                    logger.debug('no buy')
                    return 0
            logger.debug('buy')
            return buy_all(stock)

        if rates[0] <= one_sell_rate:
            logger.debug('sell by one_rate')
            return -stock.count

        for rate in rates:
            if rate >= sell_rate:
                logger.debug('no sell')
                return 0

        logger.debug('sell')
        return -stock.count


class AggTwoAlgorithm(TradeAlgorithm):
    name = 'AggTwo'

    def trade_decision(self, stock):
        one_buy_rate = adt_variables[stock.stance]['one_buy_rate']
        one_sell_rate = adt_variables[stock.stance]['one_sell_rate']
        buy_rate = adt_variables[stock.stance]['buy_rate']
        sell_rate = adt_variables[stock.stance]['sell_rate']
        days = adt_variables[stock.stance]['days']

        try:
            day_histories = models.DayHistory.objects.filter(symbol=stock.symbol).order_by('-date')[:days]
        except IndexError:
            return 0

        if len(day_histories) < days:
            logger.error('not enough history')
            return 0

        rates = list()
        yesterday = day_histories[0]

        center = (yesterday.high + yesterday.low) / 2
        rates.append((stock.value - center) / yesterday.low)

        for n in range(len(day_histories) - 1):
            today = day_histories[n]
            yesterday = day_histories[n+1]

            center = (yesterday.high + yesterday.low) / 2
            rates.append((today.open - center) / yesterday.low)

        logger.debug('rates: ' + str(rates))

        if not stock.count:
            if rates[0] >= one_buy_rate:
                logger.debug('buy by one_rate')
                return buy_all(stock)
            for rate in rates:
                if rate <= buy_rate:
                    logger.debug('no buy')
                    return 0
            logger.debug('buy')
            return buy_all(stock)

        if rates[0] <= one_sell_rate:
            logger.debug('sell by one_rate')
            return -stock.count

        for rate in rates:
            if rate >= sell_rate:
                logger.debug('no sell')
                return 0

        logger.debug('sell')
        return -stock.count


ra_variables = (
    {'days': 7},     # conservative
    {'days': 6},     # moderate
    {'days': 5},     # aggressive
)


class RAvgAlgorithm(TradeAlgorithm):
    name = 'RAvg'

    def trade_decision(self, stock):
        days = ra_variables[stock.stance]['days']

        try:
            day_histories = models.DayHistory.objects.filter(symbol=stock.symbol).order_by('-date')[:days]
        except IndexError:
            return 0

        if len(day_histories) < days:
            logger.error('not enough history')
            return 0

        total = 0.0
        start_open = day_histories[days - 1].open
        weight = 1
        a = 0.05
        weight_sum = 0.0
        times = 0
        for day_history in day_histories:
            total += day_history.open * weight
            weight_sum += weight
            times += 1
            weight = pow(1 - a, times)

        diff = total / weight_sum - start_open

        logger.debug('diff = %f' % diff)

        if not stock.count:
            if diff >= 0.0:
                logger.debug('buy')
                return buy_all(stock)
            logger.debug('hold: empty stock')
            return 0

        if diff <= 0.0:
            logger.debug('sell')
            return -stock.count

        logger.debug('hold: keep stocks')
        return 0


alg_sess = None
alg_x = None
alg_outputs = None
ml_variables = (
    {'threshold': 0.006},      # conservative
    {'threshold': 0.004},      # moderate
    {'threshold': 0.002},      # aggressive
)

n_steps = 20
n_inputs = 2
n_neurons = 150
n_outputs = n_inputs


def next_batch(sample_list, batch_size, steps):
    batch_list = list()
    for n in range(batch_size):
        line = list()

        sample = random.choice(sample_list)
        open_list = sample[0]
        volume_list = sample[1]

        start = random.randint(0, len(open_list) - steps - 2)
        start_volume = volume_list[start]
        if not start_volume:
            logger.warning('volume or price is 0 in training data')
            continue

        batch_list.append(line)
        for i in range(steps + 1):
            line.append((open_list[start + i], volume_list[start + i] / start_volume,))

    batch_array = np.array(batch_list)
    global n_inputs

    return batch_array[:, :-1].reshape(-1, steps, n_inputs), batch_array[:, 1:].reshape(-1, steps, n_inputs)


def tf_learn(start_date, end_date):
    if no_tf:
        return None

    symbol_list = list()
    symbols = models.SimHistory.objects.all().values('symbol').distinct()
    for symbol_dict in symbols:
        symbol_list.append(symbol_dict['symbol'])

    global n_steps, n_inputs, n_neurons, n_outputs

    learning_rate = 0.0001
    n_iterations = 10000
    batch_size = 50

    tf.reset_default_graph()

    x = tf.placeholder(tf.float32, [None, n_steps, n_inputs], 'x')
    y = tf.placeholder(tf.float32, [None, n_steps, n_outputs], 'y')

    cell = tf.contrib.rnn.OutputProjectionWrapper(tf.contrib.rnn.BasicRNNCell(num_units=n_neurons,
                                                                              activation=tf.nn.relu),
                                                  output_size=n_outputs)
    outputs, states = tf.nn.dynamic_rnn(cell, x, dtype=tf.float32)

    weights = tf.constant([[[1.0, 0]] * n_steps])
    loss = tf.losses.mean_squared_error(outputs, y, weights=weights)
    optimizer = tf.train.AdamOptimizer(learning_rate=learning_rate)
    training_op = optimizer.minimize(loss)

    sess = tf.Session()
    init_op = tf.group(tf.global_variables_initializer(),
                       tf.local_variables_initializer())
    sess.run(init_op)

    sample_list = list()
    for symbol in symbol_list:
        print('loading %s' % symbol)
        open_list = list()
        volume_list = list()

        sim_histories = models.SimHistory.objects.filter(symbol=symbol,
                                                         date__gte=start_date,
                                                         date__lte=end_date).order_by('date')
        for n in range(1, len(sim_histories)):
            today = sim_histories[n]
            yesterday = sim_histories[n-1]
            open_list.append((today.open - yesterday.open) / yesterday.open)
            volume_list.append(yesterday.volume)

        if len(open_list) < n_steps + 1:
            logger.error('price data is not enough')
            continue

        sample_list.append((open_list, volume_list,))

    for iteration in range(n_iterations):
        x_batch, y_batch = next_batch(sample_list, batch_size, n_steps)

        sess.run(training_op, feed_dict={x: x_batch, y: y_batch})
        if iteration % 100 == 0:
            mse = loss.eval(feed_dict={x: x_batch, y: y_batch}, session=sess)
            print('%d\tMSE:%f' % (iteration, mse))
            x_batch_re = x_batch[0].reshape(-1, n_steps, n_inputs)
            o = sess.run(outputs, feed_dict={x: x_batch_re})
            y_batch_re = y_batch[0].reshape(-1, n_steps, n_inputs)
            print('\tsample: real %f, pred %f, error %f' % (y_batch_re[0][-1][0],
                                                    o[0][-1][0],
                                                    y_batch_re[0][-1][0] - o[0][-1][0]))

    saver = tf.train.Saver()
    saver.save(sess, TF_STORE_FILE)

    global alg_sess, alg_x, alg_outputs
    alg_sess = sess
    alg_x = x
    alg_outputs = outputs

    logger.info('loaded learning set')


class MLAlgorithm(TradeAlgorithm):
    name = 'MachineLearning'

    def trade_decision(self, stock):
        logger.debug('evaluating: %s' % stock.symbol)
        global n_steps
        try:
            histories = models.DayHistory.objects.filter(symbol=stock.symbol).order_by('-date')[:n_steps]
        except IndexError:
            logger.error('no history')
            return 0

        if len(histories) < n_steps:
            logger.error('no history')
            return 0

        threshold = ml_variables[stock.stance]['threshold']

        open_list = list()
        volume_list = list()
        start_volume = histories[n_steps-1].volume
        open_list.append((stock.value - histories[0].open) / histories[0].open)
        for n in range(len(histories) + 1):
            today = histories[n]
            volume_list.append(today.volume / start_volume)
            if n == len(histories) - 1:
                break
            yesterday = histories[n+1]
            open_list.append((today.open - yesterday.open) / yesterday.open)

        x_list = list()
        for n in range(len(open_list)):
            x_list.append((open_list[n], volume_list[n],))

        global n_inputs, n_neurons
        global alg_x, alg_outputs, alg_sess

        if alg_sess is None:
            tf.reset_default_graph()
            alg_x = tf.placeholder(tf.float32, [None, n_steps, n_inputs], 'x')
            cell = tf.contrib.rnn.OutputProjectionWrapper(tf.contrib.rnn.BasicRNNCell(num_units=n_neurons,
                                                                                      activation=tf.nn.relu),
                                                          output_size=n_outputs)
            alg_outputs, states = tf.nn.dynamic_rnn(cell, alg_x, dtype=tf.float32)

            alg_sess = tf.Session()
            init_op = tf.group(tf.global_variables_initializer(),
                               tf.local_variables_initializer())
            alg_sess.run(init_op)
            saver = tf.train.Saver()
            saver.restore(alg_sess, TF_STORE_FILE)

        x_new = np.array(x_list)
        x_new = np.flip(x_new, 0)
        x_new = x_new.reshape(-1, n_steps, n_inputs)
        res = alg_sess.run(alg_outputs, feed_dict={alg_x: x_new})

        y_gap = res[0][-1][0] - res[0][-2][0]
        logger.debug('prediction: %f' % y_gap)

        if not stock.count and y_gap > threshold:
            logger.debug('buy')
            return buy_all(stock)

        if stock.count and y_gap < -threshold:
            logger.debug('sell')
            return -stock.count

        return 0


daytrade_variables = (
    {'in_rate': 0.998},     # conservative
    {'in_rate': 0.999},     # moderate
    {'in_rate': 1.000},     # aggressive
)


class DayTradeAlgorithm(TradeAlgorithm):
    name = 'DayTrade'

    def trade_decision(self, stock):
        in_rate = daytrade_variables[stock.stance]['in_rate']

        logger.debug('evaluating: ' + stock.symbol)

        try:
            history = models.DayHistory.objects.filter(symbol=stock.symbol).order_by('-date')[0]
            prev_price = history.open
        except IndexError:
            logger.debug('no history yet')
            prev_price = stock.value

        if not stock.count:
            if stock.value < prev_price * in_rate:
                return buy_all(stock)
            else:
                return 0
        else:
            return sell_all(stock)


AHNYUNG_DAYS = 10
ahnyung_variables = (
    {'in_rate': 0.980, 'out_rate': 1.020},    # conservative
    {'in_rate': 0.990, 'out_rate': 1.010},    # moderate
    {'in_rate': 0.995, 'out_rate': 1.005},    # aggressive
)


class AhnyungAlgorithm(TradeAlgorithm):
    name = 'Ahnyung'

    def trade_decision(self, stock):
        in_rate = ahnyung_variables[stock.stance]['in_rate']
        out_rate = ahnyung_variables[stock.stance]['out_rate']

        logger.debug('evaluating: ' + stock.symbol)

        try:
            prev_order = models.Order.objects.filter(symbol=stock.symbol,
                                                     account_id=stock.account.id,
                                                     action=ACTION_BUY).order_by('-dt')[0]
            prev_buy = prev_order.price
        except IndexError:
            logger.debug('buy: no previous order')
            prev_buy = stock.value

        histories = models.DayHistory.objects.filter(symbol=stock.symbol).order_by('-date')
        if not histories:
            logger.info('no previous price history')
            return 0

        if len(histories) > AHNYUNG_DAYS:
            histories = histories[:AHNYUNG_DAYS]

        if stock.count:
            if stock.value > prev_buy * out_rate:
                return sell_all(stock)
            else:
                return 0

        top_price = stock.value
        for history in histories:
            if history.open > top_price:
                top_price = history.open
            else:
                break

        if top_price * in_rate > stock.value:
            return buy_all(stock)

        return 0


private_algorithm_list.append(AhnyungAlgorithm)
