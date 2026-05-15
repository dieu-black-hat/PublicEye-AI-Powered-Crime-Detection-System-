from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Camera(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('maintenance', 'Maintenance'),
        ('offline', 'Offline'),
    ]
    
    camera_id = models.CharField(max_length=50, unique=True)
    location = models.CharField(max_length=200)
    latitude = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    stream_url = models.URLField(max_length=500, null=True, blank=True, help_text="RTSP or HTTP stream URL")
    description = models.TextField(blank=True, null=True, help_text="Additional camera information")
    installed_date = models.DateTimeField(auto_now_add=True)
    last_active = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.camera_id} - {self.location}"
    
    class Meta:
        verbose_name_plural = "Cameras"
        ordering = ['-installed_date']


class CrimeAlert(models.Model):
    CRIME_TYPES = [
        ('theft', 'Theft'),
        ('assault', 'Assault'),
        ('vandalism', 'Vandalism'),
        ('robbery', 'Robbery'),
        ('suspicious_activity', 'Suspicious Activity'),
        ('fight', 'Fight'),
        ('accident', 'Accident'),
        ('weapon', 'Weapon Detection'),
        ('trespassing', 'Trespassing'),
        ('other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('investigating', 'Under Investigation'),
        ('resolved', 'Resolved'),
        ('false_alarm', 'False Alarm'),
        ('dispatched', 'Police Dispatched'),
    ]
    
    alert_id = models.CharField(max_length=50, unique=True)
    camera = models.ForeignKey(Camera, on_delete=models.CASCADE, related_name='alerts')
    crime_type = models.CharField(max_length=50, choices=CRIME_TYPES)
    confidence_score = models.FloatField(help_text="AI confidence percentage")
    timestamp = models.DateTimeField(auto_now_add=True)
    location = models.CharField(max_length=200)
    video_clip = models.FileField(upload_to='crime_clips/%Y/%m/%d/', null=True, blank=True)
    screenshot = models.ImageField(upload_to='crime_screenshots/%Y/%m/%d/', null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    description = models.TextField()
    additional_notes = models.TextField(blank=True, null=True)
    reported_to_police = models.BooleanField(default=False)
    police_response_time = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Alert {self.alert_id} - {self.get_crime_type_display()}"
    
    def save(self, *args, **kwargs):
        if not self.alert_id:
            self.alert_id = f"ALERT_{timezone.now().strftime('%Y%m%d_%H%M%S')}_{self.camera.camera_id}"
        if self.status == 'resolved' and not self.resolved_at:
            self.resolved_at = timezone.now()
        super().save(*args, **kwargs)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['status']),
            models.Index(fields=['crime_type']),
        ]


class VideoUpload(models.Model):
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='video_uploads')
    video_file = models.FileField(upload_to='uploads/%Y/%m/%d/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    analyzed = models.BooleanField(default=False)
    analysis_completed_at = models.DateTimeField(null=True, blank=True)
    analysis_result = models.TextField(null=True, blank=True)
    crime_alert = models.OneToOneField(CrimeAlert, on_delete=models.SET_NULL, null=True, blank=True, related_name='video_upload')
    file_size = models.BigIntegerField(null=True, blank=True, help_text="File size in bytes")
    duration = models.FloatField(null=True, blank=True, help_text="Video duration in seconds")
    
    def __str__(self):
        return f"Upload {self.id} - {self.uploaded_by.username} - {self.uploaded_at}"
    
    def save(self, *args, **kwargs):
        if self.video_file and not self.file_size:
            self.file_size = self.video_file.size
        super().save(*args, **kwargs)
    
    class Meta:
        ordering = ['-uploaded_at']


class PoliceNotification(models.Model):
    NOTIFICATION_TYPES = [
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('dashboard', 'Dashboard'),
        ('push', 'Push Notification'),
    ]
    
    alert = models.ForeignKey(CrimeAlert, on_delete=models.CASCADE, related_name='notifications')
    sent_at = models.DateTimeField(auto_now_add=True)
    sent_to = models.CharField(max_length=200)
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES)
    message = models.TextField()
    delivered = models.BooleanField(default=False)
    delivered_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"Notification for {self.alert.alert_id} - {self.get_notification_type_display()}"
    
    def mark_as_delivered(self):
        self.delivered = True
        self.delivered_at = timezone.now()
        self.save()
    
    class Meta:
        ordering = ['-sent_at']


# Optional: Police Profile for additional police officer information
class PoliceProfile(models.Model):
    RANK_CHOICES = [
        ('officer', 'Police Officer'),
        ('sergeant', 'Sergeant'),
        ('lieutenant', 'Lieutenant'),
        ('captain', 'Captain'),
        ('chief', 'Chief'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='police_profile')
    badge_number = models.CharField(max_length=20, unique=True)
    rank = models.CharField(max_length=20, choices=RANK_CHOICES, default='officer')
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    station = models.CharField(max_length=200, blank=True, null=True)
    is_on_duty = models.BooleanField(default=True)
    assigned_zone = models.CharField(max_length=100, blank=True, null=True)
    joined_date = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.get_rank_display()} {self.user.get_full_name()} ({self.badge_number})"
    
    class Meta:
        verbose_name_plural = "Police Profiles"