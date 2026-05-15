from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.http import JsonResponse, StreamingHttpResponse, HttpResponse
from django.core.paginator import Paginator
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.db.models import Count, Avg, Q, Sum
from django.db.models.functions import ExtractHour, ExtractWeekDay, TruncDate, TruncMonth
from .models import Camera, CrimeAlert, VideoUpload, PoliceNotification
from .ai_detector import CrimeDetector
import cv2
import json
import os
import numpy as np
from datetime import timedelta
from pathlib import Path

# Import WebSocket channels
try:
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync
    CHANNELS_AVAILABLE = True
except ImportError:
    CHANNELS_AVAILABLE = False
    print("Warning: Channels not available. WebSocket alerts disabled.")

# Initialize AI detector
detector = CrimeDetector()

def home(request):
    """Home page view"""
    return render(request, 'index.html')

def is_police_officer(user):
    """Check if user is police officer"""
    return user.is_authenticated and (user.is_staff or user.groups.filter(name='Police').exists())

@login_required
def dashboard(request):
    """Police dashboard with statistics"""
    # Statistics
    total_cameras = Camera.objects.count()
    active_cameras = Camera.objects.filter(status='active').count()
    total_alerts = CrimeAlert.objects.count()
    pending_alerts = CrimeAlert.objects.filter(status='pending').count()
    investigating_alerts = CrimeAlert.objects.filter(status='investigating').count()
    resolved_alerts = CrimeAlert.objects.filter(status='resolved').count()
    false_alarms = CrimeAlert.objects.filter(status='false_alarm').count()
    
    # Calculate AI accuracy
    if total_alerts > 0:
        accuracy = round(((total_alerts - false_alarms) / total_alerts) * 100, 1)
    else:
        accuracy = 100
    
    # Recent alerts
    recent_alerts = CrimeAlert.objects.select_related('camera').order_by('-timestamp')[:10]
    
    # Get recent uploads
    recent_uploads = VideoUpload.objects.filter(uploaded_by=request.user).order_by('-uploaded_at')[:5]
    
    context = {
        'total_cameras': total_cameras,
        'active_cameras': active_cameras,
        'total_alerts': total_alerts,
        'pending_alerts': pending_alerts,
        'investigating_alerts': investigating_alerts,
        'resolved_alerts': resolved_alerts,
        'false_alarms': false_alarms,
        'accuracy': accuracy,
        'recent_alerts': recent_alerts,
        'recent_uploads': recent_uploads,
        'websocket_enabled': CHANNELS_AVAILABLE,
    }
    return render(request, 'dashboard.html', context)

def send_websocket_alert(alert):
    """Send real-time alert via WebSocket to all connected clients"""
    if not CHANNELS_AVAILABLE:
        return
    
    try:
        channel_layer = get_channel_layer()
        
        alert_data = {
            'alert_id': alert.alert_id,
            'crime_type': alert.get_crime_type_display(),
            'crime_code': alert.crime_type,
            'confidence': float(alert.confidence_score),
            'location': alert.location,
            'description': alert.description,
            'timestamp': alert.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'iso_timestamp': alert.timestamp.isoformat(),
            'url': f'/alert/{alert.alert_id}/',
            'camera_id': alert.camera.camera_id,
            'camera_location': alert.camera.location,
            'screenshot_url': alert.screenshot.url if alert.screenshot else None,
            'requires_attention': True
        }
        
        # Send to the crime_alerts group
        async_to_sync(channel_layer.group_send)(
            'crime_alerts',
            {
                'type': 'crime_alert',
                'alert_data': alert_data
            }
        )
        print(f"📡 WebSocket alert sent for: {alert.alert_id}")
        
        # Also send to dashboard group for stats update
        async_to_sync(channel_layer.group_send)(
            'dashboard_updates',
            {
                'type': 'dashboard_update',
                'stats': {
                    'total_alerts': CrimeAlert.objects.count(),
                    'pending_alerts': CrimeAlert.objects.filter(status='pending').count(),
                    'latest_alert': alert_data
                },
                'timestamp': timezone.now().isoformat()
            }
        )
        
    except Exception as e:
        print(f"⚠️ WebSocket error: {e}")

