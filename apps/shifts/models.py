from django.db import models

class Shift(models.Model):
    STATUS_CHOICES = [
        ('open', 'Aperto'),
        ('assigned', 'Assegnato'),
        ('confirmed', 'Confermato'),
        ('completed', 'Completato'),
        ('cancelled', 'Cancellato')
    ]
    
    pizzeria = models.ForeignKey('pizzerias.Pizzeria', on_delete=models.CASCADE)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    hourly_rate = models.DecimalField(max_digits=6, decimal_places=2)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.pizzeria.name} - {self.date} {self.start_time}"

class ShiftAssignment(models.Model):
    shift = models.OneToOneField(Shift, on_delete=models.CASCADE)
    rider = models.ForeignKey('riders.Rider', on_delete=models.CASCADE)
    assigned_at = models.DateTimeField(auto_now_add=True)
    confirmed_by_rider = models.BooleanField(default=False)
    confirmed_by_pizzeria = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.rider} -> {self.shift}"