from django.contrib import admin
from .models import  *



admin.site.register(Users)
admin.site.register(Greenhouse)
admin.site.register(Thresholds)
admin.site.register(SensorData)