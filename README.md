# 🚔 PublicEye - AI-Powered Crime Detection System

[![Django](https://img.shields.io/badge/Django-4.2-green.svg)](https://www.djangoproject.com/)
[![OpenCV](https://img.shields.io/badge/OpenCV-4.8-blue.svg)](https://opencv.org/)
[![Python](https://img.shields.io/badge/Python-3.8+-yellow.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-red.svg)](LICENSE)
[![WebSocket](https://img.shields.io/badge/WebSocket-Realtime-orange.svg)](https://channels.readthedocs.io/)

## 📌 Overview

PublicEye is an advanced AI-powered crime detection system designed for police departments and security agencies. It uses computer vision and machine learning to automatically detect criminal activities in real-time from CCTV cameras and uploaded video footage.

## ✨ Key Features

### 🎯 Core Detection Capabilities
- **Fight Detection** - Identifies physical altercations and fights
- **Theft/Robbery Detection** - Detects suspicious movement and theft behavior
- **Vandalism Detection** - Identifies property damage and unusual surface changes
- **Suspicious Activity** - Recognizes unusual behavior patterns
- **Weapon Detection** - Identifies potential weapons in the scene
- **Accident Detection** - Detects vehicle accidents and incidents

### 📊 Analytics & Reporting
- **Real-time Dashboard** - Live statistics and KPIs
- **Crime Trends** - Hourly, daily, and monthly crime patterns
- **Response Time Analytics** - Track police response times
- **AI Performance Metrics** - Accuracy and confidence scoring
- **Export Reports** - CSV and JSON export functionality
- **Interactive Charts** - Visual data representation with Chart.js

### 🔔 Alert System
- **WebSocket Real-time Alerts** - Instant notifications
- **Sound Alerts** - Severity-based audio alerts (Critical/Warning/Caution)
- **Browser Notifications** - Desktop push notifications
- **Toast Messages** - Non-intrusive in-app notifications
- **Popup Modals** - Detailed alert information

### 🎥 Camera Management
- **Live Camera Streaming** - Real-time video feeds
- **Multiple Camera Support** - IP cameras, USB webcams, RTSP streams
- **Camera Status Monitoring** - Active/Inactive/Maintenance status
- **Add/Edit/Delete Cameras** - Complete camera management

### 📹 Video Analysis
- **Upload Video Files** - Support for MP4, AVI, MOV, MKV formats
- **Frame-by-Frame Analysis** - Detailed video processing
- **Screenshot Capture** - Automatic evidence saving
- **Progress Tracking** - Real-time analysis progress

## 🏗️ Technology Stack

### Backend
| Technology | Version | Purpose |
|------------|---------|---------|
| Django | 4.2 | Web Framework |
| Django Channels | 4.0 | WebSocket Support |
| SQLite/MySQL | - | Database |
| OpenCV | 4.8 | Computer Vision |
| NumPy | 1.24 | Numerical Processing |

### Frontend
| Technology | Purpose |
|------------|---------|
| Bootstrap 5 | UI Framework |
| Chart.js | Data Visualization |
| WebSocket API | Real-time Communication |
| Font Awesome | Icons |

## 🔐 Default Login Credentials

After setting up the system, use these credentials to access the police dashboard:

| Field | Value |
|-------|-------|
| **Username** | `admin` |
| **Password** | `test12345` |

### How to Set Up Login Credentials

#### Method 1: Using Django Shell (Recommended)
```bash
python manage.py shell
