from django.contrib import admin
from .models import Rider, RiderAvailability

@admin.register(Rider)
class RiderAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone', 'transport_type', 'rating', 'is_active']
    list_filter = ['transport_type', 'is_active', 'created_at']
    search_fields = ['user__first_name', 'user__last_name', 'phone']

@admin.register(RiderAvailability)
class RiderAvailabilityAdmin(admin.ModelAdmin):
    list_display = ['rider', 'day_of_week', 'start_time', 'end_time', 'is_preferred']
    list_filter = ['day_of_week', 'is_preferred']