// static/js/main.js
// PublicEye - Real-time Crime Alert System with Sound Alarms

// ============================================================
// WEBSOCKET CONNECTION FOR REAL-TIME ALERTS
// ============================================================

let socket = null;
let audioContext = null;
let reconnectAttempts = 0;
let maxReconnectAttempts = 5;
let reconnectInterval = 3000;
let alertSound = null;
let connectionTimeout = null;
let isSoundEnabled = true;

// Initialize WebSocket connection
function initWebSocket() {
    // Don't try to connect on login or home page
    const currentPath = window.location.pathname;
    if (currentPath === '/login/' || currentPath === '/' || currentPath === '') {
        console.log('Not on authenticated page, skipping WebSocket');
        return;
    }
    
    // Check if WebSocket is already connected
    if (socket && socket.readyState === WebSocket.OPEN) {
        console.log('WebSocket already connected');
        return;
    }
    
    const wsScheme = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
    const wsUrl = `${wsScheme}${window.location.host}/ws/alerts/`;
    
    console.log('Connecting to WebSocket:', wsUrl);
    
    try {
        socket = new WebSocket(wsUrl);
        
        // Set connection timeout
        connectionTimeout = setTimeout(() => {
            if (socket && socket.readyState !== WebSocket.OPEN) {
                console.log('WebSocket connection timeout');
                if ($('#ws-status').length) {
                    $('#ws-status').removeClass('bg-secondary').addClass('bg-warning');
                    $('#ws-status').html('<i class="fas fa-clock"></i> Timeout');
                }
                socket.close();
            }
        }, 5000);
        
        socket.onopen = function(e) {
            console.log('✅ WebSocket connected successfully');
            clearTimeout(connectionTimeout);
            reconnectAttempts = 0;
            
            // Update status indicator
            if ($('#ws-status').length) {
                $('#ws-status').removeClass('bg-secondary bg-danger bg-warning').addClass('bg-success');
                $('#ws-status').html('<i class="fas fa-plug"></i> ● Live');
            }
            
            // Send ping every 30 seconds to keep connection alive
            if (window.pingInterval) clearInterval(window.pingInterval);
            window.pingInterval = setInterval(() => {
                if (socket && socket.readyState === WebSocket.OPEN) {
                    socket.send(JSON.stringify({ type: 'ping' }));
                    console.log('💓 Ping sent');
                }
            }, 30000);
        };
        
        socket.onmessage = function(e) {
            console.log('📨 Message received:', e.data.substring(0, 100));
            try {
                const data = JSON.parse(e.data);
                
                if (data.type === 'crime_alert') {
                    // New crime detected!
                    console.log('🚨 CRIME ALERT RECEIVED:', data.alert);
                    
                    // Get severity based on crime type and confidence
                    const severity = getCrimeSeverity(data.alert.crime_code, data.alert.confidence);
                    
                    // Play sound alarm based on severity
                    playCrimeAlertSound(severity);
                    
                    // Show all types of alerts
                    showCrimeAlertPopup(data.alert);
                    showBrowserNotification(data.alert);
                    showToastNotification(data.alert);
                    updateAlertCounters();
                    
                    // Flash the page title
                    flashPageTitle('🚨 CRIME ALERT! 🚨');
                    
                    // Vibrate for mobile devices on high severity
                    if (severity === 'high' && navigator.vibrate) {
                        navigator.vibrate([500, 200, 500, 200, 1000]);
                    } else if (navigator.vibrate) {
                        navigator.vibrate([200, 100, 200]);
                    }
                    
                    // Add to alert list if on alerts page
                    if (window.location.pathname === '/alerts/') {
                        addAlertToTable(data.alert);
                    }
                } 
                else if (data.type === 'connection_established') {
                    console.log('✅ Connected to alert system:', data.message);
                    showToast({
                        message: 'Connected to real-time alert system',
                        type: 'success',
                        duration: 3000
                    });
                }
                else if (data.type === 'recent_alerts') {
                    console.log(`📋 Received ${data.count} recent alerts`);
                    if (data.count > 0 && window.location.pathname === '/dashboard/') {
                        showRecentAlertsToast(data.alerts);
                    }
                }
                else if (data.type === 'pong') {
                    console.log('💓 Heartbeat received');
                }
                else if (data.type === 'stats_update') {
                    console.log('📊 Stats updated:', data.stats);
                    updateDashboardStats(data.stats);
                }
                
            } catch (error) {
                console.error('Error parsing message:', error);
            }
        };
        
        socket.onclose = function(e) {
            console.log(`WebSocket disconnected. Code: ${e.code}, Reason: ${e.reason}`);
            clearTimeout(connectionTimeout);
            
            // Update status indicator
            if ($('#ws-status').length) {
                $('#ws-status').removeClass('bg-success bg-warning').addClass('bg-danger');
                $('#ws-status').html('<i class="fas fa-plug"></i> ● Offline');
            }
            
            // Attempt to reconnect
            if (reconnectAttempts < maxReconnectAttempts) {
                reconnectAttempts++;
                const delay = reconnectInterval * reconnectAttempts;
                console.log(`Reconnecting in ${delay/1000}s... (Attempt ${reconnectAttempts}/${maxReconnectAttempts})`);
                setTimeout(initWebSocket, delay);
            } else {
                console.error('Failed to reconnect WebSocket after multiple attempts');
                showConnectionError();
            }
        };
        
        socket.onerror = function(e) {
            console.error('WebSocket error:', e);
            clearTimeout(connectionTimeout);
            if ($('#ws-status').length) {
                $('#ws-status').removeClass('bg-secondary').addClass('bg-danger');
                $('#ws-status').html('<i class="fas fa-exclamation-triangle"></i> Error');
            }
        };
        
    } catch (error) {
        console.error('WebSocket initialization error:', error);
        if ($('#ws-status').length) {
            $('#ws-status').removeClass('bg-secondary').addClass('bg-danger');
            $('#ws-status').html('<i class="fas fa-exclamation-triangle"></i> Error');
        }
    }
}

