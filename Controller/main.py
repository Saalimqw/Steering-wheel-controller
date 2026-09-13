# /// script
# requires-python = ">=3.11,<3.12"
# dependencies = [
#     "mediapipe==0.10.14",
#     "numpy",
#     "opencv-python",
#     "pydirectinput",
# ]
# ///
# pyrefly: ignore [missing-import]
import cv2
import mediapipe as mp
import math
import pydirectinput
pydirectinput.FAILSAFE = False
import numpy as np
import time

# Initialize MediaPipe Hands
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=2,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7
)
mp_drawing = mp.solutions.drawing_utils

# Open Webcam
cap = cv2.VideoCapture(0)
cv2.namedWindow('Virtual Steering Wheel', cv2.WINDOW_NORMAL)
cv2.resizeWindow('Virtual Steering Wheel', 320, 240)
cv2.setWindowProperty('Virtual Steering Wheel', cv2.WND_PROP_TOPMOST, 1)

def calculate_angle(p1, p2):
    # p1 and p2 are tuples (x, y)
    # Returns angle in degrees
    x1, y1 = p1
    x2, y2 = p2
    angle = math.degrees(math.atan2(y2 - y1, x2 - x1))
    return angle
    
def detect_gesture(hand_landmarks):
    fingers_folded = []
    # Check index, middle, ring, pinky
    for tip_idx, pip_idx in [(8, 6), (12, 10), (16, 14), (20, 18)]:
        tip = hand_landmarks.landmark[tip_idx]
        pip = hand_landmarks.landmark[pip_idx]
        wrist = hand_landmarks.landmark[0]
        
        # Use 3D distance for rotation invariance
        tip_dist = math.sqrt((tip.x - wrist.x)**2 + (tip.y - wrist.y)**2 + (tip.z - wrist.z)**2)
        pip_dist = math.sqrt((pip.x - wrist.x)**2 + (pip.y - wrist.y)**2 + (pip.z - wrist.z)**2)
        
        fingers_folded.append(tip_dist < pip_dist)
            
    if all(fingers_folded):
        return "FIST"
    elif not any(fingers_folded):
        return "PALM"
    elif not fingers_folded[0] and all(fingers_folded[1:]):
        return "INDEX_UP"
    else:
        return "UNKNOWN"

# Global states
current_steering_key = None
steering_key_down = False
steering_pwm_cycle = 0.1 # 100ms cycle for tapping keys

current_pedal_key = None
current_horn_down = False
current_dipper_down = False
smoothed_angle = 0.0

def press_steering_key(key):
    global current_steering_key
    if current_steering_key != key:
        if current_steering_key is not None:
            pydirectinput.keyUp(current_steering_key)
        if key is not None:
            pydirectinput.keyDown(key)
        current_steering_key = key

def press_pedal_key(key):
    global current_pedal_key
    if current_pedal_key != key:
        if current_pedal_key is not None:
            pydirectinput.keyUp(current_pedal_key)
def update_steering(angle):
    global steering_key_down, current_steering_key
    
    deadzone = 10.0
    max_angle = 45.0
    abs_angle = abs(angle)
    
    # Calculate how much we should press the key (0.0 to 1.0)
    if abs_angle <= deadzone:
        duty_cycle = 0.0
        target_key = None
    else:
        duty_cycle = min((abs_angle - deadzone) / (max_angle - deadzone), 1.0)
        target_key = 'd' if angle > 0 else 'a'
        
    # If direction changed, release the old key
    if current_steering_key != target_key and current_steering_key is not None:
        if steering_key_down:
            pydirectinput.keyUp(current_steering_key)
            steering_key_down = False
            
    current_steering_key = target_key
    
    if duty_cycle == 0.0:
        if steering_key_down and current_steering_key is not None:
            pydirectinput.keyUp(current_steering_key)
            steering_key_down = False
        return "STRAIGHT", (0, 255, 0)
        
    if duty_cycle == 1.0:
        if not steering_key_down and current_steering_key is not None:
            pydirectinput.keyDown(current_steering_key)
            steering_key_down = True
        return "HARD " + ("RIGHT" if angle > 0 else "LEFT"), (0, 0, 255)
        
    # PWM logic: tap the key rapidly to simulate analog steering
    time_in_cycle = time.time() % steering_pwm_cycle
    should_be_down = (time_in_cycle / steering_pwm_cycle) < duty_cycle
    
    if should_be_down and not steering_key_down:
        pydirectinput.keyDown(current_steering_key)
        steering_key_down = True
    elif not should_be_down and steering_key_down:
        pydirectinput.keyUp(current_steering_key)
        steering_key_down = False
        
    dir_text = "RIGHT" if angle > 0 else "LEFT"
    return f"{dir_text} ({int(duty_cycle*100)}%)", (0, 255, 255)

