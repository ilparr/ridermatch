from django.contrib import admin
from django.urls import path
from django.http import JsonResponse

def health_check(request):
    """Health check endpoint"""
    return JsonResponse({
        'status': 'healthy',
        'service': 'RiderMatch',
        'version': '1.0.0'
    })

urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/', health_check, name='health_check'),
]

# Custom admin site configuration
admin.site.site_header = "RiderMatch Administration"
admin.site.site_title = "RiderMatch Admin"
admin.site.index_title = "Benvenuto nell'admin di RiderMatch"