// ============================================================
// SOUND ALARM SYSTEM
// ============================================================

// Initialize Audio Context
function initAudioContext() {
    if (!audioContext) {
        audioContext = new (window.AudioContext || window.webkitAudioContext)();
    }
    return audioContext;
}

// Get severity level based on crime type and confidence
function getCrimeSeverity(crimeType, confidence) {
    const highSeverity = ['fight', 'assault', 'robbery', 'weapon', 'shooting', 'armed_robbery'];
    const mediumSeverity = ['theft', 'vandalism', 'trespassing', 'burglary'];
    const lowSeverity = ['suspicious_activity', 'accident', 'noise_complaint'];
    
    if (highSeverity.includes(crimeType) || confidence > 90) {
        return 'high';
    } else if (mediumSeverity.includes(crimeType) || confidence > 75) {
        return 'medium';
    } else {
        return 'low';
    }
}

// Play Crime Alert Sound based on severity
function playCrimeAlertSound(severity = 'high') {
    if (!isSoundEnabled) return;
    
    try {
        const context = initAudioContext();
        
        // Resume if suspended (browser policy)
        if (context.state === 'suspended') {
            context.resume();
        }
        
        const now = context.currentTime;
        
        if (severity === 'high') {
            // High severity - Multiple loud beeps (Fight, Robbery, Weapon)
            playHighSeverityAlert(context, now);
            playAlertSiren(context, now);
        } else if (severity === 'medium') {
            // Medium severity - Two beeps (Theft, Vandalism)
            playMediumSeverityAlert(context, now);
        } else {
            // Low severity - Single beep (Suspicious activity)
            playLowSeverityAlert(context, now);
        }
        
        console.log(`🔊 Playing ${severity} severity alert sound`);
        
    } catch (e) {
        console.log("Audio error:", e);
        // Fallback to simple beep
        playSimpleBeep();
    }
}

