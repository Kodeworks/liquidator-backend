from django.contrib import admin
from .models import Category, Transaction


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    search_fields = ('name', 'description')
    list_display = ('name', 'description')


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    search_fields = ('company', 'date', 'type', 'category')
    list_display = ('company', 'date', 'type', 'category', 'money')
