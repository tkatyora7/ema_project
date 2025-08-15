from django.shortcuts import render , redirect
from django.contrib.auth import authenticate, login ,logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.csrf import csrf_protect
from django.shortcuts import render, redirect
from django.utils import timezone
import datetime
import os
import json
from .models import *
from django.conf import settings
from django.core.mail import send_mail
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from .models import Greenhouse, SensorData, Thresholds, Alert
from django.db.models import Avg
from datetime import datetime, timedelta



@csrf_protect
def sign_in(request):
    if request.user.is_authenticated:
        return redirect_user_dashboard(request.user)  

    if request.method == 'POST':
        email = request.POST.get('email')  
        password = request.POST.get('password')  

        if email and password:  
            user = authenticate(request=request, username=email, password=password)  
            if user is not None:
                if user.is_active:
                    login(request, user)  
                    messages.success(request, 'Successfully logged in!') 
                    return redirect_user_dashboard(user)  
                else:
                    messages.error(request, 'Your account is inactive.')
            else:
                messages.error(request, 'Invalid email or password.')
        else:
            messages.error(request, 'Please fill in both email and password.')
            
    return render(request, 'login.html')
    
def redirect_user_dashboard(user):
    """Redirect user based on their role"""
    if user.role == 'ema':
        return redirect('ema_dashboard')
    elif user.role == 'policy':
        return redirect('policy_dashboard')
    else:
        return redirect('no_dashboard')
def signout(request):
    logout(request)
    messages.success(request,'Logged Out Succefully.')
    return redirect('login')



@login_required
def ema_dashboard(request):

    averages = SensorData.objects.aggregate(
        avg_co2=Avg('co2'),
        avg_ch4=Avg('ch4'),
        avg_nox=Avg('nox'),
        avg_temp=Avg('temperature'),
        avg_humidity=Avg('humidity')
    )
    
    selected_greenhouse = None
    
   
    if 'q' in request.GET:
        search_query = request.GET.get('q', '').strip()
        
      
        if search_query:
            selected_greenhouse = Greenhouse.objects.filter(
                models.Q(esp32_id__icontains=search_query) |
                models.Q(location__icontains=search_query)
            ).first()
            
            if selected_greenhouse:
               
                greenhouse_avg = SensorData.objects.filter(
                    greenhouse=selected_greenhouse
                ).aggregate(
                    avg_co2=Avg('co2'),
                    avg_ch4=Avg('ch4'),
                    avg_nox=Avg('nox'),
                    avg_temp=Avg('temperature'),
                    avg_humidity=Avg('humidity')
                )
                
              
                selected_greenhouse.avg_co2 = greenhouse_avg['avg_co2']
                selected_greenhouse.avg_ch4 = greenhouse_avg['avg_ch4']
                selected_greenhouse.avg_nox = greenhouse_avg['avg_nox']
                selected_greenhouse.avg_temp = greenhouse_avg['avg_temp']
                selected_greenhouse.avg_humidity = greenhouse_avg['avg_humidity']
    recent_readings = SensorData.objects.select_related('greenhouse').order_by('-timestamp')[:5]
    all_readings = SensorData.objects.select_related('greenhouse').order_by('-timestamp')
    alert= Alert.objects.all()
    
    
    alert_counts = {
        'critical': Alert.objects.filter(status='critical', resolved=False).count(),
        'warning': Alert.objects.filter(status='warning', resolved=False).count(),
        'total': Alert.objects.filter(resolved=False).count()
    }
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    
    # Get daily averages
    daily_data = SensorData.objects.filter(
        timestamp__gte=start_date
    ).extra({
        'date': "date(timestamp)"
    }).values('date').annotate(
        avg_co2=Avg('co2'),
        avg_ch4=Avg('ch4'),
        avg_nox=Avg('nox')
    ).order_by('date')
    
    # Prepare chart data with pre-formatted dates
    chart_data = {
        'dates': [datetime.strptime(day['date'], '%Y-%m-%d').strftime('%a %m/%d') for day in daily_data],
        'co2': [float(day['avg_co2']) for day in daily_data],
        'ch4': [float(day['avg_ch4']) for day in daily_data],
        'nox': [float(day['avg_nox']) for day in daily_data]
    }
    
    
    

    context = {
        'avg_co2': averages['avg_co2'],
        'avg_ch4': averages['avg_ch4'],
        'avg_nox': averages['avg_nox'],
        'avg_temp': averages['avg_temp'],
        'avg_humidity': averages['avg_humidity'],
        'selected_greenhouse': selected_greenhouse,
        'recent_readings': recent_readings,
        'all_readings': all_readings,
        'alert_counts': alert_counts,
        "alerts":alert,
        'chart_data_json': JsonResponse(chart_data).content.decode('utf-8'),
    }
    
    return render(request, 'ema_dashboard.html', context)

@login_required
def policy_dashboard(request):
    return render(request, 'policy_dashboard.html')

