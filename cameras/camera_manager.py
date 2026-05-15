"""
Camera Manager Module for PublicEye System
Handles camera connections, video streaming, and real-time crime detection
"""

import cv2
import numpy as np
import threading
import time
import os
import json
import queue
from datetime import datetime
from pathlib import Path
import requests
from typing import Dict, List, Optional, Tuple, Any
import logging

# Setup logging
logger = logging.getLogger(__name__)

class CameraManager:
    """
    Manages multiple CCTV cameras, handles video streams,
    and performs real-time crime detection
    """
    
    def __init__(self):
        self.cameras = {}  # Dictionary to store camera instances
        self.active_streams = {}  # Active video capture objects
        self.detection_threads = {}  # Threads for each camera
        self.frame_queues = {}  # Queues for frame processing
        self.is_running = False
        self.callback_functions = []  # Callbacks for crime detection
        
        # Detection settings
        self.detection_interval = 30  # Process every 30th frame
        self.motion_threshold = 50
        self.face_cascade = None
        self.body_cascade = None
        
        # Initialize cascades
        self._initialize_cascades()
        
        logger.info("Camera Manager initialized successfully")
    
    def _initialize_cascades(self):
        """Initialize OpenCV cascades for object detection"""
        try:
            # Load pre-trained classifiers
            self.face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            )
            self.body_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_fullbody.xml'
            )
            logger.info("Object detection cascades loaded successfully")
        except Exception as e:
            logger.error(f"Error loading cascades: {e}")
    
    def add_camera(self, camera_id: str, stream_url: str, location: str = "", 
                   camera_type: str = "ip", username: str = "", password: str = "") -> bool:
        """
        Add a new camera to the system
        
        Args:
            camera_id: Unique identifier for the camera
            stream_url: RTSP/HTTP stream URL or device index (e.g., 0 for webcam)
            location: Physical location description
            camera_type: Type of camera ('ip', 'usb', 'rtsp', 'http')
            username: Username for authenticated streams
            password: Password for authenticated streams
        
        Returns:
            bool: True if camera was added successfully
        """
        try:
            camera_info = {
                'camera_id': camera_id,
                'stream_url': stream_url,
                'location': location,
                'camera_type': camera_type,
                'username': username,
                'password': password,
                'status': 'inactive',
                'added_at': datetime.now(),
                'last_frame': None,
                'frame_count': 0,
                'crime_count': 0,
                'motion_history': []
            }
            
            self.cameras[camera_id] = camera_info
            logger.info(f"Camera {camera_id} added successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error adding camera {camera_id}: {e}")
            return False
    
    def remove_camera(self, camera_id: str) -> bool:
        """
        Remove a camera from the system
        
        Args:
            camera_id: Camera identifier to remove
        
        Returns:
            bool: True if camera was removed successfully
        """
        try:
            # Stop the camera if it's running
            if camera_id in self.active_streams:
                self.stop_camera(camera_id)
            
            # Remove from dictionaries
            if camera_id in self.cameras:
                del self.cameras[camera_id]
            
            if camera_id in self.frame_queues:
                del self.frame_queues[camera_id]
            
            logger.info(f"Camera {camera_id} removed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error removing camera {camera_id}: {e}")
            return False
    
    def start_camera(self, camera_id: str) -> bool:
        """
        Start video capture for a specific camera
        
        Args:
            camera_id: Camera identifier to start
        
        Returns:
            bool: True if camera started successfully
        """
        if camera_id not in self.cameras:
            logger.error(f"Camera {camera_id} not found")
            return False
        
        if camera_id in self.active_streams:
            logger.warning(f"Camera {camera_id} is already running")
            return True
        
        try:
            camera_info = self.cameras[camera_id]
            stream_url = camera_info['stream_url']
            camera_type = camera_info['camera_type']
            
            # Open video capture based on camera type
            cap = None
            
            if camera_type == 'usb':
                # USB webcam (stream_url should be device index like '0')
                device_index = int(stream_url) if stream_url.isdigit() else 0
                cap = cv2.VideoCapture(device_index)
            else:
                # IP/RTSP/HTTP camera
                if camera_info['username'] and camera_info['password']:
                    # Add authentication to URL
                    if '@' not in stream_url:
                        # Insert credentials into URL
                        parts = stream_url.split('://')
                        if len(parts) == 2:
                            stream_url = f"{parts[0]}://{camera_info['username']}:{camera_info['password']}@{parts[1]}"
                
                cap = cv2.VideoCapture(stream_url)
            
            if not cap.isOpened():
                logger.error(f"Failed to open camera {camera_id} stream")
                return False
            
            # Store capture object
            self.active_streams[camera_id] = cap
            
            # Create frame queue for this camera
            self.frame_queues[camera_id] = queue.Queue(maxsize=10)
            
            # Update camera status
            self.cameras[camera_id]['status'] = 'active'
            
            # Start detection thread
            detection_thread = threading.Thread(
                target=self._process_camera_frames,
                args=(camera_id,),
                daemon=True
            )
            self.detection_threads[camera_id] = detection_thread
            detection_thread.start()
            
            logger.info(f"Camera {camera_id} started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error starting camera {camera_id}: {e}")
            return False
    
    def stop_camera(self, camera_id: str) -> bool:
        """
        Stop video capture for a specific camera
        
        Args:
            camera_id: Camera identifier to stop
        
        Returns:
            bool: True if camera stopped successfully
        """
        try:
            # Release video capture
            if camera_id in self.active_streams:
                self.active_streams[camera_id].release()
                del self.active_streams[camera_id]
            
            # Remove thread reference
            if camera_id in self.detection_threads:
                del self.detection_threads[camera_id]
            
            # Update camera status
            if camera_id in self.cameras:
                self.cameras[camera_id]['status'] = 'inactive'
            
            logger.info(f"Camera {camera_id} stopped successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping camera {camera_id}: {e}")
            return False
    
    def start_all_cameras(self):
        """Start all added cameras"""
        for camera_id in self.cameras:
            self.start_camera(camera_id)
        
        self.is_running = True
        logger.info("All cameras started")
    
    def stop_all_cameras(self):
        """Stop all running cameras"""
        for camera_id in list(self.active_streams.keys()):
            self.stop_camera(camera_id)
        
        self.is_running = False
        logger.info("All cameras stopped")
    
    def _process_camera_frames(self, camera_id: str):
        """
        Process frames from a camera in a separate thread
        
        Args:
            camera_id: Camera identifier
        """
        cap = self.active_streams.get(camera_id)
        if not cap:
            return
        
        frame_count = 0
        previous_frame = None
        
        while camera_id in self.active_streams and cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                logger.warning(f"Failed to read frame from camera {camera_id}")
                time.sleep(0.1)
                continue
            
            frame_count += 1
            self.cameras[camera_id]['frame_count'] = frame_count
            self.cameras[camera_id]['last_frame'] = datetime.now()
            
            # Process every Nth frame for detection
            if frame_count % self.detection_interval == 0:
                # Perform crime detection
                detection_result = self.analyze_frame(frame, previous_frame, camera_id)
                
                if detection_result and detection_result.get('crime_detected'):
                    # Crime detected! Trigger callbacks
                    detection_result['camera_id'] = camera_id
                    detection_result['timestamp'] = datetime.now().isoformat()
                    detection_result['location'] = self.cameras[camera_id]['location']
                    
                    # Save frame with crime
                    self._save_crime_frame(frame, detection_result, camera_id)
                    
                    # Increment crime counter
                    self.cameras[camera_id]['crime_count'] += 1
                    
                    # Notify all callbacks
                    self._notify_callbacks(detection_result)
                    
                    logger.warning(f"CRIME DETECTED on camera {camera_id}: {detection_result['crime_type']}")
                
                # Update motion history
                if previous_frame is not None:
                    motion_level = self._calculate_motion(previous_frame, frame)
                    self.cameras[camera_id]['motion_history'].append(motion_level)
                    # Keep only last 100 motion values
                    if len(self.cameras[camera_id]['motion_history']) > 100:
                        self.cameras[camera_id]['motion_history'].pop(0)
            
            previous_frame = frame.copy()
            
            # Add frame to queue for streaming (if needed)
            if camera_id in self.frame_queues:
                try:
                    # Don't block if queue is full
                    self.frame_queues[camera_id].put_nowait(frame)
                except queue.Full:
                    pass
            
            # Small delay to prevent CPU overuse
            time.sleep(0.01)
    
    def analyze_frame(self, frame: np.ndarray, previous_frame: np.ndarray = None, 
                      camera_id: str = "") -> Dict[str, Any]:
        """
        Analyze a single frame for criminal activity
        
        Args:
            frame: Current video frame
            previous_frame: Previous frame for motion detection
            camera_id: Camera identifier
        
        Returns:
            dict: Detection results
        """
        results = {
            'crime_detected': False,
            'crime_type': None,
            'confidence': 0.0,
            'description': '',
            'people_count': 0,
            'motion_level': 0,
            'objects_detected': []
        }
        
        if frame is None:
            return results
        
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Detect faces
            if self.face_cascade is not None:
                faces = self.face_cascade.detectMultiScale(gray, 1.1, 5)
                results['people_count'] = len(faces)
                results['objects_detected'].extend([{'type': 'face', 'count': len(faces)}])
            
            # Detect bodies
            if self.body_cascade is not None:
                bodies = self.body_cascade.detectMultiScale(gray, 1.1, 5)
                results['people_count'] = max(results['people_count'], len(bodies))
                results['objects_detected'].append({'type': 'body', 'count': len(bodies)})
            
            # Motion detection
            if previous_frame is not None:
                prev_gray = cv2.cvtColor(previous_frame, cv2.COLOR_BGR2GRAY)
                motion_level = self._calculate_motion(prev_gray, gray)
                results['motion_level'] = motion_level
                
                # High motion with multiple people = potential fight
                if motion_level > self.motion_threshold and results['people_count'] >= 2:
                    results['crime_detected'] = True
                    results['crime_type'] = 'fight'
                    results['confidence'] = min(0.95, motion_level / 100)
                    results['description'] = f'High motion detected with {results["people_count"]} people present'
            
            # Edge detection for vandalism/unusual objects
            if not results['crime_detected']:
                edges = cv2.Canny(gray, 50, 150)
                edge_density = np.sum(edges > 0) / edges.size
                
                if edge_density > 0.3:
                    results['crime_detected'] = True
                    results['crime_type'] = 'vandalism'
                    results['confidence'] = min(0.85, edge_density)
                    results['description'] = 'Unusual object or surface changes detected'
            
            # Suspicious behavior detection (loitering, running, etc.)
            if not results['crime_detected'] and len(self.cameras.get(camera_id, {}).get('motion_history', [])) > 10:
                avg_motion = np.mean(self.cameras[camera_id]['motion_history'][-10:])
                if avg_motion > 30 and results['people_count'] > 0:
                    results['crime_detected'] = True
                    results['crime_type'] = 'suspicious_activity'
                    results['confidence'] = min(0.75, avg_motion / 100)
                    results['description'] = 'Unusual movement pattern detected'
            
        except Exception as e:
            logger.error(f"Error analyzing frame: {e}")
        
        return results
    
    def _calculate_motion(self, prev_frame: np.ndarray, curr_frame: np.ndarray) -> float:
        """
        Calculate motion level between two frames
        
        Args:
            prev_frame: Previous frame
            curr_frame: Current frame
        
        Returns:
            float: Motion level (0-255)
        """
        try:
            diff = cv2.absdiff(prev_frame, curr_frame)
            motion = np.mean(diff)
            return float(motion)
        except Exception as e:
            logger.error(f"Error calculating motion: {e}")
            return 0.0
    
    def _save_crime_frame(self, frame: np.ndarray, detection_result: Dict, camera_id: str):
        """
        Save frame where crime was detected
        
        Args:
            frame: Video frame
            detection_result: Detection results
            camera_id: Camera identifier
        """
        try:
            # Create directory for crime frames
            crime_dir = Path(f"media/crime_screenshots/{datetime.now().strftime('%Y/%m/%d')}")
            crime_dir.mkdir(parents=True, exist_ok=True)
            
            # Annotate frame with detection info
            annotated_frame = frame.copy()
            
            # Add text overlay
            cv2.putText(annotated_frame, f"CRIME: {detection_result['crime_type'].upper()}", 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            cv2.putText(annotated_frame, f"Confidence: {detection_result['confidence']:.2%}", 
                       (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            cv2.putText(annotated_frame, f"Camera: {camera_id}", 
                       (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
            cv2.putText(annotated_frame, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 
                       (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
            
            # Draw rectangle around the frame
            cv2.rectangle(annotated_frame, (0, 0), 
                         (annotated_frame.shape[1], annotated_frame.shape[0]), 
                         (0, 0, 255), 3)
            
            # Generate filename
            filename = f"crime_{camera_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            filepath = crime_dir / filename
            
            # Save annotated frame
            cv2.imwrite(str(filepath), annotated_frame)
            
            # Store filepath in detection result
            detection_result['screenshot_path'] = str(filepath)
            
            logger.info(f"Crime frame saved: {filepath}")
            
        except Exception as e:
            logger.error(f"Error saving crime frame: {e}")
    
    def register_callback(self, callback_func):
        """
        Register a callback function to be called when crime is detected
        
        Args:
            callback_func: Function to call with detection results
        """
        self.callback_functions.append(callback_func)
        logger.info("Callback function registered")
    
    def _notify_callbacks(self, detection_result: Dict):
        """
        Notify all registered callbacks about crime detection
        
        Args:
            detection_result: Detection results
        """
        for callback in self.callback_functions:
            try:
                callback(detection_result)
            except Exception as e:
                logger.error(f"Error in callback: {e}")
    
    def get_camera_status(self, camera_id: str = None) -> Dict:
        """
        Get status of cameras
        
        Args:
            camera_id: Specific camera ID or None for all
        
        Returns:
            dict: Camera status information
        """
        if camera_id:
            if camera_id in self.cameras:
                return self.cameras[camera_id]
            else:
                return {'error': 'Camera not found'}
        else:
            return self.cameras
    
    def get_frame(self, camera_id: str) -> Optional[np.ndarray]:
        """
        Get the latest frame from a camera
        
        Args:
            camera_id: Camera identifier
        
        Returns:
            numpy.ndarray: Latest frame or None
        """
        if camera_id in self.frame_queues:
            try:
                # Get frame without blocking
                return self.frame_queues[camera_id].get_nowait()
            except queue.Empty:
                return None
        return None
    
    def save_camera_snapshot(self, camera_id: str) -> Optional[str]:
        """
        Save a snapshot from a camera
        
        Args:
            camera_id: Camera identifier
        
        Returns:
            str: Path to saved snapshot or None
        """
        frame = self.get_frame(camera_id)
        if frame is not None:
            try:
                snapshot_dir = Path("media/camera_snapshots")
                snapshot_dir.mkdir(parents=True, exist_ok=True)
                
                filename = f"snapshot_{camera_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                filepath = snapshot_dir / filename
                
                cv2.imwrite(str(filepath), frame)
                return str(filepath)
            except Exception as e:
                logger.error(f"Error saving snapshot: {e}")
        
        return None
    
    def get_statistics(self) -> Dict:
        """
        Get overall statistics for all cameras
        
        Returns:
            dict: Statistics summary
        """
        stats = {
            'total_cameras': len(self.cameras),
            'active_cameras': len(self.active_streams),
            'total_crimes_detected': sum(cam.get('crime_count', 0) for cam in self.cameras.values()),
            'total_frames_processed': sum(cam.get('frame_count', 0) for cam in self.cameras.values()),
            'cameras': {}
        }
        
        for cam_id, cam_info in self.cameras.items():
            stats['cameras'][cam_id] = {
                'status': cam_info.get('status', 'unknown'),
                'location': cam_info.get('location', ''),
                'crime_count': cam_info.get('crime_count', 0),
                'frame_count': cam_info.get('frame_count', 0),
                'last_active': cam_info.get('last_frame', None)
            }
        
        return stats
    
    def update_camera_settings(self, camera_id: str, settings: Dict) -> bool:
        """
        Update camera settings
        
        Args:
            camera_id: Camera identifier
            settings: Dictionary of settings to update
        
        Returns:
            bool: True if updated successfully
        """
        if camera_id not in self.cameras:
            logger.error(f"Camera {camera_id} not found")
            return False
        
        try:
            # Update allowed settings
            allowed_keys = ['location', 'stream_url', 'username', 'password']
            for key, value in settings.items():
                if key in allowed_keys and key in self.cameras[camera_id]:
                    self.cameras[camera_id][key] = value
            
            # Restart camera if stream_url changed
            if 'stream_url' in settings and camera_id in self.active_streams:
                self.stop_camera(camera_id)
                self.start_camera(camera_id)
            
            logger.info(f"Camera {camera_id} settings updated")
            return True
            
        except Exception as e:
            logger.error(f"Error updating camera settings: {e}")
            return False
    
    def set_detection_parameters(self, motion_threshold: int = None, 
                                  detection_interval: int = None):
        """
        Update crime detection parameters
        
        Args:
            motion_threshold: New motion threshold value
            detection_interval: New detection interval (frames)
        """
        if motion_threshold is not None:
            self.motion_threshold = motion_threshold
            logger.info(f"Motion threshold updated to {motion_threshold}")
        
        if detection_interval is not None:
            self.detection_interval = detection_interval
            logger.info(f"Detection interval updated to {detection_interval}")


# Example usage and integration with Django
class CameraManagerIntegration:
    """
    Integration class to connect CameraManager with Django models
    """
    
    def __init__(self):
        self.manager = CameraManager()
        self._setup_callbacks()
    
    def _setup_callbacks(self):
        """Setup callbacks to save detections to database"""
        def on_crime_detected(detection_result):
            # This will be called when crime is detected
            # You can save to Django models here
            from core.models import CrimeAlert, Camera
            
            try:
                # Get or create camera in database
                camera, created = Camera.objects.get_or_create(
                    camera_id=detection_result['camera_id'],
                    defaults={
                        'location': detection_result.get('location', 'Unknown'),
                        'status': 'active'
                    }
                )
                
                # Create crime alert
                alert = CrimeAlert.objects.create(
                    camera=camera,
                    crime_type=detection_result['crime_type'],
                    confidence_score=detection_result['confidence'] * 100,
                    location=detection_result.get('location', camera.location),
                    description=detection_result.get('description', 'Crime detected by AI'),
                    reported_to_police=True
                )
                
                logger.info(f"Crime alert saved to database: {alert.alert_id}")
                
            except Exception as e:
                logger.error(f"Error saving crime alert to database: {e}")
        
        self.manager.register_callback(on_crime_detected)
    
    def start_system(self):
        """Start the entire camera system"""
        self.manager.start_all_cameras()
    
    def stop_system(self):
        """Stop the entire camera system"""
        self.manager.stop_all_cameras()
    
    def add_camera_from_model(self, camera_model):
        """
        Add a camera from Django model
        
        Args:
            camera_model: Camera model instance
        """
        return self.manager.add_camera(
            camera_id=camera_model.camera_id,
            stream_url=camera_model.stream_url or f"http://{camera_model.ip_address}/video",
            location=camera_model.location,
            camera_type='ip' if camera_model.ip_address else 'usb'
        )


# Singleton instance for global access
camera_manager_instance = CameraManager()

# Example usage
if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Create camera manager
    manager = CameraManager()
    
    # Add a camera (example: webcam)
    manager.add_camera(
        camera_id="CAM_001",
        stream_url="0",  # 0 for default webcam
        location="Main Entrance",
        camera_type="usb"
    )
    
    # Register callback for crime detection
    def crime_callback(result):
        print(f"\n🚨 CRIME ALERT! 🚨")
        print(f"Camera: {result.get('camera_id')}")
        print(f"Crime Type: {result.get('crime_type')}")
        print(f"Confidence: {result.get('confidence')}")
        print(f"Description: {result.get('description')}")
        print(f"Time: {result.get('timestamp')}\n")
    
    manager.register_callback(crime_callback)
    
    # Start camera
    manager.start_camera("CAM_001")
    
    # Run for 60 seconds
    try:
        time.sleep(60)
    except KeyboardInterrupt:
        print("\nStopping camera...")
    finally:
        manager.stop_camera("CAM_001")
        print("Camera stopped")