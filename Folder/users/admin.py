from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from users.models import User

# Register your models here.

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'sur_name', 'is_staff', 'is_active')
    list_filter = ('is_staff', 'is_active', 'is_superuser')
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Дополнительные поля', {'fields': ('sur_name', 'image')}),
    )
    
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Дополнительные поля', {'fields': ('sur_name', 'image')}),
    )