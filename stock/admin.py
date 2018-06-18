from django.contrib import admin
from .models import *


class TradeAdmin(admin.ModelAdmin):
    fields = ['date', 'account_id', 'symbol', 'action', 'price']
    ordering = ('-date',)


class StockInline(admin.TabularInline):
    model = Stock
    extra = 1
    fields = ['symbol', 'share', 'algorithm', 'stance']
    ordering = ('symbol',)


class AccountAdmin(admin.ModelAdmin):
    inlines = [StockInline]


class SimQuoteAdmin(admin.ModelAdmin):
    ordering = ('-date', 'symbol',)


class DayReportAdmin(admin.ModelAdmin):
    ordering = ('-date', 'account_id')


admin.site.register(Quote)
admin.site.register(SimQuote, SimQuoteAdmin)
admin.site.register(Stock)
admin.site.register(Account, AccountAdmin)
admin.site.register(Trade, TradeAdmin)
admin.site.register(DayReport, DayReportAdmin)