// High Severity Alert (Urgent - for fight, robbery, weapon)
function playHighSeverityAlert(context, startTime) {
    // First beep
    const osc1 = context.createOscillator();
    const gain1 = context.createGain();
    osc1.connect(gain1);
    gain1.connect(context.destination);
    osc1.frequency.value = 880;
    gain1.gain.value = 0.5;
    osc1.start(startTime);
    gain1.gain.exponentialRampToValueAtTime(0.00001, startTime + 0.3);
    osc1.stop(startTime + 0.3);
    
    // Second beep (higher pitch)
    const osc2 = context.createOscillator();
    const gain2 = context.createGain();
    osc2.connect(gain2);
    gain2.connect(context.destination);
    osc2.frequency.value = 1046.50; // C6
    gain2.gain.value = 0.5;
    osc2.start(startTime + 0.4);
    gain2.gain.exponentialRampToValueAtTime(0.00001, startTime + 0.7);
    osc2.stop(startTime + 0.7);
    
    // Third beep (highest pitch)
    const osc3 = context.createOscillator();
    const gain3 = context.createGain();
    osc3.connect(gain3);
    gain3.connect(context.destination);
    osc3.frequency.value = 1174.66; // D6
    gain3.gain.value = 0.5;
    osc3.start(startTime + 0.8);
    gain3.gain.exponentialRampToValueAtTime(0.00001, startTime + 1.1);
    osc3.stop(startTime + 1.1);
}

// Medium Severity Alert (Theft, Vandalism)
function playMediumSeverityAlert(context, startTime) {
    // First beep
    const osc1 = context.createOscillator();
    const gain1 = context.createGain();
    osc1.connect(gain1);
    gain1.connect(context.destination);
    osc1.frequency.value = 880;
    gain1.gain.value = 0.4;
    osc1.start(startTime);
    gain1.gain.exponentialRampToValueAtTime(0.00001, startTime + 0.3);
    osc1.stop(startTime + 0.3);
    
    // Second beep
    const osc2 = context.createOscillator();
    const gain2 = context.createGain();
    osc2.connect(gain2);
    gain2.connect(context.destination);
    osc2.frequency.value = 880;
    gain2.gain.value = 0.4;
    osc2.start(startTime + 0.5);
    gain2.gain.exponentialRampToValueAtTime(0.00001, startTime + 0.8);
    osc2.stop(startTime + 0.8);
}

// Low Severity Alert (Suspicious activity)
function playLowSeverityAlert(context, startTime) {
    const osc = context.createOscillator();
    const gain = context.createGain();
    osc.connect(gain);
    gain.connect(context.destination);
    osc.frequency.value = 660;
    gain.gain.value = 0.3;
    osc.start(startTime);
    gain.gain.exponentialRampToValueAtTime(0.00001, startTime + 0.5);
    osc.stop(startTime + 0.5);
}

// Siren sound for serious crimes
function playAlertSiren(context, startTime) {
    const oscillator = context.createOscillator();
    const gain = context.createGain();
    const now = startTime;
    
    oscillator.connect(gain);
    gain.connect(context.destination);
    
    oscillator.type = 'sine';
    gain.gain.value = 0.3;
    
    // Create siren effect (frequency sweep)
    oscillator.frequency.setValueAtTime(440, now);
    oscillator.frequency.linearRampToValueAtTime(880, now + 0.5);
    oscillator.frequency.linearRampToValueAtTime(440, now + 1);
    oscillator.frequency.linearRampToValueAtTime(880, now + 1.5);
    oscillator.frequency.linearRampToValueAtTime(440, now + 2);
    
    oscillator.start(now);
    gain.gain.exponentialRampToValueAtTime(0.00001, now + 2.5);
    oscillator.stop(now + 2.5);
}

// Simple beep fallback
function playSimpleBeep() {
    try {
        const audio = new Audio();
        audio.src = "data:audio/wav;base64,U3RlYWx0aCBzb3VuZCBub3QgYXZhaWxhYmxl";
        audio.volume = 0.5;
        audio.play().catch(e => console.log("Audio play failed:", e));
    } catch(e) {
        console.log("Could not play sound");
    }
}

// Toggle sound on/off
function toggleSound() {
    isSoundEnabled = !isSoundEnabled;
    const soundBtn = $('#soundToggle');
    if (isSoundEnabled) {
        soundBtn.html('<i class="fas fa-volume-up"></i> Sound On');
        soundBtn.removeClass('btn-secondary').addClass('btn-success');
        showToastMessage('Sound alerts enabled', 'success');
    } else {
        soundBtn.html('<i class="fas fa-volume-mute"></i> Sound Off');
        soundBtn.removeClass('btn-success').addClass('btn-secondary');
        showToastMessage('Sound alerts disabled', 'info');
    }
    localStorage.setItem('soundEnabled', isSoundEnabled);
}

