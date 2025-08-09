# suspicious_activity_detector.py

import cv2
import mediapipe as mp
import dlib
from scipy.spatial import distance as dist
import numpy as np

# Initialize MediaPipe solutions for hands and face mesh
mp_hands = mp.solutions.hands
mp_face_mesh = mp.solutions.face_mesh
mp_drawing = mp.solutions.drawing_utils


# from http://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2
try:
    predictor = dlib.shape_predictor("shape_predictor_68_face_landmarks.dat")
    detector = dlib.get_frontal_face_detector()
except Exception as e:
    print(f"Error loading dlib model: {e}. Please ensure 'shape_predictor_68_face_landmarks.dat' is in the project directory.")
    predictor = None
    detector = None

# A global state to track suspicious activity
suspicious_state = {
    'phone_detected': False,
    'eye_contact_lost': False,
    'excessive_blinking': False
}

def detect_suspicious_activity(frame):
    """
    Analyzes a single video frame for various suspicious activities.
    
    Args:
        frame (np.array): The current frame from the video stream.

    Returns:
        tuple: A tuple containing the processed frame with annotations
               and a dictionary of detected activities.
    """
    # Initialize activity flags for the current frame
    activity_flags = {
        'phone_detected': False,
        'eye_contact_lost': False
    }

    h, w, _ = frame.shape
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    

    
    # 2. Hand-to-Face Gesture Detection (using MediaPipe)
    with mp_hands.Hands(min_detection_confidence=0.5, min_tracking_confidence=0.5) as hands:
        results = hands.process(rgb_frame)
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                # Get the position of the index finger and other landmarks
                index_finger_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
                
                # Check for proximity to the mouth/face
                # This is a simple heuristic; a real system would be more complex
                if index_finger_tip.x > 0.4 and index_finger_tip.x < 0.6 and index_finger_tip.y > 0.4 and index_finger_tip.y < 0.6:
                    activity_flags['hand_to_face'] = True
                    cv2.putText(frame, "Hand-to-face detected!", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
    
    # 3. Gaze and Blink Detection (using Dlib)
    if detector and predictor:
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = detector(gray_frame)
        
        if len(faces) == 0:
            activity_flags['eye_contact_lost'] = True
            cv2.putText(frame, "Candidate not found!", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        
        for face in faces:
            landmarks = predictor(gray_frame, face)
            
            # Gaze Detection (Simplified)
            left_eye_pts = np.array([(landmarks.part(i).x, landmarks.part(i).y) for i in range(36, 42)])
            right_eye_pts = np.array([(landmarks.part(i).x, landmarks.part(i).y) for i in range(42, 48)])
            
            # Calculate the center of the eyes
            left_eye_center = left_eye_pts.mean(axis=0).astype("int")
            right_eye_center = right_eye_pts.mean(axis=0).astype("int")
            
            # Check if gaze is off-center (very simplified logic)
            if abs(left_eye_center[0] - w // 2) > 100 or abs(right_eye_center[0] - w // 2) > 100:
                activity_flags['gaze_off_center'] = True
                cv2.putText(frame, "Gaze off-center!", (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                
            # Blink Detection
            # You would implement the Eye Aspect Ratio (EAR) logic here.
            # For brevity, let's assume we have an `ear` value.
            # if ear < EYE_AR_THRESH:
            #     activity_flags['blinking'] = True
    
    # Display the status of all detected activities
    for key, value in activity_flags.items():
        if value:
            cv2.putText(frame, f"Suspicious: {key}", (10, 30 + list(activity_flags.keys()).index(key) * 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
    return frame, activity_flags