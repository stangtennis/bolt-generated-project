#!/usr/bin/env python3

# Monkey patch before any other imports
import eventlet
eventlet.monkey_patch()

import os
import sys
import ssl
import json
import time
import socket
import secrets
import logging
import requests
import traceback
from datetime import datetime
from typing import Optional, Dict, Any

import numpy as np
from flask import Flask, render_template, request, redirect, url_for, session, Response, jsonify
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from PIL import Image, ImageGrab
import io
import base64
import mss
import mss.tools
from session_manager import SessionManager
from input_handler import InputHandler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(32)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max file size

# CORS configuration
CORS(app, resources={
    r"/*": {
        "origins": "*",
        "allow_headers": "*",
        "expose_headers": "*",
        "methods": ["GET", "POST", "OPTIONS"],
        "supports_credentials": True
    }
})

# Initialize Socket.IO with CORS and WebSocket configuration
socketio_server = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode='eventlet',
    logger=True,
    engineio_logger=True,
    ping_timeout=120,  # Increase timeouts for slower connections
    ping_interval=30,
    max_http_buffer_size=1e8,  # 100MB max http buffer size
    async_handlers=True,
    reconnection=True,
    reconnection_attempts=10,
    reconnection_delay=1000,
    reconnection_delay_max=5000,
    handle_sigint=False,  # Don't let socketio handle Ctrl+C
    transports=['websocket']  # Force WebSocket only
)

# STUN/TURN server configuration
STUN_SERVERS = [
    "stun:stun.l.google.com:19302",
    "stun:stun1.l.google.com:19302",
    "stun:stun2.l.google.com:19302",
    "stun:stun3.l.google.com:19302",
    "stun:stun4.l.google.com:19302"
]

def get_turn_server():
    """Get TURN server credentials from a service like Twilio or your own TURN server"""
    # For testing, we'll use a free TURN server. In production, use your own TURN server
    return {
        'urls': 'turn:openrelay.metered.ca:443',
        'username': 'openrelayproject',
        'credential': 'openrelayproject'
    }

def get_public_ip():
    """Get public IP address"""
    try:
        response = requests.get('https://api.ipify.org?format=json', timeout=5)
        if response.status_code == 200:
            return response.json()['ip']
        else:
            logger.error(f"Error getting public IP: HTTP {response.status_code}")
            return get_local_ip()
    except Exception as e:
        logger.error(f"Error getting public IP: {e}")
        return get_local_ip()