def update_pedals(left_gesture, right_gesture, is_honking):
    global current_pedal_key
    
    left_braking = (left_gesture == "PALM")
    right_braking = (right_gesture == "PALM" and not is_honking)
    
    if left_braking or right_braking:
        target_key = 's'
        pedal_text = "BRAKE"
        pedal_color = (0, 0, 255)
    elif left_gesture == "FIST" or right_gesture == "FIST":
        target_key = 'w'
        pedal_text = "GAS"
        pedal_color = (0, 255, 0)
    else:
        target_key = None
        pedal_text = "COAST"
        pedal_color = (255, 255, 0)
        
    if current_pedal_key != target_key:
        if current_pedal_key is not None:
            pydirectinput.keyUp(current_pedal_key)
        if target_key is not None:
            pydirectinput.keyDown(target_key)
        current_pedal_key = target_key
        
    return pedal_text, pedal_color

def update_actions(left_gesture, right_gesture, right_hand_center, frame_width):
    global current_horn_down, current_dipper_down
    
    # Horn: Right Hand OPEN in the middle of the screen
    should_horn = False
    if right_hand_center and right_gesture == "PALM":
        rx = right_hand_center[0]
        if frame_width * 0.3 < rx < frame_width * 0.7:
            should_horn = True
            
    if should_horn and not current_horn_down:
        pydirectinput.keyDown('h')
        current_horn_down = True
    elif not should_horn and current_horn_down:
        pydirectinput.keyUp('h')
        current_horn_down = False
        
    # Dipper mapped to Right INDEX_UP (key 'e')
    should_dipper = (right_gesture == "INDEX_UP")
    if should_dipper and not current_dipper_down:
        pydirectinput.keyDown('e')
        current_dipper_down = True
    elif not should_dipper and current_dipper_down:
        pydirectinput.keyUp('e')
        current_dipper_down = False
        
    return should_horn, should_dipper

def reset_controls():
    global steering_key_down, current_steering_key, current_pedal_key
    global current_horn_down, current_dipper_down
    
    if steering_key_down and current_steering_key:
        pydirectinput.keyUp(current_steering_key)
        steering_key_down = False
        
    if current_pedal_key:
        pydirectinput.keyUp(current_pedal_key)
        current_pedal_key = None
        
    if current_horn_down:
        pydirectinput.keyUp('h')
        current_horn_down = False
        
    if current_dipper_down:
        pydirectinput.keyUp('j')
        current_dipper_down = False

