from flask import Flask, render_template, request, jsonify
import cv2
import pytesseract
import numpy as np
import base64
import logging
import time
import os
import re
from flask_cors import CORS
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore

# Initialize Firebase
cred = credentials.Certificate('vehicle-auth-6b075-firebase-adminsdk-fbsvc-30870c584d.json')  # Update with your path
firebase_admin.initialize_app(cred)

# Initialize Firestore
db = firestore.client()

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Path to tesseract executable
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Path to the Haar Cascade for detecting plates
HAAR_CASCADE_PATH = "model/haarcascade_russian_plate_number.xml"

def validate_plate(plate_text):
    plate_text = plate_text.replace('O', '0').replace('I', '1').replace('Z', '2')
    match = re.match(r'^[A-Z0-9]{6,12}$', plate_text)
    return plate_text if match else None

def process_image(image):
    img_gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    plate_cascade = cv2.CascadeClassifier(HAAR_CASCADE_PATH)
    plates = plate_cascade.detectMultiScale(img_gray, scaleFactor=1.1, minNeighbors=5, minSize=(50, 50))
    plate_numbers = []
    min_area = 500
    
    for (x, y, w, h) in plates:
        if w * h > min_area:
            img_roi = image[y:y + h, x:x + w]
            img_roi_gray = cv2.cvtColor(img_roi, cv2.COLOR_BGR2GRAY)
            img_roi_blur = cv2.GaussianBlur(img_roi_gray, (5, 5), 0)
            img_roi_thresh = cv2.adaptiveThreshold(img_roi_blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
            kernel = np.ones((3, 3), np.uint8)
            img_roi_clean = cv2.morphologyEx(img_roi_thresh, cv2.MORPH_CLOSE, kernel)
            custom_config = r'--oem 3 --psm 8 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
            plate_text = pytesseract.image_to_string(img_roi_clean, config=custom_config)
            alphanumeric_texts = re.findall(r'\b[A-Z0-9]+\b', plate_text)
            if alphanumeric_texts:
                valid_plate = validate_plate(max(alphanumeric_texts, key=len))
                if valid_plate:
                    plate_numbers.append(valid_plate)
    return plate_numbers

def authenticate_plate(plate_number):
    """Checks if the plate is authorized in Firebase Firestore."""
    try:
        doc_ref = db.collection('authorized_plates').document(plate_number)
        doc = doc_ref.get()
        if doc.exists:
            return True
        else:
            return False
    except Exception as e:
        logger.error(f"Firebase authentication error: {e}")
        return False

def store_plate(plate_number):
    """Stores the plate in Firestore under 'license_plates' for tracking unauthorized vehicles."""
    try:
        db.collection('license_plates').document(plate_number).set({
            'plate_number': plate_number,
            'timestamp': datetime.now().isoformat()
        })
        logger.info(f"Stored unauthorized plate: {plate_number}")
    except Exception as e:
        logger.error(f"Error storing plate in Firestore: {e}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/help')
def help():
    return render_template('help.html')

@app.route('/signup')
def signup():
    return render_template('signup.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/process_image', methods=['POST'])
def process_image_route():
    try:
        if not request.is_json:
            return jsonify({'error': 'Request must be JSON'}), 400
        
        data = request.get_json()
        if not data or 'image' not in data:
            return jsonify({'error': 'No image data provided'}), 400
        
        header, encoded = data['image'].split(",", 1)
        binary_image_data = base64.b64decode(encoded)
        nparr = np.frombuffer(binary_image_data, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        os.makedirs('received_images', exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S%f")
        received_image_filename = os.path.join('received_images', f'image_{timestamp}.jpg')
        cv2.imwrite(received_image_filename, image)
        
        start_time = time.time()
        detected_text = process_image(image)
        detection_time = time.time() - start_time
        
        if not detected_text:
            return jsonify({'error': 'No license plate detected'}), 404
        
        auth_status = "Unauthorized"
        for plate in detected_text:
            if authenticate_plate(plate):
                auth_status = "Authorized Vehicle"
                break
            else:
                store_plate(plate)
        
        gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        _, buffer = cv2.imencode('.jpg', gray_image)
        grayscale_image_base64 = base64.b64encode(buffer).decode('utf-8')
        
        return jsonify({
            'result': detected_text,
            'authorization': auth_status,
            'detection_time': f"{detection_time:.2f} seconds",
            'grayscale_image': f"data:image/jpeg;base64,{grayscale_image_base64}"
        })
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    if not os.path.exists('templates'):
        os.makedirs('templates')
        logger.warning("Created missing templates directory")
    
    required_templates = ['index.html', 'contact.html', 'help.html', 'signup.html', 'login.html']
    missing_templates = [t for t in required_templates if not os.path.exists(os.path.join('templates', t))]
    
    if missing_templates:
        logger.warning(f"Missing templates: {', '.join(missing_templates)}")
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)