def system_health(request):
    systems = Greenhouse.objects.all()
    thresholds= Thresholds.objects.last()
    systems_count = systems.count()
    active_systems_count = 0
    inactive_systems_count = systems_count - active_systems_count
    
    return render(request, 'system_health.html', {
        'systems': systems,
        'systems_count': systems_count,
        'active_systems_count': active_systems_count,
        'inactive_systems_count': inactive_systems_count,
        "thresholds":thresholds,
    })



def validate_greenhouse(esp32_id):
    try:
        return Greenhouse.objects.get(esp32_id=esp32_id)
    except Greenhouse.DoesNotExist:
        return None

def check_thresholds(greenhouse, sensor_type, value, thresholds):
    alert_data = {
        'greenhouse': greenhouse,
        'value': value,
        'resolved': False
    }
    
    if sensor_type == 'DHT22_TEMP':
        if value > thresholds.temperature:
            Alert.objects.create(
                **alert_data,
                gas_type='TEMP',
                threshold=thresholds.temperature,
                status='critical' if value > thresholds.temperature * 1.1 else 'warning'
            )
    
    elif sensor_type == 'DHT22_HUMIDITY':
        if value > thresholds.humidity:
            Alert.objects.create(
                **alert_data,
                gas_type='HUMIDITY',
                threshold=thresholds.humidity,
                status='critical' if value > thresholds.humidity * 1.1 else 'warning'
            )
    
    elif sensor_type == 'MQ4_CH4':
        if value > thresholds.ch4_threshold:
            Alert.objects.create(
                **alert_data,
                gas_type='CH4',
                threshold=thresholds.ch4_threshold,
                status='critical' if value > thresholds.ch4_threshold * 1.5 else 'warning'
            )
    
    elif sensor_type in ['MQ135_CO2', 'MQ135_NOX']:
        if sensor_type == 'MQ135_CO2' and value > thresholds.co2_threshold:
            Alert.objects.create(
                **alert_data,
                gas_type='CO2',
                threshold=thresholds.co2_threshold,
                status='critical' if value > thresholds.co2_threshold * 1.5 else 'warning'
            )
        elif sensor_type == 'MQ135_NOX' and value > thresholds.no2_threshold:
            Alert.objects.create(
                **alert_data,
                gas_type='NOX',
                threshold=thresholds.no2_threshold,
                status='critical' if value > thresholds.no2_threshold * 1.5 else 'warning'
            )

@csrf_exempt
@require_POST
def dht22_data(request):
    try:
        data = json.loads(request.body)
        required_fields = ['esp32_id', 'temperature', 'humidity']
        if not all(field in data for field in required_fields):
            return JsonResponse({'status': 'error', 'message': 'Missing required fields'}, status=400)
        
        greenhouse = validate_greenhouse(data['esp32_id'])
        if not greenhouse:
            return JsonResponse({'status': 'error', 'message': 'Unauthorized device'}, status=403)
        
        thresholds = Thresholds.objects.first() or Thresholds.objects.create()
        
        sensor_data = SensorData.objects.create(
            greenhouse=greenhouse,
            temperature=data['temperature'],
            humidity=data['humidity']
        )
        
        check_thresholds(greenhouse, 'DHT22_TEMP', data['temperature'], thresholds)
        check_thresholds(greenhouse, 'DHT22_HUMIDITY', data['humidity'], thresholds)
        
        return JsonResponse({'status': 'Created'})
    
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@csrf_exempt
@require_POST
def mq4_data(request):
    try:
        data = json.loads(request.body)
        required_fields = ['esp32_id', 'ch4']
        if not all(field in data for field in required_fields):
            return JsonResponse({'status': 'error', 'message': 'Missing required fields'}, status=400)
        
        greenhouse = validate_greenhouse(data['esp32_id'])
        if not greenhouse:
            return JsonResponse({'status': 'error', 'message': 'Unauthorized device'}, status=403)
        
        thresholds = Thresholds.objects.first() or Thresholds.objects.create()
        
        sensor_data = SensorData.objects.create(
            greenhouse=greenhouse,
            ch4=data['ch4']
        )
        
        check_thresholds(greenhouse, 'MQ4_CH4', data['ch4'], thresholds)
        
        return JsonResponse({'status': 'success'})
    
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@csrf_exempt
@require_POST
def mq135_data(request):
    try:
        data = json.loads(request.body)
        required_fields = ['esp32_id', 'co2', 'nox']
        if not all(field in data for field in required_fields):
            return JsonResponse({'status': 'error', 'message': 'Missing required fields'}, status=400)
        
        greenhouse = validate_greenhouse(data['esp32_id'])
        if not greenhouse:
            return JsonResponse({'status': 'error', 'message': 'Unauthorized device'}, status=403)
        
        thresholds = Thresholds.objects.first() or Thresholds.objects.create()
        
        sensor_data = SensorData.objects.create(
            greenhouse=greenhouse,
            co2=data['co2'],
            nox=data['nox']
        )
        
        check_thresholds(greenhouse, 'MQ135_CO2', data['co2'], thresholds)
        check_thresholds(greenhouse, 'MQ135_NOX', data['nox'], thresholds)
        
        return JsonResponse({'status': 'success'})
    
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)