@login_required
def camera_feed(request):
    """View all cameras and live feeds"""
    cameras = Camera.objects.all()
    
    # Filter by status if specified
    status_filter = request.GET.get('status', '')
    if status_filter:
        cameras = cameras.filter(status=status_filter)
    
    # Search
    search_query = request.GET.get('search', '')
    if search_query:
        cameras = cameras.filter(location__icontains=search_query) | cameras.filter(camera_id__icontains=search_query)
    
    paginator = Paginator(cameras, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'cameras': page_obj,
        'status_filter': status_filter,
        'search_query': search_query,
    }
    return render(request, 'camera_feed.html', context)

@login_required
def upload_video(request):
    """Upload and analyze video for crime detection"""
    if request.method == 'POST' and request.FILES.get('video_file'):
        video_file = request.FILES['video_file']
        
        # Validate file type
        allowed_formats = ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.mpeg', '.flv']
        file_extension = os.path.splitext(video_file.name)[1].lower()
        
        if file_extension not in allowed_formats:
            messages.error(request, f'Invalid video format. Allowed formats: {", ".join(allowed_formats)}')
            return redirect('core:upload_video')
        
        # Validate file size (max 500MB)
        if video_file.size > 500 * 1024 * 1024:
            messages.error(request, 'File too large. Maximum size is 500MB.')
            return redirect('core:upload_video')
        
        # Save uploaded video
        upload = VideoUpload.objects.create(
            uploaded_by=request.user,
            video_file=video_file
        )
        
        messages.info(request, f'📹 Video "{video_file.name}" uploaded. Analyzing for criminal activity...')
        
        # Analyze video with progress callback
        analysis_result = None
        
        def progress_callback(data):
            print(f"Analysis progress: {data}")
        
        try:
            video_path = upload.video_file.path
            analysis_result = detector.analyze_video(video_path, callback=progress_callback)
        except Exception as e:
            messages.error(request, f'Error analyzing video: {str(e)}')
            upload.analyzed = True
            upload.analysis_result = json.dumps({'error': str(e)})
            upload.save()
            return redirect('core:upload_video')
        
        # Update upload record
        upload.analyzed = True
        upload.analysis_completed_at = timezone.now()
        
        if analysis_result and analysis_result.get('crime_detected'):
            # Get or create a default camera for uploaded videos
            default_camera, created = Camera.objects.get_or_create(
                camera_id='UPLOAD_CAM',
                defaults={
                    'location': 'Video Upload Analysis',
                    'status': 'active',
                    'description': 'Default camera for uploaded video analysis',
                    'ip_address': '127.0.0.1'
                }
            )
            
            # Ensure camera is active
            if not created and default_camera.status != 'active':
                default_camera.status = 'active'
                default_camera.save()
            
            # Create crime alert
            alert = CrimeAlert.objects.create(
                camera=default_camera,
                crime_type=analysis_result.get('crime_type', 'other'),
                confidence_score=analysis_result.get('confidence', 0) * 100,
                location=f'Uploaded Video: {video_file.name}',
                description=analysis_result.get('description', 'Crime detected in uploaded video'),
                reported_to_police=True
            )
            
            # Save screenshot if frame was available
            if 'frame' in analysis_result:
                try:
                    frame = analysis_result['frame']
                    # Convert frame to image
                    is_success, buffer = cv2.imencode('.jpg', frame)
                    if is_success:
                        image_file = ContentFile(buffer.tobytes())
                        alert.screenshot.save(f'alert_{alert.alert_id}.jpg', image_file)
                except Exception as e:
                    print(f"Error saving screenshot: {e}")
            
            upload.crime_alert = alert
            upload.analysis_result = json.dumps(analysis_result, default=str)
            upload.save()
            
            # Send notifications (both database and WebSocket)
            send_police_notification(alert)
            send_websocket_alert(alert)
            
            messages.success(
                request, 
                f'🚨 CRIME DETECTED: {alert.get_crime_type_display()} '
                f'(Confidence: {alert.confidence_score:.1f}%) - Police notified!'
            )
        else:
            upload.analysis_result = json.dumps({
                'crime_detected': False, 
                'message': 'No suspicious activity detected in the video'
            })
            upload.save()
            messages.info(request, '✅ Analysis complete: No criminal activity detected in the video.')
        
        return redirect('core:upload_video')
    
    # GET request - show upload form
    recent_uploads = VideoUpload.objects.filter(uploaded_by=request.user).order_by('-uploaded_at')[:10]
    context = {
        'recent_uploads': recent_uploads,
        'websocket_enabled': CHANNELS_AVAILABLE,
    }
    return render(request, 'upload_video.html', context)

