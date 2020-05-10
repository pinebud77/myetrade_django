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
