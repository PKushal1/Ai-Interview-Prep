import os
import json
import threading
import time
from flask import Flask, request, jsonify, render_template, session, Response, redirect, url_for
from dotenv import load_dotenv
import google.generativeai as genai
import cv2

from suspicious_activity_detector import detect_suspicious_activity

# Load environment variables from .env file
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables.")

# Configure the Gemini API with your key
genai.configure(api_key=GEMINI_API_KEY)

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Admin user credentials
ADMIN_USER = {
    'username': 'kushal',
    'password': 'k123'
}

# Video stream setup
camera_lock = threading.Lock()
camera = cv2.VideoCapture(0)
if not camera.isOpened():
    print("Error: Could not open video stream.")
    camera = None

latest_activity_flags = {}

# Define the Gemini Model once for consistent use
gemini_model = genai.GenerativeModel('gemini-2.5-pro')

def parse_gemini_response(response_text):
    """Attempts to find and parse a JSON object from a string."""
    try:
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        if json_start != -1 and json_end != -1:
            json_str = response_text[json_start:json_end]
            return json.loads(json_str)
        else:
            raise ValueError("No JSON object found in the response.")
    except (json.JSONDecodeError, ValueError) as e:
        print(f"Failed to parse JSON from Gemini response. Error: {e}")
        return None
    
def generate_interview_question(topic):
    """Generates a technical interview question on a given topic."""
    prompt = f"""
    You are an interviewer. Ask a clear, beginner to intermediate level technical interview question 
    related to {topic}. The question should sound like a spoken question, not a coding task. 
    Avoid words like 'write', 'implement', or 'code', and exclude phrases like 'Q:' or 'Here's the question'. 
    Keep it short and in one sentence.
    """
    try:
        response = gemini_model.generate_content(prompt)
        text = response.text.strip()
        if not text:
            return None
        return text
    except Exception as e:
        print(f"Error generating question: {e}")
        return None

def create_plotly_data(score):
    """Creates a Plotly data structure for a bar chart."""
    return {
        "data": [{
            "type": "bar",
            "x": ["Correctness Score"],
            "y": [score],
            "marker": {"color": "blue"}
        }],
        "layout": {
            "title": "Answer Evaluation Score",
            "yaxis": {"range": [0, 100], "title": "Score (%)"},
            "xaxis": {"title": "Evaluation Metric"}
        }
    }


def generate_frames():
    """Generates frames from the camera for the video feed."""
    global camera, latest_activity_flags
    if not camera:
        yield (b'--frame\r\n'
               b'Content-Type: text/plain\r\n\r\n'
               b'Error: Could not access camera.\r\n')
        return

    while True:
        with camera_lock:
            success, frame = camera.read()

        if not success:
            print("Warning: Failed to read frame from camera.")
            time.sleep(1)
            continue
        
        processed_frame, activities = detect_suspicious_activity(frame)
        latest_activity_flags.update(activities)
        
        ret, buffer = cv2.imencode('.jpg', processed_frame)
        frame_bytes = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')


@app.route('/')
@app.route('/index.html')
def home():
    """Renders the homepage, passing login status."""
    return render_template('index.html', logged_in='logged_in' in session)