// Initialize sound settings from localStorage
function initSoundSettings() {
    const saved = localStorage.getItem('soundEnabled');
    if (saved !== null) {
        isSoundEnabled = saved === 'true';
    }
    
    // Update sound toggle button if exists
    const soundBtn = $('#soundToggle');
    if (soundBtn.length) {
        if (isSoundEnabled) {
            soundBtn.html('<i class="fas fa-volume-up"></i> Sound On');
            soundBtn.removeClass('btn-secondary').addClass('btn-success');
        } else {
            soundBtn.html('<i class="fas fa-volume-mute"></i> Sound Off');
            soundBtn.removeClass('btn-success').addClass('btn-secondary');
        }
    }
}

// Test sound function
function testSoundAlarm() {
    playCrimeAlertSound('high');
    showToastMessage('🔊 Testing sound alarm', 'info');
}

// Enable audio context on user interaction
function enableAudioOnUserInteraction() {
    const events = ['click', 'touchstart', 'keydown'];
    events.forEach(event => {
        document.addEventListener(event, function initAudio() {
            if (audioContext && audioContext.state === 'suspended') {
                audioContext.resume();
                console.log('🎵 Audio context resumed');
            }
            events.forEach(e => document.removeEventListener(e, initAudio));
        });
    });
}

// ============================================================
// UPDATE DASHBOARD STATS
// ============================================================

function updateDashboardStats(stats) {
    if (stats) {
        if ($('.total-alerts-count').length) {
            animateValue($('.total-alerts-count'), 
                parseInt($('.total-alerts-count').text()) || 0, 
                stats.total_alerts || 0, 
                500);
        }
        if ($('.pending-alerts-count').length) {
            animateValue($('.pending-alerts-count'),
                parseInt($('.pending-alerts-count').text()) || 0,
                stats.pending_alerts || 0,
                500);
        }
    }
}

// ============================================================
// ALERT POPUP MODAL
// ============================================================

