from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import os
import time
import pandas as pd
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
from codes  import update_google_sheet_from_amazon
from FBA_inventory import main
from dotenv import load_dotenv


load_dotenv()

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB limit (adjust as needed)
application = app



app.secret_key = os.getenv('APP_SECRET_KEY')
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def process_main_inventory(file1_path):
    try:
        result = update_google_sheet_from_amazon(file1_path)  # Call your function
        os.remove(file1_path)  # Remove file after processing
        return result
    except Exception as e:
        return f"Error: {str(e)}"

def process_fba_inventory(file2_path):
    try:
        result = main(file2_path)  # Call your function
        os.remove(file2_path)  # Remove file after processing
        return result
    except Exception as e:
        return f"Error: {str(e)}"


# # Hardcoded User Credentials (For Testing)
ADMIN_EMAIL = os.getenv('EMAIL')
ADMIN_PASSWORD = os.getenv('PASSWORD')

# 🔐 Login Route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        # Check Credentials
        if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
            session['user'] = email  # Store session
            return render_template('index.html')  # Redirect to dashboard
        else:
            return render_template('login.html', error="Invalid credentials. Please try again.")

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/')
def index():
    if 'user' in session:
        return render_template('index.html')
    return render_template('login.html')

@app.route('/amazon_inventory')
def amazon_inventory_page():
    return render_template('amazon_inventory.html')

@app.route('/fba_inventory')
def fba_inventory_page():
    return render_template('fba_inventory.html')

@app.route('/upload_inventory1', methods=['POST'])
def upload_inventory1():
    error_message = None
    success_message = None
    file1 = request.files['file1']
    if 'file1' not in request.files:
        error_message = "No file part"
        return render_template('index.html', error=error_message)
    elif file1.filename == '':
        error_message = "No selected file"
        return render_template('index.html', error=error_message)
    else:
        filename1 = secure_filename(file1.filename)
        file_path1 = os.path.join(app.config['UPLOAD_FOLDER'], filename1)
        file1.save(file_path1)

        # Process the file
        result1 = process_main_inventory(file_path1)
        success_message = f'File "{filename1}" successfully!'
        return render_template('index.html', success=success_message)

@app.route('/upload_inventory2', methods=['POST'])
def upload_inventory2():
    error_message = None
    success_message = None
    file2 = request.files['file2']
    try:
        request.environ['werkzeug.request'].timeout = 600
        if 'file2' not in request.files:
            error_message = "No file part"
            return render_template('index.html', error=error_message)
            # return jsonify({'status': 'error', 'message': 'No file part'}), 400
        elif file2.filename == '':
            error_message = "No selected file"
            return render_template('index.html', error=error_message)
            # return jsonify({'status': 'error', 'message': 'No file part'}), 400
        else:
            filename2 = secure_filename(file2.filename)
            file_path2 = os.path.join(app.config['UPLOAD_FOLDER'], filename2)
            file2.save(file_path2)
            # Process the file

            # thread = threading.Thread(target=process_fba_inventory, args=(file_path2,))
            # thread.start()
            result2 = process_fba_inventory(file_path2)

            success_message = f'File "{filename2}" successfully!'
            return render_template('index.html', success=success_message)
    except RequestEntityTooLarge:
        return "File too large",413


if __name__ == '__main__':
      app.run(debug=True)

