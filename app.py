# -*- coding: utf-8 -*-

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file, make_response
import os
import uuid
import qrcode
import io
import json
import socket
from werkzeug.utils import secure_filename
from utils.ocr_processor import extract_phone_info
from utils.predictor import predict_issue_and_solution
from utils.log_generator import generate_device_log
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from functools import wraps

app = Flask(__name__)
app.secret_key = 'smartmobiledoctor'
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

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
    """Build a base URL reachable by mobile devices. Replaces localhost with LAN IP."""
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
                session.clear()  # Clear any existing session
                session['user'] = {'id': user[0], 'name': user[1], 'email': user[2]}
                session.permanent = True  # Make the session persistent
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
        
        # Write the log file
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(log_content))
        
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
            
            # Get issue and solution
            issue, solution = predict_issue_and_solution(phone_info)
            
            # Add issue and solution to phone_info
            phone_info['issue'] = issue
            phone_info['solution'] = solution
            
            # Generate log file
            log_filename = generate_device_log(phone_info, {'OCR_Results': 'Successful'})
            
            # Store session data
            session['phone_info'] = phone_info
            session['issue'] = issue
            session['solution'] = solution
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
        session_id = request.args.get('session_id')

    phone_info = {}
    issue = ''
    solution = ''
    image_path = ''

    def map_to_predictor_schema(data: dict) -> dict:
        mapped = {}
        if 'ram' in data and data['ram']:
            mapped['ram'] = str(data['ram'])
        elif 'ramSizeGB' in data and data['ramSizeGB']:
            mapped['ram'] = f"{data['ramSizeGB']}GB"
        if 'os_version' in data and data['os_version']:
            mapped['os_version'] = str(data['os_version'])
        elif 'androidVersion' in data and data['androidVersion']:
            mapped['os_version'] = str(data['androidVersion'])
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

    if session_id:
        data_file = os.path.join('static', 'phone_data', f"{session_id}.json")
        if os.path.exists(data_file):
            with open(data_file, 'r') as f:
                raw_data = json.load(f)

            phone_info = map_to_predictor_schema(raw_data) or {}
            phone_info.update({k: v for k, v in raw_data.items() if k not in phone_info})

            mapped = map_to_predictor_schema(phone_info)
            if all(k in mapped for k in ['ram', 'os_version', 'storage', 'battery']):
                try:
                    issue, solution = predict_issue_and_solution(mapped)
                except Exception as e:
                    app.logger.warning(f"Prediction failed for session {session_id}: {e}")
                    issue, solution = 'Diagnosis unavailable', 'Insufficient device parameters to run model.'
            else:
                issue, solution = 'Diagnosis unavailable', 'Insufficient device parameters to run model.'
        else:
            flash(f'No data found for session ID: {session_id}')
            return redirect(url_for('index'))
    else:
        raw_data = session.get('phone_info', {})
        phone_info = map_to_predictor_schema(raw_data) or {}
        phone_info.update({k: v for k, v in raw_data.items() if k not in phone_info})
        issue = session.get('issue', '')
        solution = session.get('solution', '')
        image_path = session.get('image_path', '')

    return render_template(
        'result.html',
        phone_info=phone_info,
        issue=issue,
        solution=solution,
        image_path=image_path
    )

@app.route('/generate_qr')
def generate_qr():
    try:
        session_id = session.get('qr_session_id')
        print(f"QR generation - Session ID: {session_id}")
        
        if not session_id:
            app.logger.error("No session ID found in session")
            return jsonify({"error": "No active session found"}), 400
            
        base_url = get_base_url()
        qr_url = f"{base_url}/mobile/{session_id}"
        
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
def mobile_page(session_id):
    server_ip = get_local_ip()
    return render_template('mobile.html', session_id=session_id, base_url=get_base_url(), server_ip=server_ip)

@app.route('/simple_test/<session_id>')
def simple_test_page(session_id):
    return render_template('simple_test.html', session_id=session_id, base_url=get_base_url())

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

@app.route('/debug')
def debug_page():
    return render_template('debug.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