function showCrimeAlertPopup(alert) {
    const severity = getCrimeSeverity(alert.crime_code, alert.confidence);
    const severityColor = severity === 'high' ? '#dc3545' : (severity === 'medium' ? '#ffc107' : '#17a2b8');
    const severityText = severity === 'high' ? 'CRITICAL' : (severity === 'medium' ? 'WARNING' : 'CAUTION');
    const confidenceClass = alert.confidence > 80 ? 'danger' : (alert.confidence > 60 ? 'warning' : 'info');
    
    const modalHtml = `
        <div id="crimeAlertModal" class="modal fade" data-bs-backdrop="static" data-bs-keyboard="false">
            <div class="modal-dialog modal-lg modal-dialog-centered modal-dialog-scrollable">
                <div class="modal-content border-${severity === 'high' ? 'danger' : 'warning'}">
                    <div class="modal-header bg-${severity === 'high' ? 'danger' : severity === 'medium' ? 'warning' : 'info'} text-white">
                        <h5 class="modal-title">
                            <i class="fas fa-exclamation-triangle fa-pulse"></i> 
                            🚨 CRIME ALERT! - ${severityText}
                        </h5>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="alert alert-${severity === 'high' ? 'danger' : 'warning'}">
                            <strong><i class="fas fa-flag"></i> Crime Detected:</strong> 
                            <span class="badge bg-${severity === 'high' ? 'danger' : 'warning'} fs-6">${alert.crime_type}</span>
                        </div>
                        
                        <div class="row">
                            <div class="col-md-6">
                                <p><strong><i class="fas fa-chart-line"></i> Confidence:</strong></p>
                                <div class="progress mb-3" style="height: 25px;">
                                    <div class="progress-bar bg-${confidenceClass} progress-bar-striped progress-bar-animated" 
                                         role="progressbar" 
                                         style="width: ${alert.confidence}%;">
                                        ${alert.confidence.toFixed(1)}%
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-6">
                                <p><strong><i class="fas fa-clock"></i> Time:</strong></p>
                                <p>${alert.timestamp || new Date().toLocaleString()}</p>
                            </div>
                        </div>
                        
                        <div class="row">
                            <div class="col-12">
                                <p><strong><i class="fas fa-map-marker-alt"></i> Location:</strong></p>
                                <p><code>${alert.location || 'Unknown location'}</code></p>
                            </div>
                        </div>
                        
                        <div class="row">
                            <div class="col-12">
                                <p><strong><i class="fas fa-info-circle"></i> Description:</strong></p>
                                <p class="alert alert-info">${alert.description || 'Suspicious activity detected by AI'}</p>
                            </div>
                        </div>
                        
                        ${alert.screenshot_url ? `
                        <div class="row">
                            <div class="col-12">
                                <p><strong><i class="fas fa-camera"></i> Screenshot:</strong></p>
                                <img src="${alert.screenshot_url}" class="img-fluid rounded border" style="max-height: 200px;">
                            </div>
                        </div>
                        ` : ''}
                        
                        <div class="alert alert-warning mt-3">
                            <i class="fas fa-bell"></i> 
                            <strong>Action Required:</strong> Please review this alert immediately.
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
                            <i class="fas fa-times"></i> Dismiss
                        </button>
                        <a href="${alert.url || `/alert/${alert.alert_id}/`}" class="btn btn-${severity === 'high' ? 'danger' : 'warning'}">
                            <i class="fas fa-eye"></i> View Details
                        </a>
                        <button type="button" class="btn btn-success" onclick="acknowledgeAlert('${alert.alert_id}')">
                            <i class="fas fa-check"></i> Acknowledge
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Remove existing modal if any
    if ($('#crimeAlertModal').length) {
        $('#crimeAlertModal').remove();
    }
    
    // Add modal to body
    $('body').append(modalHtml);
    
    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('crimeAlertModal'));
    modal.show();
    
    // Auto-hide after 15 seconds
    setTimeout(() => {
        if ($('#crimeAlertModal').length) {
            const modalInstance = bootstrap.Modal.getInstance(document.getElementById('crimeAlertModal'));
            if (modalInstance) modalInstance.hide();
        }
    }, 15000);
    
    // Play additional alert animation
    $('body').addClass('alert-flash');
    setTimeout(() => $('body').removeClass('alert-flash'), 1000);
}

// ============================================================
// BROWSER NOTIFICATION
// ============================================================

function showBrowserNotification(alert) {
    if (!("Notification" in window)) {
        console.log("Browser does not support notifications");
        return;
    }
    
    if (Notification.permission === "granted") {
        const notification = new Notification("🚨 PublicEye Crime Alert!", {
            body: `${alert.crime_type} detected!\nLocation: ${alert.location || 'Unknown'}\nConfidence: ${alert.confidence.toFixed(1)}%`,
            icon: "/static/images/alert-icon.png",
            tag: alert.alert_id,
            requireInteraction: true,
            vibrate: [200, 100, 200, 100, 300],
            silent: false
        });
        
        notification.onclick = function() {
            window.focus();
            window.location.href = alert.url || `/alert/${alert.alert_id}/`;
            notification.close();
        };
        
        // Auto close after 10 seconds
        setTimeout(() => notification.close(), 10000);
        
    } else if (Notification.permission !== "denied") {
        Notification.requestPermission();
    }
}

// ============================================================
// TOAST NOTIFICATION
// ============================================================

function showToastNotification(alert) {
    const severity = getCrimeSeverity(alert.crime_code, alert.confidence);
    const bgClass = severity === 'high' ? 'bg-danger' : (severity === 'medium' ? 'bg-warning' : 'bg-info');
    
    const toastHtml = `
        <div id="crimeToast" class="toast align-items-center text-white ${bgClass} border-0" role="alert" 
             data-bs-autohide="true" data-bs-delay="7000">
            <div class="d-flex">
                <div class="toast-body">
                    <i class="fas fa-exclamation-triangle fa-fw me-2"></i>
                    <strong>${alert.crime_type}</strong> detected at ${alert.location || 'unknown location'}
                    <br>
                    <small>Confidence: ${alert.confidence.toFixed(1)}%</small>
                </div>
                <div class="toast-footer">
                    <a href="${alert.url || `/alert/${alert.alert_id}/`}" class="btn btn-sm btn-light m-2">
                        View
                    </a>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
                </div>
            </div>
        </div>
    `;
    
    // Remove existing toast
    $('#crimeToast').remove();
    
    // Add toast to container
    const toastContainer = $('#toastContainer');
    if (!toastContainer.length) {
        $('body').append('<div id="toastContainer" class="position-fixed bottom-0 end-0 p-3" style="z-index: 9999;"></div>');
    }
    
    $('#toastContainer').append(toastHtml);
    
    // Show toast
    const toast = new bootstrap.Toast(document.getElementById('crimeToast'));
    toast.show();
    
    // Auto remove after hiding
    setTimeout(() => $('#crimeToast').remove(), 8000);
}

// ============================================================
// GENERIC TOAST NOTIFICATION
// ============================================================

function showToastMessage(message, type = 'info') {
    const bgClass = type === 'success' ? 'bg-success' : (type === 'error' ? 'bg-danger' : 'bg-info');
    const icon = type === 'success' ? 'check-circle' : (type === 'error' ? 'exclamation-triangle' : 'info-circle');
    
    const toastHtml = `
        <div class="toast align-items-center text-white ${bgClass} border-0" role="alert" 
             data-bs-autohide="true" data-bs-delay="3000">
            <div class="d-flex">
                <div class="toast-body">
                    <i class="fas fa-${icon} me-2"></i>
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        </div>
    `;
    
    if (!$('#toastContainer').length) {
        $('body').append('<div id="toastContainer" class="position-fixed bottom-0 end-0 p-3" style="z-index: 9999;"></div>');
    }
    
    $('#toastContainer').append(toastHtml);
    const toast = new bootstrap.Toast($('#toastContainer .toast').last());
    toast.show();
    
    setTimeout(() => {
        $('#toastContainer .toast').last().remove();
    }, 3000);
}

function showToast(options) {
    showToastMessage(options.message, options.type || 'info');
}

// ============================================================
// FLASH PAGE TITLE
// ============================================================

let originalTitle = document.title;
let titleInterval = null;

function flashPageTitle(alertText) {
    if (titleInterval) clearInterval(titleInterval);
    
    let flashCount = 0;
    titleInterval = setInterval(() => {
        document.title = flashCount % 2 === 0 ? alertText : originalTitle;
        flashCount++;
        
        if (flashCount > 10) {
            clearInterval(titleInterval);
            document.title = originalTitle;
            titleInterval = null;
        }
    }, 500);
}

// ============================================================
// UPDATE ALERT COUNTERS
// ============================================================

function updateAlertCounters() {
    $.ajax({
        url: '/api/stats/',
        method: 'GET',
        success: function(data) {
            if (data.total_alerts) {
                $('.alert-badge').text(data.total_alerts).show();
                $('.pending-badge').text(data.by_status?.['Pending Review'] || 0);
            }
        },
        error: function() {
            console.log('Could not fetch updated stats');
        }
    });
}

// ============================================================
// ACKNOWLEDGE ALERT
// ============================================================

function acknowledgeAlert(alertId) {
    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({
            type: 'acknowledge_alert',
            alert_id: alertId
        }));
    }
    
    const modal = document.getElementById('crimeAlertModal');
    if (modal) {
        const modalInstance = bootstrap.Modal.getInstance(modal);
        if (modalInstance) modalInstance.hide();
    }
    
    showToastMessage('Alert acknowledged', 'success');
}

// ============================================================
// SHOW RECENT ALERTS ON DASHBOARD
// ============================================================

function showRecentAlertsToast(alerts) {
    if (alerts && alerts.length > 0) {
        const recentCount = alerts.length;
        const mostRecent = alerts[0];
        
        showToastMessage(`You have ${recentCount} recent alert(s). Most recent: ${mostRecent.crime_type}`, 'warning');
    }
}

// ============================================================
// ADD ALERT TO TABLE
// ============================================================

function addAlertToTable(alert) {
    const newRow = `
        <tr class="table-danger">
            <td><strong>${alert.alert_id}</strong></td>
            <td>${alert.crime_type}</td>
            <td>${alert.location || 'Unknown'}</td>
            <td>
                <div class="progress" style="height: 20px;">
                    <div class="progress-bar bg-danger" style="width: ${alert.confidence}%;">
                        ${alert.confidence.toFixed(1)}%
                    </div>
                </div>
            </td>
            <td><span class="badge bg-danger">Pending</span></td>
            <td>Just now</td>
            <td><a href="/alert/${alert.alert_id}/" class="btn btn-sm btn-primary">View</a></td>
        </tr>
    `;
    
    $('#alerts-table tbody').prepend(newRow);
    $('#alerts-table tr:first').addClass('alert-highlight');
    setTimeout(() => $('#alerts-table tr:first').removeClass('alert-highlight'), 3000);
}

// ============================================================
// SHOW CONNECTION ERROR
// ============================================================

function showConnectionError() {
    showToastMessage('⚠️ Real-time alert connection lost. Using polling fallback.', 'danger');
}

// ============================================================
// AUTO-REFRESH ALERTS (FALLBACK)
// ============================================================

function refreshAlerts() {
    if (window.location.pathname === '/alerts/') {
        if (!socket || socket.readyState !== WebSocket.OPEN) {
            location.reload();
        }
    }
}

setInterval(refreshAlerts, 30000);

// ============================================================
// REAL-TIME DASHBOARD UPDATES
// ============================================================

function updateStats() {
    $.ajax({
        url: '/api/stats/',
        method: 'GET',
        success: function(data) {
            console.log('Stats updated:', data);
            if ($('.total-alerts-count').length) {
                $('.total-alerts-count').text(data.total_alerts || 0);
            }
            if ($('.pending-alerts-count').length) {
                $('.pending-alerts-count').text(data.by_status?.['Pending Review'] || 0);
            }
        },
        error: function(xhr, status, error) {
            console.error('Stats update failed:', error);
        }
    });
}

setInterval(updateStats, 60000);

// ============================================================
// CONFIRMATION DIALOGS
// ============================================================

$(document).on('click', '.delete-btn, .btn-delete, [data-confirm]', function(e) {
    const message = $(this).data('confirm') || 'Are you sure you want to delete this item?';
    if (!confirm(message)) {
        e.preventDefault();
        return false;
    }
    return true;
});

// ============================================================
// VIDEO UPLOAD PREVIEW
// ============================================================

$(document).on('change', '#video_file, input[type="file"]', function() {
    const file = this.files[0];
    if (file && file.type.startsWith('video/')) {
        const reader = new FileReader();
        reader.onload = function(e) {
            const previewContainer = $('#video-preview-container, .video-preview');
            const preview = $('#video-preview, video');
            
            if (preview.length) {
                preview.attr('src', e.target.result);
                previewContainer.show();
            }
        };
        reader.readAsDataURL(file);
    }
});

// ============================================================
// LIVE CAMERA FEED REFRESH
// ============================================================

function refreshLiveFeed(cameraId) {
    const imgElement = $(`#cam-${cameraId}, .live-feed-${cameraId}`);
    if (imgElement.length) {
        imgElement.attr('src', `/stream/${cameraId}/?t=${new Date().getTime()}`);
    }
}

