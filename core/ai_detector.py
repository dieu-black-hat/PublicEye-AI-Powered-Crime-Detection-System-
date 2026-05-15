import cv2
import numpy as np
import os
from django.conf import settings
import json
from datetime import datetime

class CrimeDetector:
    def __init__(self):
        self.model = None
        self.crime_classifier = None
        self.threshold = 0.7
        self.face_cascade = None
        self.body_cascade = None
        self.previous_frame = None
        self.initialize_cascades()
        
    def initialize_cascades(self):
        """Initialize OpenCV cascades for object detection"""
        try:
            # Load pre-trained classifiers for basic detection
            cascade_path = cv2.data.haarcascades
            self.face_cascade = cv2.CascadeClassifier(cascade_path + 'haarcascade_frontalface_default.xml')
            self.body_cascade = cv2.CascadeClassifier(cascade_path + 'haarcascade_fullbody.xml')
            print("Object detection cascades loaded successfully")
        except Exception as e:
            print(f"Error loading cascades: {e}")
    
    def load_model(self):
        """Load pre-trained AI model (optional - for future use)"""
        # For demo, we'll use OpenCV-based detection
        # In production, you can add YOLO, MediaPipe, etc.
        try:
            # Attempt to load a pre-trained model if exists
            model_path = os.path.join(settings.AI_MODEL_PATH, 'crime_detection_model.h5')
            if os.path.exists(model_path):
                # This would require tensorflow, but we'll skip for now
                # self.model = load_model(model_path)
                print("Model found but TensorFlow not loaded. Using OpenCV detection.")
            else:
                print("No pre-trained model found. Using OpenCV detection.")
                self.model = None
        except Exception as e:
            print(f"Error loading model: {e}")
            self.model = None
    
    def analyze_frame(self, frame):
        """Analyze a single frame for suspicious activity"""
        results = {
            'crime_detected': False,
            'crime_type': None,
            'confidence': 0.0,
            'description': '',
            'people_count': 0,
            'motion_level': 0
        }
        
        if frame is None:
            return results
        
        # Convert to grayscale for processing
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Detect faces and people
        if self.face_cascade is not None:
            faces = self.face_cascade.detectMultiScale(gray, 1.1, 5)
            results['people_count'] = len(faces)
        
        if self.body_cascade is not None:
            bodies = self.body_cascade.detectMultiScale(gray, 1.1, 5)
            results['people_count'] = max(results['people_count'], len(bodies))
        
        # Motion detection
        if self.previous_frame is not None:
            diff = cv2.absdiff(self.previous_frame, gray)
            motion_level = np.mean(diff)
            results['motion_level'] = motion_level
            
            # High motion with multiple people could indicate fight
            if motion_level > 50 and results['people_count'] >= 2:
                results['crime_detected'] = True
                results['crime_type'] = 'fight'
                results['confidence'] = min(0.95, motion_level / 100)
                results['description'] = f'High motion activity detected with {results["people_count"]} people present'
        
        # Store current frame for next iteration
        self.previous_frame = gray.copy()
        
        # Edge detection for unusual activity
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.sum(edges > 0) / edges.size
        
        # High edge density might indicate vandalism
        if edge_density > 0.3 and not results['crime_detected']:
            results['crime_detected'] = True
            results['crime_type'] = 'vandalism'
            results['confidence'] = min(0.85, edge_density)
            results['description'] = 'Unusual object or surface changes detected'
        
        # Fast movement detection (potential robbery/theft)
        if not results['crime_detected'] and results['motion_level'] > 70:
            results['crime_detected'] = True
            results['crime_type'] = 'suspicious_activity'
            results['confidence'] = min(0.80, results['motion_level'] / 100)
            results['description'] = 'Fast movement detected - possible theft or robbery'
        
        return results
    
    def analyze_video(self, video_path, callback=None):
        """Analyze entire video file for criminal activity"""
        if not os.path.exists(video_path):
            print(f"Video file not found: {video_path}")
            return None
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print(f"Could not open video file: {video_path}")
            return None
        
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        if total_frames == 0:
            print("Video has no frames")
            return None
        
        crime_events = []
        frame_count = 0
        self.previous_frame = None
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
                
            # Analyze every 30th frame to save processing
            if frame_count % 30 == 0:
                result = self.analyze_frame(frame)
                if result['crime_detected']:
                    result['timestamp'] = frame_count / fps if fps > 0 else 0
                    result['frame_number'] = frame_count
                    crime_events.append(result)
                    
                    if callback:
                        callback(result)
            
            frame_count += 1
            
            # Progress update
            if callback and frame_count % 100 == 0:
                progress = (frame_count / total_frames) * 100
                callback({'progress': progress, 'frame': frame_count, 'total': total_frames})
        
        cap.release()
        
        # Determine the most severe crime detected
        if crime_events:
            main_crime = max(crime_events, key=lambda x: x['confidence'])
            return main_crime
        
        return None
    
    def extract_frames(self, video_path, interval=30, max_frames=100):
        """Extract frames from video for analysis"""
        frames = []
        cap = cv2.VideoCapture(video_path)
        frame_count = 0
        
        while cap.isOpened() and len(frames) < max_frames:
            ret, frame = cap.read()
            if not ret:
                break
                
            if frame_count % interval == 0:
                frames.append(frame)
            frame_count += 1
            
        cap.release()
        return frames
    
    def get_frame_info(self, frame):
        """Get detailed information about a frame"""
        info = {
            'shape': frame.shape if frame is not None else None,
            'dtype': str(frame.dtype) if frame is not None else None,
            'mean_color': None,
            'brightness': None
        }
        
        if frame is not None:
            # Calculate average color
            mean_color = cv2.mean(frame)[:3]
            info['mean_color'] = {'blue': mean_color[0], 'green': mean_color[1], 'red': mean_color[2]}
            
            # Calculate brightness
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            info['brightness'] = float(np.mean(gray))
        
        return info


