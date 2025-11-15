# -*- coding: utf-8 -*-

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file, make_response, Response, stream_with_context
import os
import uuid
import qrcode
import io
import json
import socket
import threading
import time
from werkzeug.utils import secure_filename
from utils.ocr_processor import extract_phone_info
from utils.predictor import predict_issue_and_solution
from utils.log_generator import generate_device_log
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from functools import wraps
from collections import defaultdict
import re

app = Flask(__name__)
# Rotate secret key each start so any previous session cookies become invalid
app.secret_key = os.urandom(32)
app.config['DEBUG'] = True
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # Disable caching during development

@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
app.jinja_env.auto_reload = True

# Configure logging
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database initialization
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL,
                  email TEXT UNIQUE NOT NULL,
                  password TEXT NOT NULL)''')
    conn.commit()
    conn.close()

# Create database and tables
init_db()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Configure upload folder
UPLOAD_FOLDER = os.path.join('static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure required directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(os.path.join('static', 'phone_data'), exist_ok=True)

# In-memory session store with TTL (30 minutes)
class SessionStore:
    def __init__(self, ttl_minutes=30):
        self.sessions = {}  # { sid: { snapshot?: Snapshot, live?: Live, createdAt: number } }
        self.ttl = timedelta(minutes=ttl_minutes)
        self.lock = threading.Lock()
        self.subscribers = defaultdict(list)  # session_id -> list of callbacks (for SSE)
        
    def create_session(self, session_id):
        with self.lock:
            if session_id not in self.sessions:
                self.sessions[session_id] = {
                    'snapshot': None,
                    'live': None,
                    'createdAt': int(time.time() * 1000)  # milliseconds timestamp
                }
                app.logger.info(f"Created session: {session_id}")
    
    def get_session(self, session_id):
        with self.lock:
            if session_id not in self.sessions:
                return None
            sess = self.sessions[session_id]
            # Check TTL (createdAt is in milliseconds)
            created_at = datetime.fromtimestamp(sess['createdAt'] / 1000)
            if datetime.now() - created_at > self.ttl:
                del self.sessions[session_id]
                if session_id in self.subscribers:
                    del self.subscribers[session_id]
                return None
            return sess
    
    def set_snapshot(self, session_id, snapshot):
        with self.lock:
            if session_id not in self.sessions:
                self.create_session(session_id)
            sess = self.sessions[session_id]
            sess['snapshot'] = snapshot
            app.logger.info(f"Snapshot saved for session: {session_id}")
            # Broadcast to SSE subscribers
            self._broadcast(session_id, {'type': 'snapshot', 'data': snapshot})
    
    def set_live(self, session_id, live_data):
        with self.lock:
            if session_id not in self.sessions:
                self.create_session(session_id)
            sess = self.sessions[session_id]
            sess['live'] = live_data
            # Broadcast to SSE subscribers
            self._broadcast(session_id, {'type': 'battery', 'data': live_data})
    
    def _broadcast(self, session_id, message):
        """Broadcast message to all SSE subscribers for this session"""
        callbacks = self.subscribers.get(session_id, [])
        app.logger.info(f"Broadcasting to {len(callbacks)} subscribers for session {session_id}: {message.get('type', 'unknown')}")
        for callback in callbacks:
            try:
                callback(message)
            except Exception as e:
                app.logger.error(f"Error in subscriber callback: {e}")
    
    def subscribe(self, session_id, callback):
        with self.lock:
            self.subscribers[session_id].append(callback)
            app.logger.info(f"Subscribed to session {session_id} (total subscribers: {len(self.subscribers[session_id])})")
    
    def unsubscribe(self, session_id, callback):
        with self.lock:
            if callback in self.subscribers[session_id]:
                self.subscribers[session_id].remove(callback)
                app.logger.info(f"Unsubscribed from session {session_id} (remaining: {len(self.subscribers[session_id])})")
    
    def cleanup_expired(self):
        """Remove expired sessions"""
        with self.lock:
            now = datetime.now()
            expired = []
            for sid, sess in self.sessions.items():
                created_at = datetime.fromtimestamp(sess['createdAt'] / 1000)
                if now - created_at > self.ttl:
                    expired.append(sid)
            for sid in expired:
                del self.sessions[sid]
                if sid in self.subscribers:
                    del self.subscribers[sid]
            if expired:
                app.logger.info(f"Cleaned up {len(expired)} expired sessions")

# Global session store
session_store = SessionStore(ttl_minutes=30)

# Share token store: { token: { session_id: str, expires_at: datetime } }
share_tokens = {}
share_tokens_lock = threading.Lock()

def generate_share_token():
    """Generate a random share token"""
    return uuid.uuid4().hex[:16]  # 16 character token

def create_share_token(session_id):
    """Create a share token for a session (24 hour expiry)"""
    token = generate_share_token()
    expires_at = datetime.now() + timedelta(hours=24)
    with share_tokens_lock:
        share_tokens[token] = {
            'session_id': session_id,
            'expires_at': expires_at
        }
    return token

def get_share_token(token):
    """Get session_id for a share token if valid"""
    with share_tokens_lock:
        if token in share_tokens:
            token_data = share_tokens[token]
            if datetime.now() < token_data['expires_at']:
                return token_data['session_id']
            else:
                # Expired, remove it
                del share_tokens[token]
    return None

def cleanup_expired_share_tokens():
    """Remove expired share tokens"""
    now = datetime.now()
    with share_tokens_lock:
        expired = [token for token, data in share_tokens.items() if now >= data['expires_at']]
        for token in expired:
            del share_tokens[token]

# Cleanup thread
def cleanup_worker():
    while True:
        time.sleep(300)  # Run every 5 minutes
        session_store.cleanup_expired()
        cleanup_expired_share_tokens()

cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
cleanup_thread.start()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Performance score calculation with new weighting
def compute_performance_score(data):
    """
    Compute performance score with weighting:
    30% RAM, 30% Storage, 20% Battery, 20% OS recency
    """
    def parse_numeric(text, default=0):
        if not text or text == 'Unknown':
            return default
        if isinstance(text, (int, float)):
            return float(text)
        match = re.search(r'(\d+(?:\.\d+)?)', str(text))
        return float(match.group(1)) if match else default
    
    def clamp(v, lo, hi):
        return max(lo, min(hi, v))
    
    # Extract RAM (deviceMemory in GB)
    ram_gb = 0
    if 'deviceMemory' in data and data['deviceMemory']:
        ram_gb = parse_numeric(data['deviceMemory'])
    elif 'ram' in data:
        ram_gb = parse_numeric(data['ram'])
    elif 'ramSizeGB' in data:
        ram_gb = parse_numeric(data['ramSizeGB'])
    
    # RAM score: tier-based (0-2GB=0-30, 2-4GB=30-50, 4-6GB=50-70, 6-8GB=70-85, 8GB+=85-100)
    if ram_gb <= 2:
        ram_score = clamp((ram_gb / 2.0) * 30, 0, 30)
    elif ram_gb <= 4:
        ram_score = 30 + ((ram_gb - 2) / 2.0) * 20
    elif ram_gb <= 6:
        ram_score = 50 + ((ram_gb - 4) / 2.0) * 20
    elif ram_gb <= 8:
        ram_score = 70 + ((ram_gb - 6) / 2.0) * 15
    else:
        ram_score = 85 + clamp(((ram_gb - 8) / 4.0) * 15, 0, 15)
    ram_score = clamp(ram_score, 0, 100)
    
    # Extract Storage (browser sandbox - free/total from estimate)
    storage_score = 50  # Default
    if 'storage' in data and data['storage']:
        storage_info = data['storage']
        if isinstance(storage_info, dict):
            # Use new sandbox format if available
            if 'storageSandboxQuotaMB' in storage_info and 'storageSandboxUsedMB' in storage_info:
                quota_mb = storage_info.get('storageSandboxQuotaMB', 0)
                used_mb = storage_info.get('storageSandboxUsedMB', 0)
                if quota_mb > 0:
                    free_pct = ((quota_mb - used_mb) / quota_mb) * 100
                    # Score based on free percentage: 0-20%=0-40, 20-40%=40-70, 40-60%=70-90, 60%+=90-100
                    if free_pct < 20:
                        storage_score = (free_pct / 20.0) * 40
                    elif free_pct < 40:
                        storage_score = 40 + ((free_pct - 20) / 20.0) * 30
                    elif free_pct < 60:
                        storage_score = 70 + ((free_pct - 40) / 20.0) * 20
                    else:
                        storage_score = 90 + clamp(((free_pct - 60) / 40.0) * 10, 0, 10)
            # Fallback to old format (quota/usage in bytes)
            elif 'quota' in storage_info:
                quota = storage_info.get('quota', 0)
                usage = storage_info.get('usage', 0)
                if quota > 0:
                    free_pct = ((quota - usage) / quota) * 100
                    # Score based on free percentage: 0-20%=0-40, 20-40%=40-70, 40-60%=70-90, 60%+=90-100
                    if free_pct < 20:
                        storage_score = (free_pct / 20.0) * 40
                    elif free_pct < 40:
                        storage_score = 40 + ((free_pct - 20) / 20.0) * 30
                    elif free_pct < 60:
                        storage_score = 70 + ((free_pct - 40) / 20.0) * 20
                    else:
                        storage_score = 90 + clamp(((free_pct - 60) / 40.0) * 10, 0, 10)
        else:
            # Try to parse as GB (legacy format)
            storage_gb = parse_numeric(storage_info)
            if storage_gb > 0:
                storage_score = clamp((storage_gb / 128.0) * 100, 0, 100)
    storage_score = clamp(storage_score, 0, 100)
    
    # Extract Battery (level with charging bonus)
    battery_score = 50  # Default
    battery_level = None
    is_charging = False
    
    if 'battery' in data:
        battery_info = data['battery']
        if isinstance(battery_info, dict):
            battery_level = battery_info.get('level')
            is_charging = battery_info.get('charging', False)
        else:
            battery_level = parse_numeric(battery_info)
    elif 'batteryLevel' in data:
        battery_level = parse_numeric(data['batteryLevel'])
        is_charging = data.get('charging', False)
    
    if battery_level is not None:
        battery_score = float(battery_level)  # 0-100
        # Small charging bonus: +5 points if charging
        if is_charging:
            battery_score = min(100, battery_score + 5)
    battery_score = clamp(battery_score, 0, 100)
    
    # Extract OS version (recency proxy)
    os_score = 50  # Default
    os_version = None
    if 'os_version' in data:
        os_version = data['os_version']
    elif 'androidVersion' in data:
        os_version = data['androidVersion']
    elif 'platform' in data:
        os_version = data['platform']
    
    if os_version:
        # Extract version number
        version_num = parse_numeric(os_version)
        if version_num > 0:
            # Android: 8-14 scale to 0-100, iOS: 12-17 scale to 0-100
            if 'android' in str(os_version).lower() or version_num < 20:
                os_score = clamp(((version_num - 8) / 6.0) * 100, 0, 100)
            else:  # iOS
                os_score = clamp(((version_num - 12) / 5.0) * 100, 0, 100)
    os_score = clamp(os_score, 0, 100)
    
    # Weighted average: 30% RAM, 30% Storage, 20% Battery, 20% OS
    performance_score = int(round(
        0.30 * ram_score +
        0.30 * storage_score +
        0.20 * battery_score +
        0.20 * os_score
    ))
    
    return clamp(performance_score, 0, 100)

def get_performance_label_and_recommendations(score, data):
    """Get performance label and recommendations based on score"""
    if score >= 85:
        label = "Excellent"
        recommendations = [
            "Your device is performing excellently. Keep software updated.",
            "Maintain at least 20% free storage for optimal performance.",
            "Continue regular maintenance (clear cache periodically)."
        ]
    elif score >= 70:
        label = "Good"
        recommendations = [
            "Device performance is good. Consider clearing cache regularly.",
            "Keep at least 20% free storage space.",
            "Update OS when available for best performance."
        ]
    elif score >= 50:
        label = "Fair"
        recommendations = [
            "Clear cache to free up memory.",
            "Uninstall rarely used apps to free storage.",
            "Keep storage at least 20% free.",
            "Update OS if an update is available.",
            "Enable battery saver mode if battery is below 40%."
        ]
    else:
        label = "Poor"
        recommendations = [
            "Clear cache immediately to free up memory.",
            "Uninstall unused apps to free storage space.",
            "Free up storage - keep at least 20% free.",
            "Update your OS to the latest version.",
            "Enable battery saver mode if battery is below 40%.",
            "Consider factory reset if problems persist (backup data first)."
        ]
    
    return label, recommendations

# Networking helpers to make QR codes work on mobile over LAN
def get_local_ip() -> str:
    """Return the LAN IP of this machine for use by mobile devices on the same network."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(('8.8.8.8', 80))
        ip = sock.getsockname()[0]
        sock.close()
        return ip
    except Exception:
        host_only = request.host.split(':')[0]
        return host_only

def get_base_url() -> str:
    """Build a base URL reachable by mobile devices. Uses request URL for HTTPS tunnels."""
    # For HTTPS (Cloudflare Tunnel, ngrok, etc.), use the request URL directly
    if request.is_secure or request.headers.get('X-Forwarded-Proto') == 'https':
        return request.url_root.rstrip('/')
    
    # For HTTP, try to use LAN IP if localhost
    base_url = request.url_root.rstrip('/')
    host_only = request.host.split(':')[0]
    if host_only in ('127.0.0.1', 'localhost'):
        lan_ip = get_local_ip()
        port = request.host.split(':')[1] if ':' in request.host else '80'
        return f"http://{lan_ip}:{port}"
    return base_url

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Support both form-encoded and JSON payloads
        if request.is_json:
            data = request.get_json(silent=True) or {}
            email = data.get('email')
            password = data.get('password')
        else:
            email = request.form.get('email')
            password = request.form.get('password')

        if not email or not password:
            return jsonify({"success": False, "message": "Email and password are required"})

        conn = sqlite3.connect('users.db')
        c = conn.cursor()

        try:
            c.execute("SELECT * FROM users WHERE email = ?", (email,))
            user = c.fetchone()

            if user and check_password_hash(user[3], password):
                session.clear()
                session['user'] = {'id': user[0], 'name': user[1], 'email': user[2]}
                # Require login each new server run and avoid long-lived cookies
                session.permanent = False
                return jsonify({"success": True, "redirect": url_for('index')})
            else:
                return jsonify({"success": False, "message": "Invalid email or password"})
        except Exception as e:
            return jsonify({"success": False, "message": str(e)})
        finally:
            conn.close()

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not all([name, email, password]):
            return jsonify({"success": False, "message": "All fields are required"})
        
        hashed_password = generate_password_hash(password)
        
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        
        try:
            c.execute("INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
                     (name, email, hashed_password))
            conn.commit()
            return jsonify({"success": True})
        except sqlite3.IntegrityError:
            return jsonify({"success": False, "message": "Email already exists"})
        except Exception as e:
            return jsonify({"success": False, "message": str(e)})
        finally:
            conn.close()
    
    return render_template('register.html')

@app.route('/auth/<provider>')
def auth_provider(provider):
    # TODO: Implement social authentication
    return jsonify({"success": False, "message": "Social authentication not implemented yet"})

@app.route('/')
@login_required
def index():
    try:
        user = session.get('user', {})
        return render_template('index.html', user=user)
    except Exception as e:
        app.logger.error(f"Error rendering index: {str(e)}")
        return redirect(url_for('login'))

@app.route('/test')
def test():
    return "Server is working!"

@app.route('/test_mobile')
def test_mobile():
    return jsonify({
        'status': 'success',
        'message': 'Mobile test endpoint working',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/health')
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'server': 'Smart Mobile Doctor'
    })

@app.route('/collect_device_info', methods=['POST'])
def collect_device_info():
    try:
        device_info = request.json
        session_id = request.args.get('session_id', 'unknown')
        
        # Add session ID and timestamp to device info
        device_info['sessionId'] = session_id
        device_info['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Generate log file with device info
        log_filename = generate_device_log(device_info, {
            'collection_status': 'Successful',
            'collected_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        
        # Store the log filename in session
        session['log_file'] = log_filename
        
        return jsonify({
            'success': True,
            'log_file': log_filename,
            'message': 'Device information collected successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/download_log/<filename>')
def download_log(filename):
    try:
        # Ensure the filename is secure
        secure_filename = os.path.basename(filename)
        log_path = os.path.join('static', 'logs', secure_filename)
        
        if not os.path.exists(log_path):
            return jsonify({
                'error': 'Log file not found',
                'message': 'The requested log file could not be found'
            }), 404

        return send_file(
            log_path,
            mimetype='text/plain',
            as_attachment=True,
            download_name=f'device_analysis_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log',
            max_age=0
        )
    except Exception as e:
        app.logger.error(f"Error downloading log file {filename}: {str(e)}")
        return jsonify({
            'error': 'Download failed',
            'message': 'Failed to download the log file'
        }), 500

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'phone_image' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['phone_image']
    
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file and allowed_file(file.filename):
        filename = str(uuid.uuid4()) + secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        try:
            # Extract phone information
            phone_info = extract_phone_info(filepath)
            session_id = str(uuid.uuid4())
            
            # Get issue, solution and performance score
            issue, solution, performance_score = predict_issue_and_solution(phone_info)
            
            # Add issue and solution to phone_info
            phone_info['issue'] = issue
            phone_info['solution'] = solution
            
            # Generate log file
            log_filename = generate_device_log(phone_info, {'OCR_Results': 'Successful'})
            
            # Store session data
            session['phone_info'] = phone_info
            session['issue'] = issue
            session['solution'] = solution
            session['performance_score'] = performance_score
            session['image_path'] = os.path.join('uploads', filename)
            session['qr_session_id'] = session_id
            session['log_file'] = log_filename
            
            print(f"Session data stored: {session['qr_session_id']}")
            
            return redirect(url_for('result'))
        except Exception as e:
            flash(f'Error processing image: {str(e)}')
            return redirect(request.url)
    
    flash('Invalid file type. Please upload a PNG or JPG image.')
    return redirect(request.url)

@app.route('/result')
@app.route('/result/<session_id>')
def result(session_id=None):
    if session_id is None:
        session_id = request.args.get('session_id') or request.args.get('sid')

    phone_info = {}
    issue = ''
    solution = ''
    performance_score = 85
    image_path = ''
    ocr_data = {}
    web_data = {}
    merged_data = {}

    # Get OCR data from session (if uploaded screenshot)
    if not session_id:
        ocr_data = session.get('phone_info', {})
        image_path = session.get('image_path', '')
        if ocr_data:
            # Mark OCR data with source
            ocr_data = {k: {'value': v, 'source': 'screenshot'} for k, v in ocr_data.items()}

    # Get web data from session store or file
    if session_id:
        sess = session_store.get_session(session_id)
        if sess and sess.get('snapshot'):
            web_data = sess['snapshot']
        else:
            # Try file for backward compatibility
            data_file = os.path.join('static', 'phone_data', f"{session_id}.json")
            if os.path.exists(data_file):
                with open(data_file, 'r') as f:
                    web_data = json.load(f)
        
        # Mark web data with source
        if web_data:
            web_data = {k: {'value': v, 'source': 'web'} for k, v in web_data.items() if k != 'source'}

    # Merge data: prefer web data, fallback to OCR
    all_keys = set(ocr_data.keys()) | set(web_data.keys())
    for key in all_keys:
        if key in web_data:
            merged_data[key] = web_data[key]
        elif key in ocr_data:
            merged_data[key] = ocr_data[key]
    
    # Convert merged data to simple format for display
    phone_info = {}
    for key, val in merged_data.items():
        if isinstance(val, dict) and 'value' in val:
            phone_info[key] = val['value']
        else:
            phone_info[key] = val

    # Compute performance score with new weighting
    if merged_data:
        performance_score = compute_performance_score(phone_info)
        perf_label, recommendations = get_performance_label_and_recommendations(performance_score, phone_info)
    else:
        perf_label = "Unknown"
        recommendations = []

    # Get diagnosis if we have enough data
    def map_to_predictor_schema(data: dict) -> dict:
        mapped = {}
        if 'ram' in data and data['ram']:
            mapped['ram'] = str(data['ram'])
        elif 'ramSizeGB' in data and data['ramSizeGB']:
            mapped['ram'] = f"{data['ramSizeGB']}GB"
        elif 'deviceMemory' in data and data['deviceMemory']:
            mapped['ram'] = f"{data['deviceMemory']}GB"
        if 'os_version' in data and data['os_version']:
            mapped['os_version'] = str(data['os_version'])
        elif 'androidVersion' in data and data['androidVersion']:
            mapped['os_version'] = str(data['androidVersion'])
        elif 'platform' in data and data['platform']:
            mapped['os_version'] = str(data['platform'])
        if 'storage' in data and data['storage']:
            mapped['storage'] = str(data['storage'])
        elif 'storageSizeGB' in data and data['storageSizeGB']:
            mapped['storage'] = (
                f"{data['storageSizeGB']}GB" if isinstance(data['storageSizeGB'], (int, float))
                else str(data['storageSizeGB'])
            )
        if 'battery' in data and data['battery']:
            mapped['battery'] = str(data['battery'])
        elif 'batteryLevel' in data and data['batteryLevel'] is not None:
            mapped['battery'] = f"{data['batteryLevel']}%"
        return mapped

    mapped = map_to_predictor_schema(phone_info)
    if all(k in mapped for k in ['ram', 'os_version', 'storage', 'battery']):
        try:
            issue, solution, _ = predict_issue_and_solution(mapped)
        except Exception as e:
            app.logger.warning(f"Prediction failed for session {session_id}: {e}")
            issue, solution = 'Diagnosis unavailable', 'Insufficient device parameters to run model.'
    else:
        issue, solution = 'Diagnosis unavailable', 'Insufficient device parameters to run model.'

    # Get session ID for QR generation
    qr_session_id = session_id or session.get('qr_session_id')
    if qr_session_id and not session_store.get_session(qr_session_id):
        session_store.create_session(qr_session_id)

    is_https = request.is_secure or request.headers.get('X-Forwarded-Proto') == 'https'
    
    return render_template(
        'result.html',
        phone_info=phone_info,
        merged_data=merged_data,  # Pass merged data with source tags
        issue=issue,
        solution=solution,
        performance_score=performance_score,
        performance_label=perf_label,
        recommendations=recommendations,
        image_path=image_path,
        session_id=qr_session_id,
        is_https=is_https
    )

@app.route('/generate_qr')
def generate_qr():
    try:
        session_id = session.get('qr_session_id')
        app.logger.info(f"[QR] Creating QR code with sessionId: {session_id}")
        print(f"[QR] Creating QR code with sessionId: {session_id}")
        
        if not session_id:
            app.logger.error("No session ID found in session")
            return jsonify({"error": "No active session found"}), 400
            
        base_url = get_base_url()
        # Use /collector?sid=... format
        qr_url = f"{base_url}/collector?sid={session_id}"
        app.logger.info(f"[QR] QR URL: {qr_url}")
        
        # Create session in store if not exists
        session_store.create_session(session_id)
        
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_url)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        img_io = io.BytesIO()
        img.save(img_io, 'PNG')
        img_io.seek(0)
        
        return send_file(img_io, mimetype='image/png', max_age=0)
    except Exception as e:
        app.logger.error(f"Error generating QR code: {str(e)}")
        return jsonify({"error": f"Failed to generate QR code: {str(e)}"}), 500

@app.route('/qr_debug')
def qr_debug():
    session_id = session.get('qr_session_id')
    if not session_id:
        return jsonify({'error': 'No active session found'}), 400
    base_url = get_base_url()
    qr_url = f"{base_url}/mobile/{session_id}"
    return jsonify({'qr_url': qr_url, 'session_id': session_id, 'base_url': base_url})

@app.route('/mobile/<session_id>')
def mobile_page_old(session_id):
    # Legacy route - redirect to new collector format
    return redirect(url_for('collector_page', sid=session_id))

@app.route('/collector')
def collector_page():
    session_id = request.args.get('sid')
    if not session_id:
        return jsonify({"error": "Missing session ID"}), 400
    # Create session if not exists
    if not session_store.get_session(session_id):
        session_store.create_session(session_id)
    server_ip = get_local_ip()
    base_url = get_base_url()
    is_https = request.is_secure or request.headers.get('X-Forwarded-Proto') == 'https'
    
    # Add User-Agent Client Hints headers (HTTPS only)
    response = make_response(render_template('collector.html', session_id=session_id, base_url=base_url, server_ip=server_ip, is_https=is_https))
    if is_https:
        response.headers['Accept-CH'] = 'Sec-CH-UA, Sec-CH-UA-Platform, Sec-CH-UA-Platform-Version, Sec-CH-UA-Model'
        response.headers['Permissions-Policy'] = 'ch-ua=(self), ch-ua-platform=(self), ch-ua-platform-version=(self), ch-ua-model=(self)'
    return response

@app.route('/simple_test/<session_id>')
def simple_test_page(session_id):
    return render_template('simple_test.html', session_id=session_id, base_url=get_base_url())

# New API endpoints for real-time collection
@app.route('/api/collect', methods=['POST'])
def api_collect():
    """Receive initial snapshot from mobile collector"""
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No JSON data received'}), 400
        
        session_id = data.get('sessionId') or data.get('session_id')
        if not session_id:
            return jsonify({'error': 'Missing sessionId'}), 400
        
        app.logger.info(f"[COLLECTOR] POST received for sessionId: {session_id}")
        print(f"[COLLECTOR] POST received for sessionId: {session_id}")
        
        # Validate required fields
        if 'snapshot' not in data:
            return jsonify({'error': 'Missing snapshot data'}), 400
        
        snapshot = data['snapshot']
        timestamp = datetime.now().isoformat()
        
        # Add metadata
        snapshot_with_meta = {
            **snapshot,
            'timestamp': timestamp,
            'source': 'web'
        }
        
        # Store snapshot in session store (this will broadcast to SSE)
        session_store.set_snapshot(session_id, snapshot_with_meta)
        
        # Also save to file for backward compatibility
        phone_data_dir = os.path.join('static', 'phone_data')
        os.makedirs(phone_data_dir, exist_ok=True)
        data_file = os.path.join(phone_data_dir, f"{session_id}.json")
        with open(data_file, 'w') as f:
            json.dump(snapshot_with_meta, f, default=str)
        
        # Add User-Agent Client Hints headers (HTTPS only)
        is_https = request.is_secure or request.headers.get('X-Forwarded-Proto') == 'https'
        response = jsonify({
            'success': True,
            'message': 'Snapshot received',
            'sessionId': session_id,
            'timestamp': timestamp
        })
        if is_https:
            response.headers['Accept-CH'] = 'Sec-CH-UA, Sec-CH-UA-Platform, Sec-CH-UA-Platform-Version, Sec-CH-UA-Model'
            response.headers['Permissions-Policy'] = 'ch-ua=(self), ch-ua-platform=(self), ch-ua-platform-version=(self), ch-ua-model=(self)'
        return response
    except Exception as e:
        app.logger.error(f"Error in /api/collect: {str(e)}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/api/live-battery', methods=['POST'])
def api_live_battery():
    """Receive live battery updates from mobile collector"""
    try:
        # Support both JSON and sendBeacon (Blob with application/json)
        if request.content_type and 'application/json' in request.content_type:
            if request.is_json:
                data = request.json
            else:
                # Handle Blob from sendBeacon
                try:
                    data = json.loads(request.data.decode('utf-8'))
                except:
                    return jsonify({'error': 'Invalid JSON data'}), 400
        else:
            # Try to parse as JSON anyway (fallback)
            try:
                if request.data:
                    data = json.loads(request.data.decode('utf-8'))
                else:
                    return jsonify({'error': 'No data received'}), 400
            except:
                return jsonify({'error': 'Invalid data format'}), 400
        
        if not data:
            return jsonify({'error': 'No data received'}), 400
        
        # Accept both 'sid' and 'sessionId' for compatibility
        session_id = data.get('sid') or data.get('sessionId') or data.get('session_id')
        if not session_id:
            return jsonify({'error': 'Missing sid/sessionId'}), 400
        
        # Use timestamp from client if provided, otherwise use server time
        client_ts = data.get('ts')
        battery_data = {
            'level': data.get('level'),
            'charging': data.get('charging'),
            'timestamp': datetime.now().isoformat(),
            'ts': client_ts or int(time.time() * 1000)  # Keep client timestamp
        }
        
        app.logger.info(f"[BATTERY] Update received for session {session_id}: {battery_data['level']}% ({'charging' if battery_data['charging'] else 'not charging'})")
        
        # Store live battery update (this will broadcast to SSE)
        session_store.set_live(session_id, battery_data)
        
        # Add User-Agent Client Hints headers (HTTPS only)
        is_https = request.is_secure or request.headers.get('X-Forwarded-Proto') == 'https'
        response = jsonify({
            'success': True,
            'message': 'Battery update received',
            'timestamp': battery_data['timestamp']
        })
        if is_https:
            response.headers['Accept-CH'] = 'Sec-CH-UA, Sec-CH-UA-Platform, Sec-CH-UA-Platform-Version, Sec-CH-UA-Model'
            response.headers['Permissions-Policy'] = 'ch-ua=(self), ch-ua-platform=(self), ch-ua-platform-version=(self), ch-ua-model=(self)'
        return response
    except Exception as e:
        app.logger.error(f"Error in /api/live-battery: {str(e)}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/api/session/<session_id>')
def api_session(session_id):
    """Get full session object"""
    try:
        sess = session_store.get_session(session_id)
        if not sess:
            # Try to load from file for backward compatibility
            data_file = os.path.join('static', 'phone_data', f"{session_id}.json")
            if os.path.exists(data_file):
                with open(data_file, 'r') as f:
                    snapshot = json.load(f)
                return jsonify({
                    'success': True,
                    'snapshot': snapshot,
                    'live': None,
                    'createdAt': int(time.time() * 1000)
                })
            return jsonify({
                'success': False,
                'error': 'Session not found'
            }), 404
        
        # Return full session object
        return jsonify({
            'success': True,
            'snapshot': sess.get('snapshot'),
            'live': sess.get('live'),
            'createdAt': sess.get('createdAt')
        })
    except Exception as e:
        app.logger.error(f"Error in /api/session/{session_id}: {str(e)}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/api/stream/<session_id>')
def api_stream(session_id):
    """SSE endpoint for live updates"""
    def generate():
        queue = []
        closed = threading.Event()
        
        def callback(message):
            queue.append(message)
        
        app.logger.info(f"[SSE] Opening stream for sessionId: {session_id}")
        print(f"[SSE] Opening stream for sessionId: {session_id}")
        session_store.subscribe(session_id, callback)
        
        try:
            # Send initial connection message
            yield f"data: {json.dumps({'type': 'connected', 'sessionId': session_id})}\n\n"
            
            # Send current snapshot if available
            sess = session_store.get_session(session_id)
            if sess and sess.get('snapshot'):
                snapshot_msg = {'type': 'snapshot', 'data': sess['snapshot']}
                yield f"data: {json.dumps(snapshot_msg)}\n\n"
                app.logger.info(f"[SSE] Sent initial snapshot for session {session_id}")
            
            # Keep connection alive and send updates
            last_heartbeat = time.time()
            while not closed.is_set():
                # Send heartbeat every 30 seconds
                if time.time() - last_heartbeat > 30:
                    yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': datetime.now().isoformat()})}\n\n"
                    last_heartbeat = time.time()
                
                # Send queued updates
                while queue:
                    update = queue.pop(0)
                    message_str = json.dumps(update)
                    yield f"data: {message_str}\n\n"
                    app.logger.info(f"[SSE] Broadcast sent for session {session_id}: {update.get('type', 'unknown')}")
                    print(f"[SSE] Broadcast sent for session {session_id}: {update.get('type', 'unknown')}")
                
                time.sleep(0.1)  # Check for updates every 100ms for faster updates
        finally:
            session_store.unsubscribe(session_id, callback)
            closed.set()
            app.logger.info(f"[SSE] Stream closed for sessionId: {session_id}")
    
    return Response(stream_with_context(generate()), mimetype='text/event-stream', headers={
        'Cache-Control': 'no-cache',
        'X-Accel-Buffering': 'no',
        'Connection': 'keep-alive'
    })

@app.route('/api/submit_phone_data', methods=['POST'])
def submit_phone_data():
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No JSON data received'}), 400
            
        session_id = data.get('session_id')
        phone_data = data.get('phone_data')
        
        if not session_id:
            return jsonify({'error': 'No session_id provided'}), 400
            
        if not phone_data:
            return jsonify({'error': 'No phone_data provided'}), 400
        
        phone_data_dir = os.path.join('static', 'phone_data')
        os.makedirs(phone_data_dir, exist_ok=True)
        
        data_file = os.path.join(phone_data_dir, f"{session_id}.json")
        
        try:
            with open(data_file, 'w') as f:
                json.dump(phone_data, f, default=str)
        except Exception as e:
            return jsonify({'error': f'Failed to save data: {str(e)}'}), 500
        
        return jsonify({'success': True, 'message': 'Data saved successfully'})
        
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/debug/phone_data/<session_id>')
def debug_phone_data(session_id):
    data_file = os.path.join('static', 'phone_data', f"{session_id}.json")
    if os.path.exists(data_file):
        with open(data_file, 'r') as f:
            data = json.load(f)
        return jsonify({
            'exists': True,
            'file_path': data_file,
            'data_keys': list(data.keys()),
            'sample_data': dict(list(data.items())[:10])
        })
    else:
        return jsonify({
            'exists': False,
            'file_path': data_file,
            'available_files': os.listdir(os.path.join('static', 'phone_data')) if os.path.exists(os.path.join('static', 'phone_data')) else []
        })

@app.route('/api/check_phone_data/<session_id>')
def check_phone_data(session_id):
    data_file = os.path.join('static', 'phone_data', f"{session_id}.json")
    if os.path.exists(data_file):
        with open(data_file, 'r') as f:
            return jsonify({'available': True, 'data': json.load(f)})
    return jsonify({'available': False})

@app.route('/api/download-health-report/<session_id>')
def download_health_report(session_id):
    """Generate and download comprehensive health report PDF"""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
        from reportlab.lib.units import inch
        from reportlab.graphics.shapes import Drawing
        from reportlab.graphics.charts.piecharts import Pie
    except ImportError:
        # Fallback to JSON if reportlab not available
        sess = session_store.get_session(session_id)
        if not sess:
            data_file = os.path.join('static', 'phone_data', f"{session_id}.json")
            if os.path.exists(data_file):
                with open(data_file, 'r') as f:
                    data = json.load(f)
            else:
                return jsonify({'error': 'Session not found'}), 404
        else:
            data = sess.get('snapshot', {})
        
        # Return JSON as fallback
        response = make_response(json.dumps({
            'sessionId': session_id,
            'timestamp': datetime.now().isoformat(),
            'data': data
        }, indent=2))
        response.headers['Content-Type'] = 'application/json'
        response.headers['Content-Disposition'] = f'attachment; filename=health-report-{session_id}.json'
        return response
    
    # Get session data
    sess = session_store.get_session(session_id)
    snapshot = None
    live_data = None
    
    if sess:
        snapshot = sess.get('snapshot', {})
        live_data = sess.get('live', {})
        created_at = sess.get('createdAt', datetime.now())
    else:
        # Try file for backward compatibility
        data_file = os.path.join('static', 'phone_data', f"{session_id}.json")
        if os.path.exists(data_file):
            with open(data_file, 'r') as f:
                snapshot = json.load(f)
        else:
            return jsonify({'error': 'Session not found'}), 404
        created_at = datetime.now()
    
    # Use live battery if available, otherwise snapshot
    battery_level = None
    battery_charging = False
    battery_last_update = None
    
    if live_data and live_data.get('level') is not None:
        battery_level = live_data.get('level')
        battery_charging = live_data.get('charging', False)
        ts = live_data.get('ts')
        if ts:
            if isinstance(ts, (int, float)):
                battery_last_update = datetime.fromtimestamp(ts / 1000) if ts > 1e10 else datetime.fromtimestamp(ts)
            else:
                battery_last_update = ts
        else:
            battery_last_update = created_at
    elif snapshot and snapshot.get('battery'):
        battery_data = snapshot.get('battery', {})
        battery_level = battery_data.get('level')
        battery_charging = battery_data.get('charging', False)
        battery_last_update = created_at
    
    # Compute AI Health Score
    health_score = 50
    health_status = "Unknown"
    health_recommendation = "Analyzing device metrics..."
    
    # Calculate health score (simplified version of smart_diagnosis.js logic)
    if snapshot:
        score = 0
        # Battery: 40%
        if battery_level is not None:
            score += (battery_level / 100) * 40
        else:
            score += 20
        
        # RAM: 30% (simplified)
        if snapshot.get('deviceMemory'):
            ram_gb = parse_numeric(snapshot.get('deviceMemory'))
            if ram_gb >= 8:
                score += 30
            elif ram_gb >= 6:
                score += 25
            elif ram_gb >= 4:
                score += 20
            else:
                score += 15
        else:
            score += 15
        
        # Storage: 20%
        if snapshot.get('storage'):
            storage = snapshot.get('storage', {})
            usage_percent = 0
            if storage.get('storageSandboxUsagePercent') is not None:
                usage_percent = storage.get('storageSandboxUsagePercent')
            elif storage.get('quota') and storage.get('usage'):
                quota = float(storage.get('quota', 0))
                usage = float(storage.get('usage', 0))
                if quota > 0:
                    usage_percent = (usage / quota) * 100
            
            if usage_percent > 0:
                free_pct = 100 - usage_percent
                score += 20 * (free_pct / 100)
            else:
                score += 10
        else:
            score += 10
        
        # Charging bonus: 10%
        if battery_charging:
            score += 10
        
        health_score = max(0, min(100, round(score)))
        
        # Determine status
        if health_score >= 80:
            health_status = "Excellent"
        elif health_score >= 60:
            health_status = "Good"
        elif health_score >= 40:
            health_status = "Moderate"
        else:
            health_status = "Critical"
        
        # Generate recommendation
        recommendations = []
        if battery_level is not None and battery_level < 20:
            recommendations.append("Plug in your charger immediately.")
        elif battery_level is not None and battery_level < 40:
            recommendations.append("Consider plugging in your charger soon.")
        
        if snapshot.get('storage'):
            storage = snapshot.get('storage', {})
            usage_percent = 0
            if storage.get('storageSandboxUsagePercent') is not None:
                usage_percent = storage.get('storageSandboxUsagePercent')
            elif storage.get('quota') and storage.get('usage'):
                quota = float(storage.get('quota', 0))
                usage = float(storage.get('usage', 0))
                if quota > 0:
                    usage_percent = (usage / quota) * 100
            
            if usage_percent > 80:
                recommendations.append("Delete unused files to free up space.")
            elif usage_percent > 60:
                recommendations.append("Consider cleaning up storage space.")
        
        if snapshot.get('deviceMemory'):
            ram_gb = parse_numeric(snapshot.get('deviceMemory'))
            if ram_gb < 4:
                recommendations.append("Close background apps to free up RAM.")
        
        if recommendations:
            health_recommendation = " ".join(recommendations)
        else:
            health_recommendation = "Your device is performing well."
    
    # Get storage info
    storage_usage = None
    storage_quota = None
    storage_usage_percent = None
    if snapshot and snapshot.get('storage'):
        storage = snapshot.get('storage', {})
        if storage.get('storageSandboxUsedMB') is not None:
            storage_usage = storage.get('storageSandboxUsedMB')
            storage_quota = storage.get('storageSandboxQuotaMB')
            storage_usage_percent = storage.get('storageSandboxUsagePercent')
        elif storage.get('usage') and storage.get('quota'):
            storage_usage = round(storage.get('usage', 0) / (1024 * 1024))
            storage_quota = round(storage.get('quota', 0) / (1024 * 1024))
            if storage_quota > 0:
                storage_usage_percent = round((storage_usage / storage_quota) * 100)
    
    # Generate QR code for session
    base_url = get_base_url()
    qr_url = f"{base_url}/result?session_id={session_id}"
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=4, border=2)
    qr.add_data(qr_url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    qr_buffer = io.BytesIO()
    qr_img.save(qr_buffer, format='PNG')
    qr_buffer.seek(0)
    
    # Generate PDF
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    story = []
    styles = getSampleStyleSheet()
    
    # Cover Page
    cover_title_style = ParagraphStyle(
        'CoverTitle',
        parent=styles['Heading1'],
        fontSize=32,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=20,
        alignment=1,  # Center
    )
    story.append(Spacer(1, 1.5*inch))
    story.append(Paragraph("Smart Mobile Doctor", cover_title_style))
    story.append(Paragraph("Health Report", ParagraphStyle('CoverSubtitle', parent=styles['Heading2'], fontSize=24, textColor=colors.HexColor('#666666'), alignment=1)))
    story.append(Spacer(1, 0.5*inch))
    
    # Session info on cover
    cover_info_style = ParagraphStyle('CoverInfo', parent=styles['Normal'], fontSize=11, textColor=colors.HexColor('#666666'), alignment=1)
    story.append(Paragraph(f"Session ID: {session_id}", cover_info_style))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", cover_info_style))
    story.append(Spacer(1, 0.3*inch))
    
    # QR Code on cover
    qr_img_pl = Image(qr_buffer, width=1.5*inch, height=1.5*inch)
    story.append(qr_img_pl)
    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph("Scan to view live session", cover_info_style))
    
    story.append(PageBreak())
    
    # Summary Section
    summary_style = ParagraphStyle('SummaryTitle', parent=styles['Heading1'], fontSize=20, textColor=colors.HexColor('#1a1a1a'), spaceAfter=15)
    story.append(Paragraph("Executive Summary", summary_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Summary cards
    summary_data = [
        ['Metric', 'Value', 'Status'],
        ['AI Health Score', f'{health_score}%', health_status],
        ['Battery Level', f'{battery_level}%' if battery_level is not None else 'N/A', 'Charging' if battery_charging else 'Not Charging' if battery_level is not None else 'N/A'],
        ['Storage Usage', f'{storage_usage_percent}%' if storage_usage_percent is not None else 'N/A', f'{storage_usage} MB / {storage_quota} MB' if storage_usage and storage_quota else 'N/A'],
    ]
    
    summary_table = Table(summary_data, colWidths=[2*inch, 2*inch, 2.5*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4a5568')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f7fafc')),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f7fafc')])
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 0.3*inch))
    
    # Smart Recommendation
    story.append(Paragraph("<b>Smart Recommendation</b>", styles['Heading2']))
    story.append(Spacer(1, 0.1*inch))
    rec_style = ParagraphStyle('Recommendation', parent=styles['Normal'], fontSize=11, leftIndent=0.2*inch, textColor=colors.HexColor('#2d3748'))
    story.append(Paragraph(health_recommendation, rec_style))
    story.append(Spacer(1, 0.3*inch))
    
    # Device Information
    story.append(Paragraph("<b>Device Information</b>", styles['Heading2']))
    story.append(Spacer(1, 0.1*inch))
    
    device_data = [['Field', 'Value']]
    for key, value in snapshot.items():
        if key not in ['timestamp', 'source', 'battery', 'storage']:
            display_key = key.replace('_', ' ').title()
            if isinstance(value, dict):
                value_str = json.dumps(value, indent=2)[:100] + '...' if len(json.dumps(value)) > 100 else json.dumps(value, indent=2)
            else:
                value_str = str(value) if value is not None else "Not exposed by browser"
            device_data.append([display_key, value_str])
    
    # Add battery info
    if battery_level is not None:
        device_data.append(['Battery Level', f'{battery_level}% ({"Charging" if battery_charging else "Not Charging"})'])
        if battery_last_update:
            if isinstance(battery_last_update, datetime):
                device_data.append(['Battery Last Updated', battery_last_update.strftime('%Y-%m-%d %H:%M:%S')])
            else:
                device_data.append(['Battery Last Updated', str(battery_last_update)])
    
    # Add storage info
    if storage_usage_percent is not None:
        device_data.append(['Storage Usage', f'{storage_usage_percent}% ({storage_usage} MB used of {storage_quota} MB)'])
        device_data.append(['Storage Type', 'Browser Sandbox'])
    
    if len(device_data) > 1:
        table = Table(device_data, colWidths=[2*inch, 4.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4a5568')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f7fafc')),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f7fafc')])
        ]))
        story.append(table)
    
    story.append(Spacer(1, 0.3*inch))
    
    # Notes & Limitations
    story.append(Paragraph("<b>Notes & Limitations</b>", styles['Heading2']))
    story.append(Spacer(1, 0.1*inch))
    notes_style = ParagraphStyle('Notes', parent=styles['Normal'], fontSize=10, textColor=colors.HexColor('#718096'), leftIndent=0.2*inch)
    story.append(Paragraph("• Battery health (mAh/wear) is not available on web browsers. We show live battery level and charging status only.", notes_style))
    story.append(Spacer(1, 0.05*inch))
    story.append(Paragraph("• Storage information shows browser sandbox quota, not full device memory.", notes_style))
    story.append(Spacer(1, 0.05*inch))
    story.append(Paragraph("• Some metrics may not be available on all browsers or require HTTPS.", notes_style))
    
    doc.build(story)
    buffer.seek(0)
    
    return send_file(
        buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'health-report-{session_id}-{datetime.now().strftime("%Y%m%d")}.pdf'
    )

@app.route('/api/share-report/<session_id>', methods=['POST'])
def create_share_link(session_id):
    """Create a shareable link for a session report"""
    try:
        # Verify session exists
        sess = session_store.get_session(session_id)
        if not sess:
            # Try file for backward compatibility
            data_file = os.path.join('static', 'phone_data', f"{session_id}.json")
            if not os.path.exists(data_file):
                return jsonify({'error': 'Session not found'}), 404
        
        # Create share token
        token = create_share_token(session_id)
        base_url = get_base_url()
        share_url = f"{base_url}/share/{token}"
        
        # Get expiry time
        with share_tokens_lock:
            token_data = share_tokens.get(token)
            expires_at = token_data['expires_at'] if token_data else datetime.now() + timedelta(hours=24)
        
        return jsonify({
            'success': True,
            'share_url': share_url,
            'expires_at': expires_at.isoformat()
        })
    except Exception as e:
        app.logger.error(f"Error creating share link: {str(e)}")
        return jsonify({'error': f'Failed to create share link: {str(e)}'}), 500

@app.route('/share/<token>')
def share_view(token):
    """Read-only view of a shared report"""
    try:
        # Get session_id from token
        session_id = get_share_token(token)
        if not session_id:
            return render_template('share_expired.html'), 404
        
        # Get session data
        sess = session_store.get_session(session_id)
        snapshot = None
        live_data = None
        
        if sess:
            snapshot = sess.get('snapshot', {})
            live_data = sess.get('live', {})
            created_at = sess.get('createdAt', datetime.now())
        else:
            # Try file for backward compatibility
            data_file = os.path.join('static', 'phone_data', f"{session_id}.json")
            if os.path.exists(data_file):
                with open(data_file, 'r') as f:
                    snapshot = json.load(f)
            else:
                return render_template('share_expired.html'), 404
            created_at = datetime.now()
        
        # Get expiry time
        with share_tokens_lock:
            token_data = share_tokens.get(token)
            expires_at = token_data['expires_at'] if token_data else datetime.now() + timedelta(hours=24)
        
        # Use live battery if available
        battery_level = None
        battery_charging = False
        if live_data and live_data.get('level') is not None:
            battery_level = live_data.get('level')
            battery_charging = live_data.get('charging', False)
        elif snapshot and snapshot.get('battery'):
            battery_data = snapshot.get('battery', {})
            battery_level = battery_data.get('level')
            battery_charging = battery_data.get('charging', False)
        
        # Compute health score (same logic as PDF)
        health_score = 50
        health_status = "Unknown"
        health_recommendation = "Analyzing device metrics..."
        
        if snapshot:
            score = 0
            if battery_level is not None:
                score += (battery_level / 100) * 40
            else:
                score += 20
            
            if snapshot.get('deviceMemory'):
                ram_gb = parse_numeric(snapshot.get('deviceMemory'))
                if ram_gb >= 8:
                    score += 30
                elif ram_gb >= 6:
                    score += 25
                elif ram_gb >= 4:
                    score += 20
                else:
                    score += 15
            else:
                score += 15
            
            if snapshot.get('storage'):
                storage = snapshot.get('storage', {})
                usage_percent = 0
                if storage.get('storageSandboxUsagePercent') is not None:
                    usage_percent = storage.get('storageSandboxUsagePercent')
                elif storage.get('quota') and storage.get('usage'):
                    quota = float(storage.get('quota', 0))
                    usage = float(storage.get('usage', 0))
                    if quota > 0:
                        usage_percent = (usage / quota) * 100
                
                if usage_percent > 0:
                    free_pct = 100 - usage_percent
                    score += 20 * (free_pct / 100)
                else:
                    score += 10
            else:
                score += 10
            
            if battery_charging:
                score += 10
            
            health_score = max(0, min(100, round(score)))
            
            if health_score >= 80:
                health_status = "Excellent"
            elif health_score >= 60:
                health_status = "Good"
            elif health_score >= 40:
                health_status = "Moderate"
            else:
                health_status = "Critical"
            
            recommendations = []
            if battery_level is not None and battery_level < 20:
                recommendations.append("Plug in your charger immediately.")
            elif battery_level is not None and battery_level < 40:
                recommendations.append("Consider plugging in your charger soon.")
            
            if snapshot.get('storage'):
                storage = snapshot.get('storage', {})
                usage_percent = 0
                if storage.get('storageSandboxUsagePercent') is not None:
                    usage_percent = storage.get('storageSandboxUsagePercent')
                elif storage.get('quota') and storage.get('usage'):
                    quota = float(storage.get('quota', 0))
                    usage = float(storage.get('usage', 0))
                    if quota > 0:
                        usage_percent = (usage / quota) * 100
                
                if usage_percent > 80:
                    recommendations.append("Delete unused files to free up space.")
                elif usage_percent > 60:
                    recommendations.append("Consider cleaning up storage space.")
            
            if snapshot.get('deviceMemory'):
                ram_gb = parse_numeric(snapshot.get('deviceMemory'))
                if ram_gb < 4:
                    recommendations.append("Close background apps to free up RAM.")
            
            if recommendations:
                health_recommendation = " ".join(recommendations)
            else:
                health_recommendation = "Your device is performing well."
        
        # Get storage info
        storage_usage = None
        storage_quota = None
        storage_usage_percent = None
        if snapshot and snapshot.get('storage'):
            storage = snapshot.get('storage', {})
            if storage.get('storageSandboxUsedMB') is not None:
                storage_usage = storage.get('storageSandboxUsedMB')
                storage_quota = storage.get('storageSandboxQuotaMB')
                storage_usage_percent = storage.get('storageSandboxUsagePercent')
            elif storage.get('usage') and storage.get('quota'):
                storage_usage = round(storage.get('usage', 0) / (1024 * 1024))
                storage_quota = round(storage.get('quota', 0) / (1024 * 1024))
                if storage_quota > 0:
                    storage_usage_percent = round((storage_usage / storage_quota) * 100)
        
        return render_template('share_view.html',
                             session_id=session_id,
                             snapshot=snapshot,
                             battery_level=battery_level,
                             battery_charging=battery_charging,
                             health_score=health_score,
                             health_status=health_status,
                             health_recommendation=health_recommendation,
                             storage_usage=storage_usage,
                             storage_quota=storage_quota,
                             storage_usage_percent=storage_usage_percent,
                             expires_at=expires_at)
    except Exception as e:
        app.logger.error(f"Error rendering share view: {str(e)}")
        return render_template('share_expired.html'), 500

@app.route('/debug')
def debug_page():
    return render_template('debug.html')

@app.route('/logout')
def logout():
    try:
        session.clear()
    finally:
        return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