setInterval(() => {
    $('[data-live-feed]').each(function() {
        const cameraId = $(this).data('camera-id');
        if (cameraId) refreshLiveFeed(cameraId);
    });
}, 5000);

// ============================================================
// CRIME TYPE COLOR MAPPING
// ============================================================

const crimeColors = {
    'theft': '#ffc107',
    'assault': '#dc3545',
    'vandalism': '#fd7e14',
    'robbery': '#dc3545',
    'suspicious_activity': '#ffc107',
    'fight': '#dc3545',
    'accident': '#0dcaf0',
    'weapon': '#dc3545',
    'trespassing': '#fd7e14',
    'other': '#6c757d'
};

function getCrimeColor(crimeType) {
    return crimeColors[crimeType] || '#6c757d';
}

// ============================================================
// DISPLAY CRIME ALERT NOTIFICATION (LEGACY)
// ============================================================

function showCrimeAlert(alertData) {
    if (Notification.permission === 'granted') {
        new Notification('PublicEye Crime Alert', {
            body: `${alertData.crime_type} detected at ${alertData.location}`,
            icon: '/static/images/alert-icon.png',
            tag: alertData.alert_id || Date.now().toString(),
            requireInteraction: true
        });
    }
}

// ============================================================
// REQUEST NOTIFICATION PERMISSION
// ============================================================

