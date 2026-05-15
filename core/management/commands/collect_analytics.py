# core/management/commands/collect_analytics.py
"""
Management command to collect and aggregate analytics data for reporting.
Run with: python manage.py collect_analytics
"""

import json
import csv
from datetime import datetime, timedelta
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db.models import Count, Avg, Sum, Q, F
from django.db.models.functions import TruncDate, TruncHour, TruncMonth, ExtractHour, ExtractWeekDay

from core.models import CrimeAlert, Camera, VideoUpload, PoliceNotification


class Command(BaseCommand):
    help = 'Collect and aggregate analytics data for crime reporting and statistics'

    def add_arguments(self, parser):
        """Add command line arguments"""
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Number of days to analyze (default: 30)'
        )
        parser.add_argument(
            '--format',
            type=str,
            choices=['json', 'csv', 'console'],
            default='console',
            help='Output format (default: console)'
        )
        parser.add_argument(
            '--output',
            type=str,
            help='Output file path (for json/csv formats)'
        )
        parser.add_argument(
            '--export',
            action='store_true',
            help='Export full analytics report'
        )

    def handle(self, *args, **options):
        """Main command handler"""
        days = options['days']
        output_format = options['format']
        output_file = options.get('output')
        export_mode = options.get('export', False)
        
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('📊 PublicEye Analytics Collection'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(f'📅 Analyzing last {days} days\n')
        
        # Calculate date range
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        # Collect all analytics data
        analytics_data = {
            'collection_date': end_date.isoformat(),
            'date_range': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat(),
                'days': days
            },
            'summary': self.get_summary_stats(start_date, end_date),
            'crime_analytics': self.get_crime_analytics(start_date, end_date),
            'temporal_analytics': self.get_temporal_analytics(start_date, end_date),
            'ai_performance': self.get_ai_performance_metrics(start_date, end_date),
            'camera_analytics': self.get_camera_analytics(start_date, end_date),
            'response_analytics': self.get_response_analytics(start_date, end_date),
            'trends': self.get_trend_analysis(start_date, end_date),
            'predictions': self.get_predictions(start_date, end_date)
        }
        
        # Output based on format
        if output_format == 'json':
            self.output_json(analytics_data, output_file)
        elif output_format == 'csv':
            self.output_csv(analytics_data, output_file)
        else:
            self.output_console(analytics_data)
        
        # Export full report if requested
        if export_mode:
            self.export_full_report(analytics_data, days)
        
        self.stdout.write(self.style.SUCCESS('\n✅ Analytics collection completed!'))

    def get_summary_stats(self, start_date, end_date):
        """Get summary statistics"""
        alerts = CrimeAlert.objects.filter(timestamp__gte=start_date, timestamp__lte=end_date)
        
        total_alerts = alerts.count()
        resolved_alerts = alerts.filter(status='resolved').count()
        false_alarms = alerts.filter(status='false_alarm').count()
        pending_alerts = alerts.filter(status='pending').count()
        investigating_alerts = alerts.filter(status='investigating').count()
        
        # Calculate average confidence
        avg_confidence = alerts.aggregate(Avg('confidence_score'))['confidence_score__avg'] or 0
        
        # Calculate accuracy
        if total_alerts > 0:
            accuracy = ((total_alerts - false_alarms) / total_alerts) * 100
        else:
            accuracy = 100
        
        return {
            'total_alerts': total_alerts,
            'resolved_alerts': resolved_alerts,
            'false_alarms': false_alarms,
            'pending_alerts': pending_alerts,
            'investigating_alerts': investigating_alerts,
            'average_confidence': round(avg_confidence, 2),
            'accuracy': round(accuracy, 2),
            'false_positive_rate': round((false_alarms / total_alerts * 100) if total_alerts > 0 else 0, 2)
        }

    def get_crime_analytics(self, start_date, end_date):
        """Get crime type analytics"""
        alerts = CrimeAlert.objects.filter(timestamp__gte=start_date, timestamp__lte=end_date)
        
        # Crime type distribution
        crime_distribution = []
        for crime_code, crime_name in CrimeAlert.CRIME_TYPES:
            count = alerts.filter(crime_type=crime_code).count()
            if count > 0:
                avg_conf = alerts.filter(crime_type=crime_code).aggregate(Avg('confidence_score'))['confidence_score__avg'] or 0
                crime_distribution.append({
                    'code': crime_code,
                    'name': crime_name,
                    'count': count,
                    'percentage': round((count / alerts.count() * 100) if alerts.count() > 0 else 0, 2),
                    'avg_confidence': round(avg_conf, 2)
                })
        
        # Top crime locations
        top_locations = alerts.values('location').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        # Crime severity scoring
        severity_scores = {
            'theft': 7,
            'assault': 9,
            'vandalism': 5,
            'robbery': 10,
            'suspicious_activity': 4,
            'fight': 8,
            'accident': 6,
            'weapon': 10,
            'trespassing': 3,
            'other': 2
        }
        
        total_severity = 0
        for crime in crime_distribution:
            severity = severity_scores.get(crime['code'], 5)
            total_severity += severity * crime['count']
        
        return {
            'crime_distribution': crime_distribution,
            'top_locations': list(top_locations),
            'total_severity_score': total_severity,
            'average_severity': round(total_severity / alerts.count(), 2) if alerts.count() > 0 else 0,
            'most_common_crime': crime_distribution[0] if crime_distribution else None,
            'least_common_crime': crime_distribution[-1] if crime_distribution else None
        }

    def get_temporal_analytics(self, start_date, end_date):
        """Get time-based analytics"""
        alerts = CrimeAlert.objects.filter(timestamp__gte=start_date, timestamp__lte=end_date)
        
        # Hourly distribution
        hourly_stats = alerts.annotate(
            hour=ExtractHour('timestamp')
        ).values('hour').annotate(
            count=Count('id')
        ).order_by('hour')
        
        hourly_data = {h['hour']: h['count'] for h in hourly_stats}
        
        # Find peak hours
        peak_hour = max(hourly_data.items(), key=lambda x: x[1])[0] if hourly_data else None
        peak_hour_count = hourly_data.get(peak_hour, 0) if peak_hour else 0
        
        # Daily distribution
        daily_stats = alerts.annotate(
            day=ExtractWeekDay('timestamp')
        ).values('day').annotate(
            count=Count('id')
        ).order_by('day')
        
        days_of_week = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        daily_data = {}
        for stat in daily_stats:
            day_name = days_of_week[stat['day'] - 1] if 1 <= stat['day'] <= 7 else 'Unknown'
            daily_data[day_name] = stat['count']
        
        # Find busiest day
        busiest_day = max(daily_data.items(), key=lambda x: x[1])[0] if daily_data else None
        
        # Monthly trends
        monthly_stats = alerts.annotate(
            month=TruncMonth('timestamp')
        ).values('month').annotate(
            count=Count('id')
        ).order_by('month')
        
        monthly_trends = [
            {
                'month': stat['month'].strftime('%B %Y'),
                'count': stat['count'],
                'growth': 0  # Would need previous period for growth calculation
            }
            for stat in monthly_stats
        ]
        
        return {
            'hourly_distribution': hourly_data,
            'peak_hour': peak_hour,
            'peak_hour_crimes': peak_hour_count,
            'daily_distribution': daily_data,
            'busiest_day': busiest_day,
            'monthly_trends': monthly_trends,
            'crime_rate_by_time': {
                'morning_6_12': sum(hourly_data.get(h, 0) for h in range(6, 12)),
                'afternoon_12_18': sum(hourly_data.get(h, 0) for h in range(12, 18)),
                'evening_18_24': sum(hourly_data.get(h, 0) for h in range(18, 24)),
                'night_0_6': sum(hourly_data.get(h, 0) for h in range(0, 6))
            }
        }

    def get_ai_performance_metrics(self, start_date, end_date):
        """Get AI detection performance metrics"""
        alerts = CrimeAlert.objects.filter(timestamp__gte=start_date, timestamp__lte=end_date)
        
        # Confidence score distribution
        confidence_buckets = {
            'Excellent (>90%)': alerts.filter(confidence_score__gt=90).count(),
            'Good (80-90%)': alerts.filter(confidence_score__gte=80, confidence_score__lte=90).count(),
            'Fair (70-80%)': alerts.filter(confidence_score__gte=70, confidence_score__lt=80).count(),
            'Low (<70%)': alerts.filter(confidence_score__lt=70).count()
        }
        
        # Performance by crime type
        performance_by_type = []
        for crime_code, crime_name in CrimeAlert.CRIME_TYPES:
            crime_alerts = alerts.filter(crime_type=crime_code)
            if crime_alerts.exists():
                avg_confidence = crime_alerts.aggregate(Avg('confidence_score'))['confidence_score__avg'] or 0
                performance_by_type.append({
                    'crime_type': crime_name,
                    'count': crime_alerts.count(),
                    'avg_confidence': round(avg_confidence, 2),
                    'accuracy_score': round(avg_confidence, 2)  # Using confidence as accuracy proxy
                })
        
        # Sort by confidence
        performance_by_type.sort(key=lambda x: x['avg_confidence'], reverse=True)
        
        # Detection rate over time
        detection_trend = alerts.annotate(
            date=TruncDate('timestamp')
        ).values('date').annotate(
            count=Count('id'),
            avg_confidence=Avg('confidence_score')
        ).order_by('date')[:30]  # Last 30 days
        
        return {
            'confidence_distribution': confidence_buckets,
            'performance_by_crime_type': performance_by_type,
            'best_performing_crime': performance_by_type[0] if performance_by_type else None,
            'worst_performing_crime': performance_by_type[-1] if performance_by_type else None,
            'detection_trend': list(detection_trend),
            'overall_accuracy': round(alerts.aggregate(Avg('confidence_score'))['confidence_score__avg'] or 0, 2),
            'total_detections': alerts.count()
        }

    def get_camera_analytics(self, start_date, end_date):
        """Get camera performance analytics"""
        cameras = Camera.objects.all()
        alerts = CrimeAlert.objects.filter(timestamp__gte=start_date, timestamp__lte=end_date)
        
        # Camera performance
        camera_performance = []
        for camera in cameras:
            camera_alerts = alerts.filter(camera=camera)
            camera_performance.append({
                'camera_id': camera.camera_id,
                'location': camera.location,
                'status': camera.status,
                'total_alerts': camera_alerts.count(),
                'avg_confidence': round(camera_alerts.aggregate(Avg('confidence_score'))['confidence_score__avg'] or 0, 2),
                'last_active': camera.last_active.isoformat() if camera.last_active else None
            })
        
        # Sort by alerts count
        camera_performance.sort(key=lambda x: x['total_alerts'], reverse=True)
        
        return {
            'total_cameras': cameras.count(),
            'active_cameras': cameras.filter(status='active').count(),
            'inactive_cameras': cameras.filter(status='inactive').count(),
            'maintenance_cameras': cameras.filter(status='maintenance').count(),
            'camera_performance': camera_performance[:10],  # Top 10 cameras
            'most_active_camera': camera_performance[0] if camera_performance else None
        }

    def get_response_analytics(self, start_date, end_date):
        """Get police response analytics"""
        alerts = CrimeAlert.objects.filter(
            timestamp__gte=start_date,
            timestamp__lte=end_date,
            police_response_time__isnull=False
        )
        
        response_times = []
        for alert in alerts:
            if alert.police_response_time:
                response_time = (alert.police_response_time - alert.timestamp).total_seconds() / 60
                response_times.append(response_time)
        
        if response_times:
            avg_response_time = sum(response_times) / len(response_times)
            min_response_time = min(response_times)
            max_response_time = max(response_times)
            
            # Response time distribution
            fast_response = len([t for t in response_times if t < 5])
            medium_response = len([t for t in response_times if 5 <= t < 15])
            slow_response = len([t for t in response_times if t >= 15])
        else:
            avg_response_time = 0
            min_response_time = 0
            max_response_time = 0
            fast_response = 0
            medium_response = 0
            slow_response = 0
        
        return {
            'total_responded': len(response_times),
            'average_response_time_minutes': round(avg_response_time, 2),
            'fastest_response_minutes': round(min_response_time, 2),
            'slowest_response_minutes': round(max_response_time, 2),
            'response_time_distribution': {
                'fast_under_5min': fast_response,
                'medium_5_15min': medium_response,
                'slow_over_15min': slow_response
            },
            'response_rate': round((len(response_times) / alerts.count() * 100) if alerts.count() > 0 else 0, 2)
        }

    def get_trend_analysis(self, start_date, end_date):
        """Get trend analysis and predictions"""
        alerts = CrimeAlert.objects.filter(timestamp__gte=start_date, timestamp__lte=end_date)
        
        # Calculate daily crime rate
        daily_crime_rate = alerts.annotate(
            date=TruncDate('timestamp')
        ).values('date').annotate(
            count=Count('id')
        ).order_by('-date')[:30]
        
        # Calculate weekly average
        weekly_averages = alerts.annotate(
            week=TruncDate('timestamp')
        ).values('week').annotate(
            count=Count('id')
        ).order_by('-week')[:4]
        
        # Calculate percentage change
        if len(weekly_averages) >= 2:
            current_week = weekly_averages[0]['count']
            previous_week = weekly_averages[1]['count']
            if previous_week > 0:
                percentage_change = ((current_week - previous_week) / previous_week) * 100
            else:
                percentage_change = 100 if current_week > 0 else 0
        else:
            percentage_change = 0
        
        # Simple prediction for next week (using average of last 4 weeks)
        if weekly_averages:
            next_week_prediction = int(sum(w['count'] for w in weekly_averages) / len(weekly_averages))
        else:
            next_week_prediction = 0
        
        return {
            'daily_crime_rate': list(daily_crime_rate),
            'weekly_averages': list(weekly_averages),
            'percentage_change_week_over_week': round(percentage_change, 2),
            'trend_direction': 'Increasing' if percentage_change > 0 else 'Decreasing' if percentage_change < 0 else 'Stable',
            'next_week_prediction': next_week_prediction,
            'total_crimes_last_week': weekly_averages[0]['count'] if weekly_averages else 0,
            'total_crimes_previous_week': weekly_averages[1]['count'] if len(weekly_averages) > 1 else 0
        }

    def get_predictions(self, start_date, end_date):
        """Generate simple predictions based on historical data"""
        alerts = CrimeAlert.objects.filter(timestamp__gte=start_date, timestamp__lte=end_date)
        
        # Calculate average daily crime rate
        days_diff = (end_date - start_date).days
        if days_diff > 0:
            avg_daily_crimes = alerts.count() / days_diff
        else:
            avg_daily_crimes = 0
        
        # Predict next 7 days
        predictions = []
        for i in range(1, 8):
            predicted_count = int(avg_daily_crimes * i)
            predictions.append({
                'day': i,
                'date': (end_date + timedelta(days=i)).strftime('%Y-%m-%d'),
                'predicted_crimes': predicted_count,
                'confidence_range': f"{predicted_count - 2} to {predicted_count + 2}"
            })
        
        # Identify high-risk time slots
        hourly_stats = alerts.annotate(
            hour=ExtractHour('timestamp')
        ).values('hour').annotate(
            count=Count('id')
        ).order_by('-count')[:3]  # Top 3 high-risk hours
        
        high_risk_hours = [h['hour'] for h in hourly_stats]
        
        return {
            'average_daily_crimes': round(avg_daily_crimes, 2),
            'next_7_days_predictions': predictions,
            'high_risk_hours': high_risk_hours,
            'recommended_patrol_times': high_risk_hours,
            'risk_level': 'High' if avg_daily_crimes > 10 else 'Medium' if avg_daily_crimes > 5 else 'Low'
        }

    def output_console(self, data):
        """Output analytics data to console in readable format"""
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('📊 ANALYTICS REPORT'))
        self.stdout.write('=' * 60)
        
        # Summary
        summary = data['summary']
        self.stdout.write(f"\n📈 SUMMARY STATISTICS")
        self.stdout.write(f"   Total Alerts: {summary['total_alerts']}")
        self.stdout.write(f"   Resolved: {summary['resolved_alerts']}")
        self.stdout.write(f"   Pending: {summary['pending_alerts']}")
        self.stdout.write(f"   Investigating: {summary['investigating_alerts']}")
        self.stdout.write(f"   False Alarms: {summary['false_alarms']}")
        self.stdout.write(f"   AI Accuracy: {summary['accuracy']}%")
        self.stdout.write(f"   Average Confidence: {summary['average_confidence']}%")
        
        # Crime Analytics
        crime = data['crime_analytics']
        self.stdout.write(f"\n🚨 CRIME ANALYTICS")
        self.stdout.write(f"   Most Common Crime: {crime['most_common_crime']['name'] if crime['most_common_crime'] else 'N/A'} ({crime['most_common_crime']['count'] if crime['most_common_crime'] else 0} incidents)")
        self.stdout.write(f"   Total Severity Score: {crime['total_severity_score']}")
        
        if crime['top_locations']:
            self.stdout.write(f"\n   📍 Top Locations:")
            for loc in crime['top_locations'][:5]:
                self.stdout.write(f"      - {loc['location']}: {loc['count']} incidents")
        
        # AI Performance
        ai = data['ai_performance']
        self.stdout.write(f"\n🤖 AI PERFORMANCE")
        self.stdout.write(f"   Overall Accuracy: {ai['overall_accuracy']}%")
        self.stdout.write(f"   Total Detections: {ai['total_detections']}")
        self.stdout.write(f"\n   Confidence Distribution:")
        for level, count in ai['confidence_distribution'].items():
            self.stdout.write(f"      {level}: {count}")
        
        # Predictions
        pred = data['predictions']
        self.stdout.write(f"\n🔮 PREDICTIONS")
        self.stdout.write(f"   Risk Level: {pred['risk_level']}")
        self.stdout.write(f"   Average Daily Crimes: {pred['average_daily_crimes']}")
        self.stdout.write(f"   High Risk Hours: {', '.join(map(str, pred['high_risk_hours']))}:00")
        
        self.stdout.write('\n' + '=' * 60)

    def output_json(self, data, output_file=None):
        """Output analytics data as JSON"""
        json_data = json.dumps(data, indent=2, default=str)
        
        if output_file:
            with open(output_file, 'w') as f:
                f.write(json_data)
            self.stdout.write(self.style.SUCCESS(f"\n✅ JSON data saved to: {output_file}"))
        else:
            self.stdout.write(json_data)

    def output_csv(self, data, output_file=None):
        """Output analytics data as CSV"""
        if not output_file:
            output_file = f"analytics_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        with open(output_file, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            
            # Write summary
            writer.writerow(['Analytics Report - PublicEye'])
            writer.writerow(['Generated:', datetime.now().isoformat()])
            writer.writerow([])
            
            # Write summary statistics
            writer.writerow(['SUMMARY STATISTICS'])
            writer.writerow(['Metric', 'Value'])
            for key, value in data['summary'].items():
                writer.writerow([key.replace('_', ' ').title(), value])
            
            writer.writerow([])
            
            # Write crime distribution
            writer.writerow(['CRIME DISTRIBUTION'])
            writer.writerow(['Crime Type', 'Count', 'Percentage', 'Avg Confidence'])
            for crime in data['crime_analytics']['crime_distribution']:
                writer.writerow([crime['name'], crime['count'], f"{crime['percentage']}%", f"{crime['avg_confidence']}%"])
        
        self.stdout.write(self.style.SUCCESS(f"\n✅ CSV data saved to: {output_file}"))

    def export_full_report(self, data, days):
        """Export full HTML report"""
        report_dir = Path('reports')
        report_dir.mkdir(exist_ok=True)
        
        report_file = report_dir / f"analytics_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>PublicEye Analytics Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                h1 {{ color: #dc3545; }}
                h2 {{ color: #007bff; margin-top: 30px; }}
                table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                .metric {{ font-size: 24px; font-weight: bold; color: #28a745; }}
                .summary {{ display: flex; gap: 20px; margin: 20px 0; }}
                .card {{ border: 1px solid #ddd; border-radius: 8px; padding: 20px; flex: 1; }}
            </style>
        </head>
        <body>
            <h1>📊 PublicEye Analytics Report</h1>
            <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>Analysis Period: Last {days} days</p>
            
            <div class="summary">
                <div class="card">
                    <h3>Total Alerts</h3>
                    <div class="metric">{data['summary']['total_alerts']}</div>
                </div>
                <div class="card">
                    <h3>AI Accuracy</h3>
                    <div class="metric">{data['summary']['accuracy']}%</div>
                </div>
                <div class="card">
                    <h3>Avg Response Time</h3>
                    <div class="metric">{data['response_analytics']['average_response_time_minutes']} min</div>
                </div>
            </div>
            
            <h2>🚨 Crime Distribution</h2>
            <table>
                <tr><th>Crime Type</th><th>Count</th><th>Percentage</th><th>Avg Confidence</th></tr>
        """
        
        for crime in data['crime_analytics']['crime_distribution']:
            html_content += f"<tr><td>{crime['name']}</td><td>{crime['count']}</td><td>{crime['percentage']}%</td><td>{crime['avg_confidence']}%</td></tr>"
        
        html_content += """
            </table>
            
            <h2>📈 Trends & Predictions</h2>
            <table>
                <tr><th>Metric</th><th>Value</th></tr>
                <tr><td>Trend Direction</td><td>""" + data['trends']['trend_direction'] + """</td></tr>
                <tr><td>Change (Week over Week)</td><td>""" + str(data['trends']['percentage_change_week_over_week']) + """%</td></tr>
                <tr><td>Next Week Prediction</td><td>""" + str(data['trends']['next_week_prediction']) + """ crimes</td></tr>
                <tr><td>Risk Level</td><td>""" + data['predictions']['risk_level'] + """</td></tr>
            </table>
            
            <p><em>This report was automatically generated by PublicEye Analytics System.</em></p>
        </body>
        </html>
        """
        
        with open(report_file, 'w') as f:
            f.write(html_content)
        
        self.stdout.write(self.style.SUCCESS(f"\n✅ HTML report saved to: {report_file}"))