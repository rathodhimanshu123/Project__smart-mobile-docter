from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file
import os
import uuid
import qrcode
import io
import json
from werkzeug.utils import secure_filename
from utils.ocr_processor import extract_phone_info
from utils.predictor import predict_issue_and_solution

app = Flask(__name__)
app.secret_key = 'smartmobiledoctor'

# Configure upload folder
UPLOAD_FOLDER = os.path.join('static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure required directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(os.path.join('static', 'phone_data'), exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

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
            
            # Get prediction and solution
            issue, solution = predict_issue_and_solution(phone_info)
            
            # Store results in session
            session['phone_info'] = phone_info
            session['issue'] = issue
            session['solution'] = solution
            session['image_path'] = os.path.join('uploads', filename)
            # Generate a unique session ID for QR code
            session['qr_session_id'] = str(uuid.uuid4())
            
            return redirect(url_for('result'))
        except Exception as e:
            flash(f'Error processing image: {str(e)}')
            return redirect(request.url)
    
    flash('Invalid file type. Please upload a PNG or JPG image.')
    return redirect(request.url)

@app.route('/result')
def result():
    # Get results from session
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
        if not session_id:
            app.logger.error("No session ID found in session")
            return jsonify({"error": "No active session found"}), 400
            
        # Create the URL that the QR code will point to
        base_url = request.url_root.rstrip('/')
        qr_url = f"{base_url}/mobile/{session_id}"
        
        app.logger.info(f"Generating QR code for URL: {qr_url}")
        
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
        
        # Return the image
        return send_file(img_io, mimetype='image/png', cache_timeout=0)
    except Exception as e:
        app.logger.error(f"Error generating QR code: {str(e)}")
        return jsonify({"error": "Failed to generate QR code"}), 500

@app.route('/mobile/<session_id>')
def mobile_page(session_id):
    return render_template('mobile.html', session_id=session_id)

@app.route('/api/submit_phone_data', methods=['POST'])
def submit_phone_data():
    data = request.json
    session_id = data.get('session_id')
    phone_data = data.get('phone_data')
    
    # Store the data (in a real app, you'd use a database)
    phone_data_dir = os.path.join('static', 'phone_data')
    os.makedirs(phone_data_dir, exist_ok=True)
    
    with open(os.path.join(phone_data_dir, f"{session_id}.json"), 'w') as f:
        json.dump(phone_data, f)
    
    return jsonify({'success': True})

@app.route('/api/check_phone_data/<session_id>')
def check_phone_data(session_id):
    data_file = os.path.join('static', 'phone_data', f"{session_id}.json")
    if os.path.exists(data_file):
        with open(data_file, 'r') as f:
            return jsonify({'available': True, 'data': json.load(f)})
    return jsonify({'available': False})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)