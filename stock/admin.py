from django.contrib import admin
from .models import *


class TradeAdmin(admin.ModelAdmin):
    fields = ['date', 'account_id', 'symbol', 'type', 'price']
    ordering = ('-date',)


class StockInline(admin.TabularInline):
    model = Stock
    extra = 1
    fields = ['symbol', 'share', 'algorithm', 'stance']
    ordering = ('symbol',)


class AccountAdmin(admin.ModelAdmin):
    inlines = [StockInline]


admin.site.register(QuoteName)
admin.site.register(Account, AccountAdmin)
admin.site.register(Trade, TradeAdmin)
