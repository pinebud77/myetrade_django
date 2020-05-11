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

from django.contrib import admin
from .models import *


class OrderAdmin(admin.ModelAdmin):
    fields = ['dt', 'account_id', 'symbol', 'action', 'price', 'count']
    ordering = ('-dt',)


class StockInline(admin.TabularInline):
    model = Stock
    extra = 1
    fields = ['symbol', 'share', 'in_algorithm', 'in_stance', 'out_algorithm', 'out_stance']
    ordering = ('symbol',)


class AccountAdmin(admin.ModelAdmin):
    inlines = [StockInline]


class SimHistoryAdmin(admin.ModelAdmin):
    ordering = ('-date', 'symbol',)


class DayHistoryAdmin(admin.ModelAdmin):
    ordering = ('-date', 'symbol',)


class DayReportAdmin(admin.ModelAdmin):
    ordering = ('-date', 'account_id')


admin.site.register(OrderID)
admin.site.register(Quote)
admin.site.register(Stock)
admin.site.register(DayHistory, DayHistoryAdmin)
admin.site.register(SimHistory, SimHistoryAdmin)
admin.site.register(Account, AccountAdmin)
admin.site.register(Order, OrderAdmin)
admin.site.register(DayReport, DayReportAdmin)
