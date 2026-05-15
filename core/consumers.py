# core/consumers.py
import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from .models import CrimeAlert, Camera

# Set up logging
logger = logging.getLogger(__name__)


class AlertConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time crime alerts.
    Handles WebSocket connections and sends instant alerts to connected clients.
    """
    
    async def connect(self):
        """
        Called when a client connects to the WebSocket.
        Adds the client to the crime_alerts group.
        """
        self.room_group_name = 'crime_alerts'
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        # Accept the connection
        await self.accept()
        
        # Send recent alerts to the newly connected client
        await self.send_recent_alerts()
        
        # Log the connection
        logger.info(f"WebSocket client connected: {self.channel_name}")
        
        # Send connection confirmation
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': 'Connected to PublicEye real-time alert system',
            'timestamp': timezone.now().isoformat()
        }))
    
    async def disconnect(self, close_code):
        """
        Called when a client disconnects.
        Removes the client from the crime_alerts group.
        """
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        
        # Log the disconnection
        logger.info(f"WebSocket client disconnected: {self.channel_name} (Code: {close_code})")
    
    async def receive(self, text_data):
        """
        Called when a message is received from the client.
        Handles different message types.
        """
        try:
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get('type')
            
            # Handle ping message (keep connection alive)
            if message_type == 'ping':
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'message': 'Connection alive',
                    'timestamp': timezone.now().isoformat()
                }))
            
            # Handle request for latest alerts
            elif message_type == 'get_latest_alerts':
                limit = text_data_json.get('limit', 10)
                alerts = await self.get_latest_alerts(limit)
                await self.send(text_data=json.dumps({
                    'type': 'latest_alerts',
                    'alerts': alerts,
                    'count': len(alerts)
                }))
            
            # Handle request for alert statistics
            elif message_type == 'get_stats':
                stats = await self.get_alert_stats()
                await self.send(text_data=json.dumps({
                    'type': 'stats',
                    'stats': stats
                }))
            
            # Handle acknowledgment of alert
            elif message_type == 'acknowledge_alert':
                alert_id = text_data_json.get('alert_id')
                await self.acknowledge_alert(alert_id)
                logger.info(f"Alert {alert_id} acknowledged via WebSocket")
            
            # Unknown message type
            else:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': f'Unknown message type: {message_type}'
                }))
                
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON received: {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON format'
            }))
        except Exception as e:
            logger.error(f"Error processing WebSocket message: {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f'Server error: {str(e)}'
            }))
    
    async def crime_alert(self, event):
        """
        Called when a crime alert is sent to the group.
        Sends the alert to the connected client.
        """
        alert_data = event['alert_data']
        
        # Add additional info
        alert_data['received_at'] = timezone.now().isoformat()
        alert_data['requires_attention'] = True
        
        # Send to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'crime_alert',
            'alert': alert_data,
            'timestamp': timezone.now().isoformat()
        }))
        
        logger.info(f"Alert sent to client: {alert_data.get('alert_id')}")
    
    async def send_recent_alerts(self):
        """
        Send recent alerts to newly connected client.
        """
        try:
            alerts = await self.get_recent_alerts()
            
            if alerts:
                await self.send(text_data=json.dumps({
                    'type': 'recent_alerts',
                    'alerts': alerts,
                    'count': len(alerts)
                }))
                logger.info(f"Sent {len(alerts)} recent alerts to new client")
            else:
                await self.send(text_data=json.dumps({
                    'type': 'recent_alerts',
                    'alerts': [],
                    'count': 0,
                    'message': 'No recent alerts'
                }))
        except Exception as e:
            logger.error(f"Error sending recent alerts: {e}")
    
    @database_sync_to_async
    def get_recent_alerts(self, limit=5):
        """
        Get recent alerts from the database.
        
        Args:
            limit: Number of recent alerts to retrieve
            
        Returns:
            list: List of alert dictionaries
        """
        try:
            alerts = CrimeAlert.objects.select_related('camera').order_by('-timestamp')[:limit]
            
            return [{
                'alert_id': alert.alert_id,
                'crime_type': alert.get_crime_type_display(),
                'crime_code': alert.crime_type,
                'confidence': float(alert.confidence_score),
                'location': alert.location,
                'camera_id': alert.camera.camera_id,
                'timestamp': alert.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'iso_timestamp': alert.timestamp.isoformat(),
                'status': alert.status,
                'description': alert.description,
                'url': f'/alert/{alert.alert_id}/',
                'has_screenshot': bool(alert.screenshot),
                'screenshot_url': alert.screenshot.url if alert.screenshot else None
            } for alert in alerts]
        except Exception as e:
            logger.error(f"Error fetching recent alerts: {e}")
            return []
    
    @database_sync_to_async
    def get_latest_alerts(self, limit=10):
        """
        Get latest alerts from the database.
        
        Args:
            limit: Number of alerts to retrieve
            
        Returns:
            list: List of alert dictionaries
        """
        try:
            alerts = CrimeAlert.objects.select_related('camera').order_by('-timestamp')[:limit]
            
            return [{
                'alert_id': alert.alert_id,
                'crime_type': alert.get_crime_type_display(),
                'confidence': float(alert.confidence_score),
                'location': alert.location,
                'timestamp': alert.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'status': alert.status,
                'url': f'/alert/{alert.alert_id}/'
            } for alert in alerts]
        except Exception as e:
            logger.error(f"Error fetching latest alerts: {e}")
            return []
    
    @database_sync_to_async
    def get_alert_stats(self):
        """
        Get alert statistics from the database.
        
        Returns:
            dict: Statistics including totals by type and status
        """
        try:
            from django.db.models import Count
            
            total_alerts = CrimeAlert.objects.count()
            pending_alerts = CrimeAlert.objects.filter(status='pending').count()
            investigating_alerts = CrimeAlert.objects.filter(status='investigating').count()
            resolved_alerts = CrimeAlert.objects.filter(status='resolved').count()
            false_alarms = CrimeAlert.objects.filter(status='false_alarm').count()
            
            # Get counts by crime type
            crime_type_counts = {}
            for crime_code, crime_name in CrimeAlert.CRIME_TYPES:
                count = CrimeAlert.objects.filter(crime_type=crime_code).count()
                if count > 0:
                    crime_type_counts[crime_name] = count
            
            # Get counts by hour (last 24 hours)
            from datetime import timedelta
            last_24h = timezone.now() - timedelta(hours=24)
            hourly_counts = []
            
            for hour in range(24):
                start_time = last_24h + timedelta(hours=hour)
                end_time = start_time + timedelta(hours=1)
                count = CrimeAlert.objects.filter(
                    timestamp__gte=start_time,
                    timestamp__lt=end_time
                ).count()
                hourly_counts.append({
                    'hour': hour,
                    'count': count,
                    'time': start_time.strftime('%H:00')
                })
            
            return {
                'total': total_alerts,
                'pending': pending_alerts,
                'investigating': investigating_alerts,
                'resolved': resolved_alerts,
                'false_alarms': false_alarms,
                'by_crime_type': crime_type_counts,
                'hourly': hourly_counts,
                'updated_at': timezone.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error fetching alert stats: {e}")
            return {
                'total': 0,
                'pending': 0,
                'investigating': 0,
                'resolved': 0,
                'false_alarms': 0,
                'by_crime_type': {},
                'hourly': []
            }
    
    @database_sync_to_async
    def acknowledge_alert(self, alert_id):
        """
        Mark an alert as acknowledged (adds a note).
        
        Args:
            alert_id: ID of the alert to acknowledge
        """
        try:
            alert = CrimeAlert.objects.get(alert_id=alert_id)
            if alert.additional_notes:
                alert.additional_notes += f"\n[ACKNOWLEDGED via WebSocket at {timezone.now()}]"
            else:
                alert.additional_notes = f"[ACKNOWLEDGED via WebSocket at {timezone.now()}]"
            alert.save()
            return True
        except CrimeAlert.DoesNotExist:
            logger.warning(f"Alert {alert_id} not found for acknowledgment")
            return False
        except Exception as e:
            logger.error(f"Error acknowledging alert: {e}")
            return False


class CameraStreamConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for camera stream monitoring.
    Sends real-time frame analysis results.
    """
    
    async def connect(self):
        """
        Called when a client connects to camera stream WebSocket.
        """
        self.camera_id = self.scope['url_route']['kwargs']['camera_id']
        self.room_group_name = f'camera_{self.camera_id}'
        
        # Join camera room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        logger.info(f"Camera stream WebSocket connected: {self.camera_id}")
        
        # Send confirmation
        await self.send(text_data=json.dumps({
            'type': 'connected',
            'camera_id': self.camera_id,
            'message': f'Connected to camera {self.camera_id} stream'
        }))
    
    async def disconnect(self, close_code):
        """
        Called when a client disconnects from camera stream.
        """
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        
        logger.info(f"Camera stream WebSocket disconnected: {self.camera_id}")
    
    async def receive(self, text_data):
        """
        Called when a message is received from the client.
        """
        try:
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get('type')
            
            if message_type == 'frame_analysis':
                # Process frame analysis result
                analysis_result = text_data_json.get('result', {})
                
                # Broadcast to all clients monitoring this camera
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'frame_update',
                        'analysis': analysis_result,
                        'timestamp': timezone.now().isoformat()
                    }
                )
            
            elif message_type == 'ping':
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'timestamp': timezone.now().isoformat()
                }))
        
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in camera stream: {text_data}")
        except Exception as e:
            logger.error(f"Error in camera stream: {e}")
    
    async def frame_update(self, event):
        """
        Send frame analysis update to client.
        """
        await self.send(text_data=json.dumps({
            'type': 'frame_analysis',
            'analysis': event['analysis'],
            'timestamp': event['timestamp']
        }))


class DashboardConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for dashboard real-time updates.
    Sends statistics updates to connected dashboard clients.
    """
    
    async def connect(self):
        """
        Called when a client connects to dashboard WebSocket.
        """
        self.room_group_name = 'dashboard_updates'
        
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        logger.info(f"Dashboard WebSocket client connected: {self.channel_name}")
        
        # Send initial stats
        await self.send_dashboard_stats()
    
    async def disconnect(self, close_code):
        """
        Called when a client disconnects from dashboard.
        """
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        
        logger.info(f"Dashboard WebSocket client disconnected: {self.channel_name}")
    
    async def receive(self, text_data):
        """
        Called when a message is received from the client.
        """
        try:
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get('type')
            
            if message_type == 'refresh_stats':
                await self.send_dashboard_stats()
            
            elif message_type == 'ping':
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'timestamp': timezone.now().isoformat()
                }))
        
        except Exception as e:
            logger.error(f"Error in dashboard consumer: {e}")
    
    async def dashboard_update(self, event):
        """
        Send dashboard update to client.
        """
        await self.send(text_data=json.dumps({
            'type': 'stats_update',
            'stats': event['stats'],
            'timestamp': event['timestamp']
        }))
    
    async def send_dashboard_stats(self):
        """
        Send current dashboard statistics to client.
        """
        try:
            stats = await self.get_dashboard_stats()
            await self.send(text_data=json.dumps({
                'type': 'stats',
                'stats': stats,
                'timestamp': timezone.now().isoformat()
            }))
        except Exception as e:
            logger.error(f"Error sending dashboard stats: {e}")
    
    @database_sync_to_async
    def get_dashboard_stats(self):
        """
        Get dashboard statistics from database.
        
        Returns:
            dict: Dashboard statistics
        """
        try:
            total_cameras = Camera.objects.count()
            active_cameras = Camera.objects.filter(status='active').count()
            total_alerts = CrimeAlert.objects.count()
            pending_alerts = CrimeAlert.objects.filter(status='pending').count()
            
            # Get last 24 hours alerts
            from datetime import timedelta
            last_24h = timezone.now() - timedelta(hours=24)
            recent_alerts = CrimeAlert.objects.filter(timestamp__gte=last_24h).count()
            
            return {
                'total_cameras': total_cameras,
                'active_cameras': active_cameras,
                'total_alerts': total_alerts,
                'pending_alerts': pending_alerts,
                'recent_alerts': recent_alerts,
                'updated_at': timezone.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting dashboard stats: {e}")
            return {
                'total_cameras': 0,
                'active_cameras': 0,
                'total_alerts': 0,
                'pending_alerts': 0,
                'recent_alerts': 0
            }