@login_required
def upload_status(request, upload_id):
    """Check status of an upload"""
    upload = get_object_or_404(VideoUpload, id=upload_id, uploaded_by=request.user)
    
    data = {
        'id': upload.id,
        'analyzed': upload.analyzed,
        'crime_detected': upload.crime_alert is not None,
        'file_name': os.path.basename(upload.video_file.name),
        'uploaded_at': upload.uploaded_at.strftime('%Y-%m-%d %H:%M:%S'),
    }
    
    if upload.crime_alert:
        data['alert'] = {
            'id': upload.crime_alert.alert_id,
            'crime_type': upload.crime_alert.get_crime_type_display(),
            'confidence': upload.crime_alert.confidence_score,
            'url': f'/alert/{upload.crime_alert.alert_id}/'
        }
    
    return JsonResponse(data)

@login_required
def delete_upload(request, upload_id):
    """Delete an uploaded video"""
    upload = get_object_or_404(VideoUpload, id=upload_id, uploaded_by=request.user)
    
    if request.method == 'POST':
        # Delete the file from storage
        if upload.video_file:
            upload.video_file.delete()
        
        # Delete the database record
        upload.delete()
        messages.success(request, 'Upload deleted successfully')
        return redirect('core:upload_video')
    
    return render(request, 'confirm_delete.html', {'upload': upload})

@login_required
def alerts(request):
    """View all crime alerts"""
    alerts = CrimeAlert.objects.select_related('camera').all().order_by('-timestamp')
    
    # Filter by crime type
    crime_type = request.GET.get('crime_type', '')
    if crime_type:
        alerts = alerts.filter(crime_type=crime_type)
    
    # Filter by status
    status = request.GET.get('status', '')
    if status:
        alerts = alerts.filter(status=status)
    
    # Date range filter
    from_date = request.GET.get('from_date', '')
    to_date = request.GET.get('to_date', '')
    if from_date:
        alerts = alerts.filter(timestamp__gte=from_date)
    if to_date:
        alerts = alerts.filter(timestamp__lte=to_date)
    
    paginator = Paginator(alerts, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'alerts': page_obj,
        'crime_types': CrimeAlert.CRIME_TYPES,
        'status_choices': CrimeAlert.STATUS_CHOICES,
        'selected_crime_type': crime_type,
        'selected_status': status,
        'from_date': from_date,
        'to_date': to_date,
    }
    return render(request, 'alerts.html', context)

@login_required
def alert_detail(request, alert_id):
    """View detailed information about a specific alert"""
    alert = get_object_or_404(CrimeAlert, alert_id=alert_id)
    
    if request.method == 'POST':
        # Update alert status
        new_status = request.POST.get('status')
        if new_status in dict(CrimeAlert.STATUS_CHOICES):
            alert.status = new_status
            if new_status == 'dispatched':
                alert.police_response_time = timezone.now()
            alert.save()
            messages.success(request, f'Alert status updated to {alert.get_status_display()}')
            
            # Send WebSocket update for status change
            if CHANNELS_AVAILABLE:
                try:
                    channel_layer = get_channel_layer()
                    async_to_sync(channel_layer.group_send)(
                        'crime_alerts',
                        {
                            'type': 'crime_alert',
                            'alert_data': {
                                'alert_id': alert.alert_id,
                                'status': alert.status,
                                'action': 'status_updated'
                            }
                        }
                    )
                except Exception as e:
                    print(f"WebSocket status update error: {e}")
        
        # Add notes
        notes = request.POST.get('additional_notes')
        if notes:
            alert.additional_notes = notes
            alert.save()
            messages.success(request, 'Notes added successfully')
        
        return redirect('core:alert_detail', alert_id=alert.alert_id)
    
    context = {
        'alert': alert,
    }
    return render(request, 'alert_detail.html', context)