# @app.route('/login.html')
# def login():
#     """Renders the About Us page."""
#     return render_template('login.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Handles user login.
    If the request method is POST, it checks the credentials.
    If it's GET, it shows the login form.
    """
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if username == ADMIN_USER['username'] and password == ADMIN_USER['password']:
            # Set the 'logged_in' key in the session to True
            session['logged_in'] = True
            # Redirect to the dashboard after a successful login
            return redirect(url_for('dashboard'))
        else:
            error_message = "Invalid username or password. Please try again."
            return render_template('login.html', error=error_message)

    return render_template('login.html')

# @app.route('/dashboard')
# def dashboard():
#     """Renders the About Us page."""
#     return render_template('dashboard.html')


# @app.route('/dashboard')
# def dashboard():
#     """
#     Renders the dashboard page.
#     This route is protected and can only be accessed if the user is logged in.
#     """
#     # Check if the 'logged_in' key exists and is True in the session
#     if 'logged_in' in session and session['logged_in']:
#         return render_template('dashboard.html')
#     else:
#         # If the user is not logged in, redirect them to the login page
#         return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    """
    Renders the dashboard page.
    This route is protected and can only be accessed if the user is logged in.
    """
    # Check if the 'logged_in' key exists and is True in the session
    if 'logged_in' in session and session['logged_in']:
        # Pass the login status to the template
        return render_template('dashboard.html', logged_in='logged_in' in session)
    else:
        # If the user is not logged in, redirect them to the login page
        return redirect(url_for('login'))


# --- CORRECTED LOGOUT ROUTE ---
@app.route('/logout')
def logout():
    """Logs the user out by clearing the session and redirects to the home page."""
    session.pop('logged_in', None)
    return redirect(url_for('home'))


@app.route('/about.html')
def about():
    """Renders the About Us page, passing login status."""
    return render_template('about.html', logged_in='logged_in' in session)

@app.route('/features.html')
def features():
    """Renders the Features page, passing login status."""
    return render_template('features.html', logged_in='logged_in' in session)

@app.route('/contact.html')
def contact():
    """Renders the Contact page, passing login status."""
    return render_template('contact.html', logged_in='logged_in' in session)

# -----------------------
# GEMINI API ROUTES
# -----------------------

@app.route('/generate', methods=['POST'])
def generate():
    topic = request.form.get("topic")
    if not topic:
        return jsonify({"error": "Topic is required"}), 400

    question = generate_interview_question(topic)
    if not question:
        return jsonify({"error": "Failed to generate question"}), 500
    
    session['question'] = question

    return jsonify({"question": question})

@app.route('/evaluate', methods=['POST'])
def evaluate_answer():
    """Evaluates a user's answer and provides feedback and a performance graph."""
    data = request.get_json()
    user_answer = data.get('user_answer')

    if not user_answer:
        return jsonify({"error": "Answer is required for evaluation."}), 400
        
    generated_question = session.get('question')
    if not generated_question:
        return jsonify({"error": "No question has been generated yet. Please generate one first."}), 400

    prompt = f"""
    You are an AI interview coach. Evaluate the following interview answer based on the provided question. 
    Provide feedback in a structured JSON format.

    Question: "{generated_question}"
    Answer: "{user_answer}"

    Analyze the answer for:
    - Technical Accuracy (score 1-10)
    - Clarity and Structure (score 1-10)
    - Confidence and Delivery (score 1-10) - Assume a confident delivery for this text-based evaluation.

    Return a JSON object with the following keys:
    - `feedback_summary`: A brief paragraph summarizing the performance.
    - `areas_for_improvement`: A list of 2-3 specific points for the candidate to work on.
    - `graph`: A JSON object structured for Plotly.js to create a radar chart of the scores.
    
    Example JSON for the graph key:
    {{
      "data": [{{
        "r": [8, 9, 7],
        "theta": ["Technical Accuracy", "Clarity and Structure", "Confidence and Delivery"],
        "fill": "toself",
        "type": "scatterpolar",
        "name": "Your Score"
      }}],
      "layout": {{
        "polar": {{ "radialaxis": {{ "visible": true, "range": [0, 10] }} }},
        "showlegend": false
      }}
    }}
    
    Your response should be ONLY the JSON object. Do not include any extra text or conversation.
    """
    try:
        response = gemini_model.generate_content(prompt)
        parsed_data = parse_gemini_response(response.text)

        if parsed_data:
            return jsonify(parsed_data)
        else:
            return jsonify({"error": "Failed to parse AI response as JSON. Received non-JSON text from Gemini."}), 500

    except Exception as e:
        print(f"Error evaluating answer: {e}")
        return jsonify({"error": f"Failed to evaluate answer: {e}"}), 500


# -----------------------
# VIDEO STREAM ROUTES
# -----------------------

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/activity_flags')
def get_activity_flags():
    global latest_activity_flags
    return jsonify(latest_activity_flags)


if __name__ == '__main__':
    app.run(debug=True)