def get_local_ip():
    """Get local IP address"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception as e:
        logger.error(f"Error getting local IP: {e}")
        return "127.0.0.1"

# Screen capture configuration
QUALITY_SETTINGS = {
    1: {'quality': 10, 'resize': 0.25},  # Low quality
    2: {'quality': 30, 'resize': 0.5},   # Medium quality
    3: {'quality': 50, 'resize': 0.75},  # High quality
    4: {'quality': 70, 'resize': 1.0}    # Best quality
}

def capture_screen() -> bytes:
    """Capture screen and return as JPEG bytes"""
    try:
        with mss.mss() as sct:
            # Capture primary monitor
            monitor = sct.monitors[1]
            screenshot = sct.grab(monitor)
            
            # Convert to PIL Image
            img = Image.frombytes('RGB', screenshot.size, screenshot.rgb)
            
            # Convert to JPEG
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='JPEG', quality=70)
            img_byte_arr.seek(0)
            
            return img_byte_arr.getvalue()
    except Exception as e:
        logger.error(f"Error capturing screen: {e}")
        return b''

def process_frame(frame_bytes: bytes, quality_level: int = 4) -> str:
    """Process frame with quality settings and return as base64"""
    try:
        # Get quality settings
        settings = QUALITY_SETTINGS.get(quality_level, QUALITY_SETTINGS[4])
        quality = settings['quality']
        resize = settings['resize']
        
        # Open image
        img = Image.open(io.BytesIO(frame_bytes))
        
        # Resize if needed
        if resize < 1.0:
            new_size = tuple(int(dim * resize) for dim in img.size)
            img = img.resize(new_size, Image.Resampling.LANCZOS)
        
        # Convert to JPEG
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='JPEG', quality=quality)
        img_byte_arr.seek(0)
        
        # Convert to base64
        return base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')
    except Exception as e:
        logger.error(f"Error processing frame: {e}")
        return ''

# Initialize managers
session_manager = SessionManager()
input_handler = InputHandler()

@app.after_request
def add_header(response):
    """Add headers to allow screen capture and other features"""
    response.headers['X-UA-Compatible'] = 'IE=Edge,chrome=1'
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, X-Requested-With, Authorization'
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response

@app.route('/')
def index():
    """Render the main page"""
    logger.info("Serving index page")
    return render_template('index.html')

@app.route('/controller')
def controller():
    """Render the controller page"""
    logger.info("Serving controller page")
    return render_template('controller.html')

@app.route('/connection-info')
def get_connection_info():
    """Get connection information including STUN/TURN servers."""
    try:
        # Get STUN/TURN servers
        ice_servers = [{'urls': server} for server in STUN_SERVERS]
        turn_server = get_turn_server()
        if turn_server:
            ice_servers.append(turn_server)
        
        # Get local and public IPs
        local_ip = get_local_ip()
        public_ip = get_public_ip()
        
        response = {
            'publicIp': public_ip,
            'localIp': local_ip,
            'iceServers': ice_servers,
            'wsProtocol': 'wss',  # Always use secure WebSocket
            'serverTime': datetime.now().isoformat()
        }
        logger.info("Connection info response ready")
        logger.debug(f"Connection info: {response}")
        return jsonify(response)
    except Exception as e:
        logger.error(f"Error getting connection info: {str(e)}")
        return jsonify({'error': str(e)}), 500

@socketio_server.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    try:
        client_sid = request.sid
        logger.info(f"Client disconnected: {client_sid}")
        
        # Clean up any sessions this client was part of
        session_manager.remove_client(client_sid)
        
        # Broadcast updated session list
        broadcast_sessions()
        
    except Exception as e:
        logger.error(f"Error handling disconnect: {e}")
        traceback.print_exc()

@socketio_server.on('connect')
def handle_connect():
    """Handle client connection"""
    try:
        client_sid = request.sid
        logger.info(f"Client connected: {client_sid}")
        
        # Create a default session for this client
        session_id = session_manager.create_session(client_sid, f"User_{client_sid[:6]}")
        
        # Broadcast updated session list
        broadcast_sessions()
        
        # Send connection info
        emit('connection_info', {
            'client_id': client_sid,
            'session_id': session_id
        })
        
    except Exception as e:
        logger.error(f"Error handling connect: {e}")
        traceback.print_exc()
        emit('error', {'message': str(e)})

@socketio_server.on('create_session')
def handle_create_session(data):
    """Handle session creation request"""
    try:
        client_name = data.get('client_name', 'Unknown')
        session_id = session_manager.create_session(request.sid, client_name)
        
        # Initialize input handler for the session
        session = session_manager.get_session(session_id)
        if session:
            session.input_handler = InputHandler()
            session.quality = 4  # Start with best quality
        
        logger.info(f"Created session {session_id} for client {client_name}")
        emit('session_created', {'session_id': session_id})
        broadcast_sessions()
    except Exception as e:
        logger.error(f"Error creating session: {str(e)}")
        emit('error', {'message': str(e)})

@socketio_server.on('request_sessions')
def handle_session_request():
    """Send list of active sessions"""
    try:
        sessions = session_manager.get_sessions()
        emit('sessions_list', sessions)
    except Exception as e:
        logger.error(f"Error handling session request: {e}")
        emit('error', {'message': str(e)})

@socketio_server.on('join_session')
def handle_join_session(data):
    """Handle session join request"""
    try:
        session_id = data.get('session_id')
        if not session_id:
            logger.error("No session_id provided")
            emit('error', {'message': 'No session_id provided'})
            return
            
        if session_manager.join_session(session_id, request.sid):
            # Initialize input handler if not exists
            session = session_manager.get_session(session_id)
            if session and not hasattr(session, 'input_handler'):
                session.input_handler = InputHandler()
                session.quality = 4  # Start with best quality
            
            logger.info(f"Client {request.sid} joined session {session_id}")
            emit('joined_session', {'session_id': session_id})
            broadcast_sessions()
        else:
            logger.error(f"Failed to join session {session_id}")
            emit('error', {'message': 'Failed to join session'})
    except Exception as e:
        logger.error(f"Error joining session: {str(e)}")
        emit('error', {'message': str(e)})

@socketio_server.on('leave_session')
def handle_leave_session(data):
    """Handle session leave request"""
    try:
        session_id = data.get('session_id')
        session_manager.leave_session(session_id, request.sid)
        emit('left_session', {'session_id': session_id})
        logger.info(f"Client {request.sid} left session {session_id}")
    except Exception as e:
        logger.error(f"Error leaving session: {e}")
        emit('error', {'message': str(e)})

@socketio_server.on('keyboard_event')
def handle_keyboard_event(data):
    """Handle keyboard events from controller"""
    try:
        # Validate session ID
        session_id = data.get('session_id')
        if not session_id:
            logger.error("No session_id provided for keyboard event")
            return
            
        # Get sharer's socket ID and validate
        sharer_sid = session_manager.get_session_sharer(session_id)
        if not sharer_sid:
            logger.error(f"No sharer found for session {session_id}")
            return

        # Get event data
        key = data.get('key', '')
        event_type = data.get('type')
        
        if not key or not event_type:
            logger.error("Missing key or event type in keyboard event")
            return
            
        logger.debug(f"Processing keyboard event: {key} ({event_type})")
        
        # Handle special key combinations
        if key.startswith('Control+'):
            if key == 'Control+c':
                input_handler.copy_to_clipboard()
                logger.debug("Processed copy to clipboard")
            elif key == 'Control+v':
                input_handler.paste_from_clipboard()
                logger.debug("Processed paste from clipboard")
            else:
                input_handler.send_key(key, event_type == 'down')
                logger.debug(f"Processed special key combination: {key}")
        else:
            input_handler.send_key(key, event_type == 'down')
            logger.debug(f"Processed regular key: {key}")
            
    except Exception as e:
        logger.error(f"Error handling keyboard event: {str(e)}")
        emit('error', {'message': str(e)})

@socketio_server.on('request_frame')
def handle_frame_request(data):
    """Handle frame request from controller"""
    try:
        # Validate session ID
        session_id = data.get('session_id')
        if not session_id:
            logger.error("No session_id provided for frame request")
            return
            
        # Get session and validate
        session = session_manager.get_session(session_id)
        if not session:
            logger.error(f"No session found for ID {session_id}")
            return
            
        # Get quality setting
        quality = getattr(session, 'quality', 4)
        
        # Capture and process frame
        frame_bytes = capture_screen()
        if frame_bytes:
            frame_base64 = process_frame(frame_bytes, quality)
            if frame_base64:
                emit('frame', {
                    'image': frame_base64,
                    'timestamp': time.time(),
                    'quality': quality
                })
    except Exception as e:
        logger.error(f"Error handling frame request: {e}")
        emit('error', {'message': str(e)})

@socketio_server.on('set_quality')
def handle_set_quality(data):
    """Handle quality change request"""
    try:
        session_id = data.get('session_id')
        quality = int(data.get('quality', 4))
        
        if session_id and quality in QUALITY_SETTINGS:
            session = session_manager.get_session(session_id)
            if session:
                session.quality = quality
                logger.info(f"Set quality to {quality} for session {session_id}")
                emit('quality_changed', {'quality': quality})
    except Exception as e:
        logger.error(f"Error setting quality: {e}")
        emit('error', {'message': str(e)})

def broadcast_sessions():
    """Broadcast active sessions to all clients"""
    try:
        sessions = session_manager.get_sessions()
        socketio_server.emit('sessions_list', sessions)
    except Exception as e:
        logger.error(f"Error broadcasting sessions: {e}")

if __name__ == "__main__":
    try:
        # Get local and public IPs
        local_ip = get_local_ip()
        public_ip = get_public_ip()
        logger.info(f"Local IP: {local_ip}")
        logger.info(f"Public IP: {public_ip}")
        
        PORT = 5000
        cert_path = os.path.join('certs', 'cert.pem')
        key_path = os.path.join('certs', 'key.pem')
        
        # Verify certificate files exist
        if not os.path.exists(cert_path):
            raise FileNotFoundError(f"Certificate file not found: {cert_path}")
        if not os.path.exists(key_path):
            raise FileNotFoundError(f"Key file not found: {key_path}")
            
        logger.info(f"Using certificate: {cert_path}")
        logger.info(f"Using private key: {key_path}")
        
        # Print access information
        print("\nAccess the application at:")
        print(f"Local: https://localhost:{PORT}")
        print(f"LAN:   https://{local_ip}:{PORT}")
        print(f"WAN:   https://{public_ip}:{PORT}")
        print("\nNote: For WAN access, make sure port {PORT} is forwarded to this machine\n")
        
        # Configure monkey patching for SSL
        eventlet.monkey_patch(socket=True, select=True, thread=True)
        
        # Start server with SSL
        logger.info("Starting server with SSL...")
        socketio_server.run(
            app,
            host='0.0.0.0',
            port=PORT,
            certfile=cert_path,
            keyfile=key_path,
            debug=False,  # Disable debug to avoid reloader
            log_output=True,
            use_reloader=False  # Disable reloader to avoid duplicate processes
        )
        
    except Exception as e:
        logger.error(f"Server error: {e}")
        traceback.print_exc()
        sys.exit(1)
