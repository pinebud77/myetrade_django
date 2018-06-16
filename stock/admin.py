from django.contrib import admin
from .models import *


class StockInline(admin.TabularInline):
    model = Stock
    extra = 1
    fields = ['symbol', 'share', 'algorithm', 'stance']


class AccountAdmin(admin.ModelAdmin):
    inlines = [StockInline]


admin.site.register(Account, AccountAdmin)