@user_passes_test(is_police_officer)
def manage_cameras(request):
    """Manage CCTV cameras (add, edit, delete)"""
    if request.method == 'POST':
        action = request.POST.get('action')
        
        try:
            if action == 'add':
                camera = Camera.objects.create(
                    camera_id=request.POST.get('camera_id'),
                    location=request.POST.get('location'),
                    latitude=request.POST.get('latitude') or None,
                    longitude=request.POST.get('longitude') or None,
                    ip_address=request.POST.get('ip_address') or None,
                    stream_url=request.POST.get('stream_url') or None,
                    description=request.POST.get('description') or '',
                )
                messages.success(request, f'Camera {camera.camera_id} added successfully')
            
            elif action == 'edit':
                camera_id = request.POST.get('camera_id')
                camera = get_object_or_404(Camera, camera_id=camera_id)
                camera.location = request.POST.get('location', camera.location)
                camera.latitude = request.POST.get('latitude') or None
                camera.longitude = request.POST.get('longitude') or None
                camera.ip_address = request.POST.get('ip_address') or None
                camera.stream_url = request.POST.get('stream_url') or None
                camera.status = request.POST.get('status', camera.status)
                camera.description = request.POST.get('description') or ''
                camera.save()
                messages.success(request, f'Camera {camera.camera_id} updated successfully')
            
            elif action == 'delete':
                camera_id = request.POST.get('camera_id')
                camera = get_object_or_404(Camera, camera_id=camera_id)
                camera.delete()
                messages.success(request, f'Camera {camera_id} deleted successfully')
            
            else:
                messages.error(request, 'Invalid action')
        
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
        
        return redirect('core:manage_cameras')
    
    cameras = Camera.objects.all().order_by('-installed_date')
    context = {
        'cameras': cameras,
    }
    return render(request, 'manage_cameras.html', context)

