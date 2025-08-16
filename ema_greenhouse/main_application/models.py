from django.db import models
from django.contrib.auth.models import AbstractUser
from phonenumber_field.modelfields import PhoneNumberField
from django.db import models
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import User

class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)
    

class Users(AbstractUser):
    ROLE_CHOICES = [
        ('ema', 'EMA User'),
        ('policy', 'Policy Maker'),
        
    ]
    username = None
    email = models.EmailField(unique=True,null=True)
    phone_number = PhoneNumberField(null=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='ema')

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
   
    groups = models.ManyToManyField('auth.Group', related_name='Users_user_set', blank=True)
    user_permissions = models.ManyToManyField('auth.Permission', related_name='Users_user_set', blank=True)

    def __str__(self):
        return f"{self.email} ({self.get_role_display()})"


class Thresholds(models.Model):
    co2_threshold = models.FloatField(
        default=1000,
        help_text="Maximum CO₂ concentration in ppm"
    )
    ch4_threshold = models.FloatField(
        default=50,
        help_text="Maximum CH₄ concentration in ppm"
    )
    no2_threshold = models.FloatField(
        default=5,
        help_text="Maximum NO₂ concentration in ppm"
    )
    temperature = models.FloatField(
        default=28,
        help_text="Maximum temperature in °C"
    )
    humidity = models.FloatField(
        default=70,
        help_text="Maximum humidity percentage"
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Thresholds"
    
    def __str__(self):
        return "System Threshold Settings"


class Greenhouse(models.Model):
    
    region = models.CharField(max_length=50, choices=[
        ('harare', 'Harare'),
        ('bulawayo', 'Bulawayo'),
        ('mutare', 'Mutare')
    ])
    location = models.CharField(max_length=100)
    owner_name = models.CharField(max_length=100)
    owner_email = models.EmailField()
    owner_phone = models.CharField(max_length=20)
    esp32_id = models.CharField(max_length=50, unique=True) 
    
    def __str__(self):
        return f"{self.esp32_id} ({self.region})"

class SensorData(models.Model):
    greenhouse = models.ForeignKey(Greenhouse, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    co2 = models.FloatField(help_text="CO₂ ppm",null=True,blank=True) 
    ch4 = models.FloatField(help_text="CH₄ ppm",null=True,blank=True)
    nox = models.FloatField(help_text="NOₓ ppm",null=True,blank=True)
    temperature = models.FloatField(help_text="°C",null=True,blank=True)
    humidity = models.FloatField(help_text="%",null=True,blank=True)
   
    
    class Meta:
        ordering = ['-timestamp']

class Alert(models.Model):
    greenhouse = models.ForeignKey(Greenhouse, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    gas_type = models.CharField(max_length=10, choices=[
        ('CO2', 'Carbon Dioxide'),
        ('CH4', 'Methane'),
        ('NOX', 'Nitrogen Oxides')
    ])
    value = models.FloatField()
    threshold = models.FloatField()
    status = models.CharField(max_length=10, choices=[
        ('warning', 'Warning'),
        ('critical', 'Critical')
    ])
    resolved = models.BooleanField(default=False)
    class Meta:
        ordering = ['-timestamp']

