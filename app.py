from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file
import os
import uuid
import qrcode
import io
import json
import socket
from werkzeug.utils import secure_filename
from utils.ocr_processor import extract_phone_info
from utils.predictor import predict_issue_and_solution
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'smartmobiledoctor'
app.config['DEBUG'] = True
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.jinja_env.auto_reload = True

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
        # This does not send packets; it just selects an interface
        sock.connect(('8.8.8.8', 80))
        ip = sock.getsockname()[0]
        sock.close()
        return ip
    except Exception:
        # Fallback to host from the incoming request
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

@app.route('/')
def index():
    try:
        return render_template('index.html')
    except Exception as e:
        return f"Error: {str(e)}"

@app.route('/test')
def test():
    return "Server is working!"

@app.route('/test_mobile')
def test_mobile():
    """Test endpoint to verify mobile data collection"""
    return jsonify({
        'status': 'success',
        'message': 'Mobile test endpoint working',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/health')
def health_check():
    """Simple health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'server': 'Smart Mobile Doctor'
    })

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'phone_image' not in request.files:
        flash('No file part')
        return redirect(request.url)
    
    file = request.files['phone_image']
    
    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)
    
    if file and allowed_file(file.filename):
        # Generate unique filename
        filename = str(uuid.uuid4()) + secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Process the image with OCR
        try:
            phone_info = extract_phone_info(filepath)
            
            # Add debug print
            print(f"Session ID generated: {str(uuid.uuid4())}")
            
            # Get prediction and solution
            issue, solution = predict_issue_and_solution(phone_info)
            
            # Store results in session
            session['phone_info'] = phone_info
            session['issue'] = issue
            session['solution'] = solution
            session['image_path'] = os.path.join('uploads', filename)
            # Generate a unique session ID for QR code
            session['qr_session_id'] = str(uuid.uuid4())
            
            # Add debug print
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
    # Accept session_id from querystring as well
    if session_id is None:
        session_id = request.args.get('session_id')

    phone_info = {}
    issue = ''
    solution = ''
    image_path = ''

    def map_to_predictor_schema(data: dict) -> dict | None:
        try:
            mapped = {}
            # RAM
            if 'ram' in data and data['ram']:
                mapped['ram'] = str(data['ram'])
            elif 'ramSizeGB' in data and data['ramSizeGB']:
                mapped['ram'] = f"{data['ramSizeGB']}GB"
            # OS version
            if 'os_version' in data and data['os_version']:
                mapped['os_version'] = str(data['os_version'])
            elif 'androidVersion' in data and data['androidVersion']:
                mapped['os_version'] = str(data['androidVersion'])
            # Storage
            if 'storage' in data and data['storage']:
                mapped['storage'] = str(data['storage'])
            elif 'storageSizeGB' in data and data['storageSizeGB']:
                # storageSizeGB may include extra text like "123 (quota)"
                mapped['storage'] = f"{data['storageSizeGB']}GB" if isinstance(data['storageSizeGB'], (int, float)) else str(data['storageSizeGB'])
            # Battery
            if 'battery' in data and data['battery']:
                mapped['battery'] = str(data['battery'])
            elif 'batteryLevel' in data and data['batteryLevel'] is not None:
                mapped['battery'] = f"{data['batteryLevel']}%"
            # Minimum fields required for predictor
            return mapped if all(k in mapped for k in ['ram','os_version','storage','battery']) else None
        except Exception:
            return None

    if session_id:
        # If session_id is provided, try to load data from file
        data_file = os.path.join('static', 'phone_data', f"{session_id}.json")
        if os.path.exists(data_file):
            with open(data_file, 'r') as f:
                phone_info = json.load(f)
            # Try to run prediction if we can map inputs
            mapped = map_to_predictor_schema(phone_info)
            if mapped:
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
        # Otherwise, get results from session (for initial OCR upload)
        phone_info = session.get('phone_info', {})
        issue = session.get('issue', '')
        solution = session.get('solution', '')
        image_path = session.get('image_path', '')

    return render_template('result.html',
                           phone_info=phone_info,
                           issue=issue,
                           solution=solution,
                           image_path=image_path)

@app.route('/generate_qr')
def generate_qr():
    try:
        # Check if we have a QR session ID
        session_id = session.get('qr_session_id')
        print(f"QR generation - Session ID: {session_id}")
        
        if not session_id:
            app.logger.error("No session ID found in session")
            return jsonify({"error": "No active session found"}), 400
            
        # Create the URL that the QR code will point to
        base_url = get_base_url()
        qr_url = f"{base_url}/mobile/{session_id}"
        
        # Also create a simple test URL for debugging
        simple_test_url = f"{base_url}/simple_test/{session_id}"
        
        app.logger.info(f"Generating QR code for URL: {qr_url}")
        print(f"Generating QR code for URL: {qr_url}")
        
        # Generate QR code with error correction
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,  # Higher error correction
            box_size=10,
            border=4,
        )
        qr.add_data(qr_url)
        qr.make(fit=True)
        
        # Create the QR code image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Save to BytesIO object
        img_io = io.BytesIO()
        img.save(img_io, 'PNG')
        img_io.seek(0)
        
        # Return the image - using max_age instead of cache_timeout
        return send_file(img_io, mimetype='image/png', max_age=0)
    except Exception as e:
        app.logger.error(f"Error generating QR code: {str(e)}")
        print(f"Error generating QR code: {str(e)}")
        # Return more specific error message
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
    # Get the server's IP address for mobile devices to connect to
    server_ip = get_local_ip()
    # Provide base_url for deep-link to app
    return render_template('mobile.html', session_id=session_id, base_url=get_base_url(), server_ip=server_ip)

@app.route('/simple_test/<session_id>')
def simple_test_page(session_id):
    # Simple test page for debugging
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
        
        print(f"Received phone data for session {session_id}:")
        print(f"Phone data keys: {list(phone_data.keys()) if phone_data else 'None'}")
        print(f"Sample data: {dict(list(phone_data.items())[:5]) if phone_data else 'None'}")
        
        # Store the data (in a real app, you'd use a database)
        phone_data_dir = os.path.join('static', 'phone_data')
        os.makedirs(phone_data_dir, exist_ok=True)
        
        data_file = os.path.join(phone_data_dir, f"{session_id}.json")
        
        # Ensure the data is serializable
        try:
            with open(data_file, 'w') as f:
                json.dump(phone_data, f, default=str)
        except Exception as e:
            print(f"Error saving data: {e}")
            return jsonify({'error': f'Failed to save data: {str(e)}'}), 500
        
        print(f"Data saved to: {data_file}")
        return jsonify({'success': True, 'message': 'Data saved successfully'})
        
    except Exception as e:
        print(f"Error in submit_phone_data: {e}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/debug/phone_data/<session_id>')
def debug_phone_data(session_id):
    """Debug endpoint to check what data is stored for a session"""
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