def live_camera_stream(request, camera_id):
    """Stream live feed from camera with better error handling"""
    try:
        camera = get_object_or_404(Camera, camera_id=camera_id, status='active')
    except:
        # Return a simple error response
        error_html = f"""
        <html>
        <head><title>Camera Not Found</title></head>
        <body style="text-align:center;padding:50px;font-family:Arial;">
            <h1 style="color:#dc3545;">📹 Camera Not Found</h1>
            <p>Camera with ID <strong>{camera_id}</strong> does not exist or is inactive.</p>
            <a href="/cameras/">← Back to Cameras</a>
        </body>
        </html>
        """
        return HttpResponse(error_html, status=404)
    
    def generate_frames():
        cap = None
        
        # Try different methods to open camera
        if camera.stream_url:
            cap = cv2.VideoCapture(camera.stream_url)
        elif camera.ip_address:
            cap = cv2.VideoCapture(f'http://{camera.ip_address}/video')
        else:
            cap = cv2.VideoCapture(0)
        
        if not cap or not cap.isOpened():
            error_frame = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(error_frame, f"Camera {camera.camera_id} - Offline", (50, 240),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            cv2.putText(error_frame, "Please check camera connection", (50, 280),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 1)
            ret, buffer = cv2.imencode('.jpg', error_frame)
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            return
        
        frame_count = 0
        while True:
            success, frame = cap.read()
            if not success:
                break
            
            # Analyze every 30th frame
            if frame_count % 30 == 0:
                result = detector.analyze_frame(frame)
                if result and result.get('crime_detected'):
                    cv2.putText(frame, f"ALERT: {result['crime_type']}", (10, 30),
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                    cv2.rectangle(frame, (0, 0), (frame.shape[1], frame.shape[0]), (0, 0, 255), 3)
                    
                    if CHANNELS_AVAILABLE:
                        try:
                            temp_alert = {
                                'alert_id': f'LIVE_{camera.camera_id}_{int(timezone.now().timestamp())}',
                                'crime_type': result['crime_type'],
                                'confidence': result.get('confidence', 0) * 100,
                                'location': camera.location,
                                'description': result.get('description', 'Crime detected in live stream'),
                                'camera_id': camera.camera_id
                            }
                            channel_layer = get_channel_layer()
                            async_to_sync(channel_layer.group_send)(
                                'crime_alerts',
                                {
                                    'type': 'crime_alert',
                                    'alert_data': temp_alert
                                }
                            )
                        except Exception as e:
                            print(f"Live stream WebSocket error: {e}")
            
            cv2.putText(frame, f"Camera: {camera.camera_id}", (10, frame.shape[0] - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            cv2.putText(frame, timezone.now().strftime('%Y-%m-%d %H:%M:%S'), 
                       (frame.shape[1] - 200, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            
            frame_count += 1
        
        cap.release()
    
    response = StreamingHttpResponse(generate_frames(),
                                    content_type='multipart/x-mixed-replace; boundary=frame')
    response['Cache-Control'] = 'no-cache'
    return response

@login_required
def get_crime_stats(request):
    """API endpoint for crime statistics"""
    from django.db.models import Count
    
    days = int(request.GET.get('days', 7))
    from_date = timezone.now() - timedelta(days=days)
    
    alerts = CrimeAlert.objects.filter(timestamp__gte=from_date)
    
    stats = {
        'total_alerts': alerts.count(),
        'by_type': {},
        'by_status': {},
        'by_day': {},
        'accuracy': 0,
    }
    
    for crime_code, crime_name in CrimeAlert.CRIME_TYPES:
        count = alerts.filter(crime_type=crime_code).count()
        if count > 0:
            stats['by_type'][crime_name] = count
    
    for status_code, status_name in CrimeAlert.STATUS_CHOICES:
        count = alerts.filter(status=status_code).count()
        if count > 0:
            stats['by_status'][status_name] = count
    
    return JsonResponse(stats)

@login_required
def export_alerts(request):
    """Export alerts as CSV"""
    import csv
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="publiceye_alerts.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Alert ID', 'Crime Type', 'Location', 'Confidence', 'Status', 'Timestamp', 'Description'])
    
    alerts = CrimeAlert.objects.select_related('camera').all()
    for alert in alerts:
        writer.writerow([
            alert.alert_id,
            alert.get_crime_type_display(),
            alert.location,
            f"{alert.confidence_score}%",
            alert.get_status_display(),
            alert.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            alert.description
        ])
    
    return response

@login_required
def analytics_dashboard(request):
    """Advanced analytics dashboard with charts and statistics"""
    context = {}
    
    days = int(request.GET.get('days', 30))
    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)
    alerts = CrimeAlert.objects.filter(timestamp__gte=start_date, timestamp__lte=end_date)
    
    # Hourly distribution
    hourly_stats = alerts.annotate(hour=ExtractHour('timestamp')).values('hour').annotate(count=Count('id')).order_by('hour')
    hourly_data = {h['hour']: h['count'] for h in hourly_stats}
    context['hourly_labels'] = list(range(24))
    context['hourly_data'] = [hourly_data.get(h, 0) for h in range(24)]
    
    # Weekly distribution
    weekly_stats = alerts.annotate(day=ExtractWeekDay('timestamp')).values('day').annotate(count=Count('id')).order_by('day')
    days_of_week = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    weekly_data = {w['day']: w['count'] for w in weekly_stats}
    context['weekly_labels'] = days_of_week
    context['weekly_data'] = [weekly_data.get(i+1, 0) for i in range(7)]
    
    # Monthly trends
    monthly_stats = alerts.annotate(month=TruncDate('timestamp')).values('month').annotate(count=Count('id')).order_by('month')
    context['monthly_labels'] = [m['month'].strftime('%b %Y') for m in monthly_stats]
    context['monthly_data'] = [m['count'] for m in monthly_stats]
    
    # Crime type distribution
    crime_type_stats = alerts.values('crime_type').annotate(count=Count('id')).order_by('-count')
    context['crime_type_labels'] = [dict(CrimeAlert.CRIME_TYPES).get(c['crime_type'], c['crime_type']) for c in crime_type_stats]
    context['crime_type_data'] = [c['count'] for c in crime_type_stats]
    
    # Response time analytics
    resolved_alerts = alerts.exclude(police_response_time__isnull=True)
    if resolved_alerts.exists():
        response_times = []
        for alert in resolved_alerts:
            if alert.police_response_time:
                response_time = (alert.police_response_time - alert.timestamp).total_seconds() / 60
                response_times.append(response_time)
        
        context['avg_response_time'] = round(sum(response_times) / len(response_times), 1)
        context['min_response_time'] = round(min(response_times), 1)
        context['max_response_time'] = round(max(response_times), 1)
    else:
        context['avg_response_time'] = 0
        context['min_response_time'] = 0
        context['max_response_time'] = 0
    
    # AI accuracy metrics
    false_alarms = alerts.filter(status='false_alarm').count()
    total_alerts = alerts.count()
    if total_alerts > 0:
        context['accuracy'] = round(((total_alerts - false_alarms) / total_alerts) * 100, 1)
        context['false_positive_rate'] = round((false_alarms / total_alerts) * 100, 1)
    else:
        context['accuracy'] = 100
        context['false_positive_rate'] = 0
    
    # Crime trends
    trend_data = alerts.annotate(date=TruncDate('timestamp')).values('date').annotate(count=Count('id')).order_by('date')
    context['trend_labels'] = [t['date'].strftime('%Y-%m-%d') for t in trend_data]
    context['trend_data'] = [t['count'] for t in trend_data]
    
    # Top locations
    top_locations = alerts.values('location').annotate(count=Count('id')).order_by('-count')[:10]
    context['top_locations'] = [{'name': loc['location'][:30], 'count': loc['count']} for loc in top_locations]
    
    # Crime confidence by type
    crime_confidence = []
    for crime_code, crime_name in CrimeAlert.CRIME_TYPES:
        crime_alerts = alerts.filter(crime_type=crime_code)
        if crime_alerts.exists():
            avg_confidence = crime_alerts.aggregate(Avg('confidence_score'))['confidence_score__avg']
            crime_confidence.append({
                'name': crime_name,
                'count': crime_alerts.count(),
                'avg_confidence': round(avg_confidence, 1) if avg_confidence else 0
            })
    context['crime_confidence'] = crime_confidence
    
    context['date_range'] = days
    context['start_date'] = start_date.strftime('%Y-%m-%d')
    context['end_date'] = end_date.strftime('%Y-%m-%d')
    context['total_alerts'] = total_alerts
    context['false_alarms'] = false_alarms
    
    return render(request, 'analytics_dashboard.html', context)

@login_required
def analytics_api_data(request):
    """API endpoint for dynamic analytics data"""
    days = int(request.GET.get('days', 30))
    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)
    
    alerts = CrimeAlert.objects.filter(timestamp__gte=start_date, timestamp__lte=end_date)
    
    # Days of week for busiest day calculation
    days_of_week = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    
    # Calculate hourly distribution
    hourly_stats = alerts.annotate(hour=ExtractHour('timestamp')).values('hour').annotate(count=Count('id'))
    hourly_data = {}
    for i in range(24):
        hourly_data[i] = 0
    for stat in hourly_stats:
        hourly_data[stat['hour']] = stat['count']
    
    # Calculate weekly distribution
    weekly_stats = alerts.annotate(day=ExtractWeekDay('timestamp')).values('day').annotate(count=Count('id'))
    weekly_data = [0] * 7
    for stat in weekly_stats:
        if 1 <= stat['day'] <= 7:
            weekly_data[stat['day'] - 1] = stat['count']
    
    # Calculate monthly trends
    monthly_stats = alerts.annotate(month=TruncMonth('timestamp')).values('month').annotate(count=Count('id')).order_by('month')
    monthly_labels = [stat['month'].strftime('%b %Y') for stat in monthly_stats]
    monthly_data = [stat['count'] for stat in monthly_stats]
    
    # Crime type distribution
    crime_type_stats = alerts.values('crime_type').annotate(count=Count('id')).order_by('-count')
    crime_type_labels = []
    crime_type_data = []
    crime_confidence = []
    crime_type_dict = dict(CrimeAlert.CRIME_TYPES)
    
    for stat in crime_type_stats:
        crime_name = crime_type_dict.get(stat['crime_type'], stat['crime_type'])
        crime_type_labels.append(crime_name)
        crime_type_data.append(stat['count'])
        avg_conf = alerts.filter(crime_type=stat['crime_type']).aggregate(Avg('confidence_score'))['confidence_score__avg'] or 0
        crime_confidence.append({
            'name': crime_name,
            'count': stat['count'],
            'avg_confidence': round(avg_conf, 1)
        })
    
    # Response times
    resolved_alerts = alerts.exclude(police_response_time__isnull=True)
    response_times = []
    for alert in resolved_alerts:
        if alert.police_response_time:
            response_time = (alert.police_response_time - alert.timestamp).total_seconds() / 60
            response_times.append(response_time)
    
    if response_times:
        avg_response_time = round(sum(response_times) / len(response_times), 1)
        min_response_time = round(min(response_times), 1)
        max_response_time = round(max(response_times), 1)
    else:
        avg_response_time = 0
        min_response_time = 0
        max_response_time = 0
    
    # AI accuracy
    false_alarms = alerts.filter(status='false_alarm').count()
    total_alerts = alerts.count()
    if total_alerts > 0:
        accuracy = round(((total_alerts - false_alarms) / total_alerts) * 100, 1)
        false_positive_rate = round((false_alarms / total_alerts) * 100, 1)
    else:
        accuracy = 100
        false_positive_rate = 0
    
    # Top locations
    top_locations = alerts.values('location').annotate(count=Count('id')).order_by('-count')[:10]
    top_locations_list = [{'name': loc['location'][:30], 'count': loc['count']} for loc in top_locations]
    
    # Trends
    trend_stats = alerts.annotate(date=TruncDate('timestamp')).values('date').annotate(count=Count('id')).order_by('date')[:30]
    trend_labels = [stat['date'].strftime('%Y-%m-%d') for stat in trend_stats]
    trend_data = [stat['count'] for stat in trend_stats]
    
    # Find busiest day
    busiest_day = 'Unknown'
    if weekly_data and max(weekly_data) > 0:
        busiest_day = days_of_week[weekly_data.index(max(weekly_data))]
    
    # Most common crime
    most_common_crime = crime_type_labels[0] if crime_type_labels else 'None'
    most_common_count = crime_type_data[0] if crime_type_data else 0
    
    data = {
        'date_range': days,
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d'),
        'total_alerts': total_alerts,
        'accuracy': accuracy,
        'false_positive_rate': false_positive_rate,
        'false_alarms': false_alarms,
        'avg_response_time': avg_response_time,
        'min_response_time': min_response_time,
        'max_response_time': max_response_time,
        'hourly_data': hourly_data,
        'weekly_data': weekly_data,
        'monthly_labels': monthly_labels,
        'monthly_data': monthly_data,
        'trend_labels': trend_labels,
        'trend_data': trend_data,
        'crime_type_labels': crime_type_labels,
        'crime_type_data': crime_type_data,
        'crime_confidence': crime_confidence,
        'top_locations': top_locations_list,
        'most_common_crime': most_common_crime,
        'most_common_count': most_common_count,
        'busiest_day': busiest_day
    }
    
    return JsonResponse(data)

@login_required
def export_analytics(request, format='json'):
    """Export analytics data in various formats"""
    days = int(request.GET.get('days', 30))
    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)
    
    alerts = CrimeAlert.objects.filter(timestamp__gte=start_date, timestamp__lte=end_date)
    
    if format == 'json':
        data = {
            'total_alerts': alerts.count(),
            'crime_breakdown': {},
            'hourly_distribution': {},
            'date_range': {'start': start_date.isoformat(), 'end': end_date.isoformat()},
            'alerts': list(alerts.values('alert_id', 'crime_type', 'timestamp', 'location', 'confidence_score', 'status'))
        }
        return JsonResponse(data)
    
    elif format == 'csv':
        import csv
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="analytics_data.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Alert ID', 'Crime Type', 'Timestamp', 'Location', 'Confidence', 'Status'])
        
        for alert in alerts:
            writer.writerow([
                alert.alert_id,
                alert.get_crime_type_display(),
                alert.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                alert.location,
                f"{alert.confidence_score}%",
                alert.get_status_display()
            ])
        
        return response
    
    return JsonResponse({'error': 'Invalid format'}, status=400)

def login_view(request):
    """Custom login view"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')
            try:
                return redirect('core:dashboard')
            except:
                try:
                    return redirect('dashboard')
                except:
                    return redirect('/dashboard/')
        else:
            messages.error(request, 'Invalid username or password. Please try again.')
    return render(request, 'registration/login.html')

def logout_view(request):
    """Custom logout view"""
    logout(request)
    messages.info(request, 'You have been logged out successfully.')
    try:
        return redirect('core:home')
    except:
        try:
            return redirect('home')
        except:
            return redirect('/')

def send_police_notification(alert):
    """Send notification to police department"""
    PoliceNotification.objects.create(
        alert=alert,
        sent_to='police_dashboard',
        notification_type='dashboard',
        message=f'🚨 CRIME ALERT: {alert.get_crime_type_display()} detected. Confidence: {alert.confidence_score:.1f}%',
        delivered=True
    )
    print(f"✅ Notification sent for alert: {alert.alert_id}")

@csrf_exempt
def webhook_receive_alert(request):
    """Webhook endpoint for receiving alerts from cameras"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            return JsonResponse({'status': 'received'}, status=200)
        except:
            return JsonResponse({'error': 'Invalid data'}, status=400)
    return JsonResponse({'error': 'Method not allowed'}, status=405)

def handler404(request, exception):
    """Custom 404 error handler"""
    return render(request, 'errors/404.html', status=404)

def handler500(request):
    """Custom 500 error handler"""
    return render(request, 'errors/500.html', status=500)

def handler403(request, exception):
    """Custom 403 error handler"""
    return render(request, 'errors/403.html', status=403)