try:
    while cap.isOpened():
        success, image = cap.read()
        if not success:
            break

        # Flip the image horizontally for a selfie-view display
        image = cv2.flip(image, 1)
        
        # Convert the BGR image to RGB
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Process the image and find hands
        results = hands.process(image_rgb)
        
        h, w, _ = image.shape
        
        left_hand_center = None
        right_hand_center = None
        left_gesture = "UNKNOWN"
        right_gesture = "UNKNOWN"

        if results.multi_hand_landmarks:
            hands_data = []
            for hand_landmarks in results.multi_hand_landmarks:
                # Draw the hand landmarks
                mp_drawing.draw_landmarks(image, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                
                # Get coordinates for the index finger MCP (Landmark 5)
                # This acts as our "grip" point on the virtual steering wheel
                x = int(hand_landmarks.landmark[5].x * w)
                y = int(hand_landmarks.landmark[5].y * h)
                
                gesture = detect_gesture(hand_landmarks)
                hands_data.append({
                    'center': (x, y),
                    'gesture': gesture
                })
                
            # If two hands are detected, sort them by X coordinate to robustly assign Left and Right
            # (Since the image is horizontally flipped, smaller X is the left side of the screen)
            if len(hands_data) == 2:
                hands_data.sort(key=lambda d: d['center'][0])
                left_hand_center = hands_data[0]['center']
                left_gesture = hands_data[0]['gesture']
                right_hand_center = hands_data[1]['center']
                right_gesture = hands_data[1]['gesture']
            elif len(hands_data) == 1:
                # Fallback if only one hand is visible
                if hands_data[0]['center'][0] < w / 2:
                    left_hand_center = hands_data[0]['center']
                    left_gesture = hands_data[0]['gesture']
                else:
                    right_hand_center = hands_data[0]['center']
                    right_gesture = hands_data[0]['gesture']

        # If both hands are detected, calculate angle and draw steering wheel UI
        if left_hand_center and right_hand_center:
            # Draw line between hands
            cv2.line(image, left_hand_center, right_hand_center, (0, 165, 255), 3)
            
            # Draw circles on hands
            cv2.circle(image, left_hand_center, 15, (255, 0, 0), cv2.FILLED)  # Blue for left
            cv2.circle(image, right_hand_center, 15, (0, 255, 0), cv2.FILLED) # Green for right
            
            # Center point of the line
            cx = (left_hand_center[0] + right_hand_center[0]) // 2
            cy = (left_hand_center[1] + right_hand_center[1]) // 2
            cv2.circle(image, (cx, cy), 10, (0, 0, 255), cv2.FILLED)
            
            # Calculate angle (relative to horizontal)
            raw_angle = calculate_angle(left_hand_center, right_hand_center)
            
            # Smooth the angle to remove jitter and make it more precise
            smoothed_angle = 0.7 * smoothed_angle + 0.3 * raw_angle
            angle = smoothed_angle
            
            # Execute logic
            steer_text, steer_color = update_steering(angle)
            is_horn, is_dipper = update_actions(left_gesture, right_gesture, right_hand_center, w)
            pedal_text, pedal_color = update_pedals(left_gesture, right_gesture, is_horn)
            
            # Display text and angle
            cv2.putText(image, f"Steer: {steer_text}", (cx - 60, cy - 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, steer_color, 2)
            cv2.putText(image, f"Pedal: {pedal_text}", (cx - 60, cy - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, pedal_color, 2)
            cv2.putText(image, f"Angle: {int(angle)} deg", (cx - 60, cy + 40), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            if is_horn:
                cv2.putText(image, "HORN!", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 165, 255), 3)
            if is_dipper:
                cv2.putText(image, "DIPPER!", (w - 150, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 3)
            
            # --- Draw a User-Friendly Steering Gauge ---
            gauge_w = 200
            gx = w // 2 - gauge_w // 2
            gy = h - 40
            
            # Background line
            cv2.line(image, (gx, gy), (gx + gauge_w, gy), (200, 200, 200), 5)
            # Center tick
            cv2.line(image, (gx + gauge_w // 2, gy - 10), (gx + gauge_w // 2, gy + 10), (255, 255, 255), 3)
            
            # Map angle (-90 to 90) to X position on gauge
            display_angle = max(min(angle, 90), -90)
            marker_x = int(gx + (display_angle + 90) / 180.0 * gauge_w)
            
            # Draw moving steering marker
            cv2.circle(image, (marker_x, gy), 12, steer_color, cv2.FILLED)
        else:
            # Reset steering if hands are not detected
            reset_controls()
            cv2.putText(image, "Put both hands in frame", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        # Show the image
        cv2.imshow('Virtual Steering Wheel', image)
        
        # Press 'q' to quit
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

finally:
    # Ensure gamepad is reset when exiting
    reset_controls()
    cap.release()
    cv2.destroyAllWindows()
