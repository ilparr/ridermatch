from django.db import models
from django.contrib.auth.models import User

class Rider(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    telegram_id = models.BigIntegerField(unique=True)
    phone = models.CharField(max_length=15)
    transport_type = models.CharField(max_length=20, choices=[
        ('bike', 'Bicicletta'),
        ('scooter', 'Scooter'),
        ('car', 'Auto')
    ])
    max_distance_km = models.IntegerField(default=10)
    is_active = models.BooleanField(default=True)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=5.00)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name}"

class RiderAvailability(models.Model):
    rider = models.ForeignKey(Rider, on_delete=models.CASCADE)
    day_of_week = models.IntegerField(choices=[
        (0, 'Lunedì'), (1, 'Martedì'), (2, 'Mercoledì'),
        (3, 'Giovedì'), (4, 'Venerdì'), (5, 'Sabato'), (6, 'Domenica')
    ])
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_preferred = models.BooleanField(default=False)

    class Meta:
        unique_together = ['rider', 'day_of_week', 'start_time']