if (Notification.permission === 'default') {
    $(document).one('click', function() {
        Notification.requestPermission();
    });
    
    setTimeout(() => {
        if (Notification.permission === 'default') {
            Notification.requestPermission();
        }
    }, 5000);
}

// ============================================================
// DASHBOARD STATS ANIMATION
// ============================================================

function animateValue(element, start, end, duration) {
    if (!element.length) return;
    const range = end - start;
    const increment = range / (duration / 16);
    let current = start;
    const timer = setInterval(() => {
        current += increment;
        if ((increment > 0 && current >= end) || (increment < 0 && current <= end)) {
            element.text(Math.round(end));
            clearInterval(timer);
        } else {
            element.text(Math.round(current));
        }
    }, 16);
}

// ============================================================
// INITIALIZE ON PAGE LOAD
// ============================================================

$(document).ready(function() {
    console.log('PublicEye System Initialized');
    console.log('Current path:', window.location.pathname);
    
    // Initialize sound settings
    initSoundSettings();
    
    // Enable audio on user interaction
    enableAudioOnUserInteraction();
    
    // Initialize WebSocket (only on pages that need real-time alerts)
    if (window.location.pathname !== '/login/' && window.location.pathname !== '/') {
        console.log('Initializing WebSocket...');
        setTimeout(initWebSocket, 1000);
    } else {
        console.log('Skipping WebSocket on public page');
    }
    
    // Add WebSocket status indicator to navbar if not exists
    if ($('.navbar').length && !$('#ws-status').length) {
        $('.navbar .ms-auto').prepend(`
            <span id="ws-status" class="badge bg-secondary me-3" style="font-size: 11px; cursor: pointer;" title="Connection Status">
                <i class="fas fa-plug"></i> Connecting...
            </span>
        `);
    }
    
    // Add sound toggle button to navbar if not exists
    if ($('.navbar').length && !$('#soundToggle').length) {
        $('.navbar .ms-auto').append(`
            <li class="nav-item me-2">
                <button id="soundToggle" class="btn btn-sm btn-success" onclick="toggleSound()" title="Toggle Sound Alerts">
                    <i class="fas fa-volume-up"></i> Sound On
                </button>
            </li>
        `);
    }
    
    // Add CSS for animations
    if (!$('#alert-styles').length) {
        $('head').append(`
            <style id="alert-styles">
                @keyframes alertFlash {
                    0%, 100% { background-color: transparent; }
                    50% { background-color: rgba(220, 53, 69, 0.1); }
                }
                body.alert-flash { animation: alertFlash 1s ease-in-out; }
                .alert-highlight { animation: highlightRow 3s ease-in-out; }
                @keyframes highlightRow {
                    0%, 100% { background-color: transparent; }
                    50% { background-color: rgba(220, 53, 69, 0.2); }
                }
                .toast { opacity: 0.95; box-shadow: 0 4px 12px rgba(0,0,0,0.15); }
                .toast:hover { opacity: 1; }
                #ws-status { cursor: pointer; transition: all 0.3s ease; }
                #ws-status:hover { transform: scale(1.05); }
                .progress-bar { transition: width 0.5s ease; }
                #soundToggle { transition: all 0.3s ease; }
                #soundToggle:hover { transform: scale(1.05); }
            </style>
        `);
    }
    
    // Auto-hide alerts after 10 seconds on dashboard
    if (window.location.pathname === '/dashboard/') {
        setTimeout(() => {
            $('.alert').fadeOut('slow');
        }, 10000);
    }
    
    // Test sound on first user interaction (optional)
    $(document).one('click', function() {
        if (isSoundEnabled && audioContext && audioContext.state === 'suspended') {
            playCrimeAlertSound('low');
        }
    });
});

// ============================================================
// EXPORT FUNCTIONS FOR GLOBAL ACCESS
// ============================================================

window.showCrimeAlertPopup = showCrimeAlertPopup;
window.acknowledgeAlert = acknowledgeAlert;
window.showToast = showToast;
window.showToastMessage = showToastMessage;
window.refreshLiveFeed = refreshLiveFeed;
window.getCrimeColor = getCrimeColor;
window.initWebSocket = initWebSocket;
window.toggleSound = toggleSound;
window.testSoundAlarm = testSoundAlarm;
window.playCrimeAlertSound = playCrimeAlertSound;
window.getCrimeSeverity = getCrimeSeverity;