class SimpleCrimeDetection:
    """Fallback detection for demo purposes"""
    
    @staticmethod
    def detect_theft(frame):
        """Simple detection for theft-like behavior"""
        if frame is None:
            return {'detected': False, 'confidence': 0, 'description': 'No frame provided'}
        
        # Basic motion detection for theft
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.sum(edges > 0) / edges.size
        
        if edge_density > 0.4:
            return {
                'detected': True, 
                'confidence': min(0.75, edge_density),
                'description': 'High edge density detected - possible object removal'
            }
        
        return {'detected': False, 'confidence': 0, 'description': 'No suspicious activity'}
    
    @staticmethod
    def detect_fight(frame):
        """Simple detection for fighting"""
        if frame is None:
            return {'detected': False, 'confidence': 0, 'description': 'No frame provided'}
        
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Detect fast movement (potential fight)
        edges = cv2.Canny(gray, 50, 150)
        motion_level = np.mean(edges)
        
        if motion_level > 80:
            return {
                'detected': True,
                'confidence': min(0.85, motion_level / 120),
                'description': 'High motion detected - possible physical altercation'
            }
        
        return {'detected': False, 'confidence': 0, 'description': 'No fight detected'}
    
    @staticmethod
    def detect_violence(frame):
        """Simple detection for violent acts"""
        if frame is None:
            return {'detected': False, 'confidence': 0, 'description': 'No frame provided'}
        
        # Combine multiple detection methods
        fight_result = SimpleCrimeDetection.detect_fight(frame)
        
        if fight_result['detected']:
            return {
                'detected': True,
                'confidence': fight_result['confidence'],
                'description': f'Violent behavior detected: {fight_result["description"]}'
            }
        
        return {'detected': False, 'confidence': 0, 'description': 'No violence detected'}
    
    @staticmethod
    def detect_suspicious_activity(frame, previous_frame=None):
        """Detect suspicious behavior patterns"""
        if frame is None:
            return {'detected': False, 'confidence': 0, 'description': 'No frame provided'}
        
        results = {'detected': False, 'confidence': 0, 'description': ''}
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Loitering detection (would need temporal analysis)
        # For now, use edge detection
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.sum(edges > 0) / edges.size
        
        if 0.2 < edge_density < 0.4:
            results['detected'] = True
            results['confidence'] = 0.6
            results['description'] = 'Unusual activity pattern detected'
        
        return results