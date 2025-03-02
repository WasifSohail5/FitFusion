import cv2
import mediapipe as mp
import numpy as np
from mediapipe.python.solutions import pose


def calculate_angle(a, b, c):
    a = np.array(a)
    b = np.array(b)
    c = np.array(c)
    radians = np.arctan2(c[1] - b[1], c[0] - b[0]) - np.arctan2(a[1] - b[1], a[0] - b[0])
    angle = np.abs(radians * 180.0 / np.pi)
    return 360 - angle if angle > 180.0 else angle


class PostureAnalyzer:
    def __init__(self):
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)
        self.cap = None

    def start_camera(self):
        """Initialize the camera for video capture."""
        self.cap = cv2.VideoCapture(0)

    def release_camera(self):
        """Release the camera and close all OpenCV windows."""
        if self.cap is not None:
            self.cap.release()
            cv2.destroyAllWindows()

    def analyze_biceps_curl(self):
        left_counter, right_counter = 0, 0
        left_stage, right_stage = "down", "down"  # Initialize stages

        try:
            while True:
                ret, frame = self.cap.read()
                if not ret:
                    print("Failed to capture video.")
                    break

                # Flip the frame horizontally
                frame = cv2.flip(frame, 1)

                image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                image.flags.writeable = False
                results = self.pose.process(image)
                image.flags.writeable = True
                image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

                try:
                    landmarks = results.pose_landmarks.landmark

                    # Left arm
                    left_shoulder = [landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER.value].x,
                                     landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER.value].y]
                    left_elbow = [landmarks[self.mp_pose.PoseLandmark.LEFT_ELBOW.value].x,
                                  landmarks[self.mp_pose.PoseLandmark.LEFT_ELBOW.value].y]
                    left_wrist = [landmarks[self.mp_pose.PoseLandmark.LEFT_WRIST.value].x,
                                  landmarks[self.mp_pose.PoseLandmark.LEFT_WRIST.value].y]
                    left_angle = calculate_angle(left_shoulder, left_elbow, left_wrist)

                    if left_angle > 160:
                        left_stage = "down"
                    if left_angle < 30 and left_stage == "down":
                        left_stage = "up"
                        left_counter += 1

                    # Right arm
                    right_shoulder = [landmarks[self.mp_pose.PoseLandmark.RIGHT_SHOULDER.value].x,
                                      landmarks[self.mp_pose.PoseLandmark.RIGHT_SHOULDER.value].y]
                    right_elbow = [landmarks[self.mp_pose.PoseLandmark.RIGHT_ELBOW.value].x,
                                   landmarks[self.mp_pose.PoseLandmark.RIGHT_ELBOW.value].y]
                    right_wrist = [landmarks[self.mp_pose.PoseLandmark.RIGHT_WRIST.value].x,
                                   landmarks[self.mp_pose.PoseLandmark.RIGHT_WRIST.value].y]
                    right_angle = calculate_angle(right_shoulder, right_elbow, right_wrist)

                    if right_angle > 160:
                        right_stage = "down"
                    if right_angle < 30 and right_stage == "down":
                        right_stage = "up"
                        right_counter += 1

                    # Visualize angles
                    cv2.putText(image, str(int(left_angle)), tuple(np.multiply(left_elbow, [640, 480]).astype(int)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255),  2, cv2.LINE_AA)
                    cv2.putText(image, str(int(right_angle)), tuple(np.multiply(right_elbow, [640, 480]).astype(int)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2, cv2.LINE_AA)

                except Exception as e:
                    print(f"Keypoints not detected: {e}")
                    continue

                cv2.putText(image, f"Left Reps: {left_counter}", (10, 40),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)
                cv2.putText(image, f"Right Reps: {right_counter}", (10, 80),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)

                self.mp_drawing.draw_landmarks(image, results.pose_landmarks, self.mp_pose.POSE_CONNECTIONS)
                cv2.imshow('Biceps Curl Tracker', image)

                if cv2.waitKey(10) & 0xFF == ord('q'):
                    break

        finally:
            self.release_camera()

    def analyze_squat(self):
        while True:
            ret, frame = self.cap.read()
            if not ret:
                print("Failed to capture video.")
                break

            # Flip the frame horizontally
            frame = cv2.flip(frame, 1)

            image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image.flags.writeable = False
            results = self.pose.process(image)
            image.flags.writeable = True
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

            feedback = "Analyzing..."
            try:
                landmarks = results.pose_landmarks.landmark

                left_hip = [landmarks[self.mp_pose.PoseLandmark.LEFT_HIP.value].x,
                            landmarks[self.mp_pose.PoseLandmark.LEFT_HIP.value].y]
                left_knee = [landmarks[self.mp_pose.PoseLandmark.LEFT_KNEE.value].x,
                             landmarks[self.mp_pose.PoseLandmark.LEFT_KNEE.value].y]
                left_ankle = [landmarks[self.mp_pose.PoseLandmark.LEFT_ANKLE.value].x,
                              landmarks[self.mp_pose.PoseLandmark.LEFT_ANKLE.value].y]
                left_knee_angle = calculate_angle(left_hip, left_knee, left_ankle)

                if left_knee_angle > 170:
                    feedback = "Too Shallow! Go lower."
                elif left_knee_angle < 60:
                    feedback = "Too Deep! Adjust."
                else:
                    feedback = "Perfect Squat!"

                cv2.putText(image, f"Left: {int(left_knee_angle)}",
                            tuple(np.multiply(left_knee, [640, 480]).astype(int)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2, cv2.LINE_AA)

            except Exception as e:
                feedback = "No Person Detected!"
                print(f"Error: {e}")

            cv2.putText(image, feedback, (10, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)
            self.mp_drawing.draw_landmarks(image, results.pose_landmarks, self.mp_pose.POSE_CONNECTIONS)
            cv2.imshow('Squat Tracker', image)

            if cv2.waitKey(10) & 0xFF == ord('q'):
                break

        self.release_camera()

    def analyze_pushups(self):
        pushup_counter = 0
        pushup_stage = "down"
        feedback_pushup = "Start Push-Ups!"

        while True:
            ret, frame = self.cap.read()
            if not ret:
                print("Failed to capture video.")
                break

            # Flip the frame horizontally
            frame = cv2.flip(frame, 1)

            image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image.flags.writeable = False
            results = self.pose.process(image)
            image.flags.writeable = True
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

            try:
                landmarks = results.pose_landmarks.landmark

                left_shoulder = [landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER.value].x,
                                 landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER.value].y]
                right_shoulder = [landmarks[self.mp_pose.PoseLandmark.RIGHT_SHOULDER.value]. x,
                                  landmarks[self.mp_pose.PoseLandmark.RIGHT_SHOULDER.value].y]
                left_hip = [landmarks[self.mp_pose.PoseLandmark.LEFT_HIP.value].x,
                            landmarks[self.mp_pose.PoseLandmark.LEFT_HIP.value].y]
                right_hip = [landmarks[self.mp_pose.PoseLandmark.RIGHT_HIP.value].x,
                             landmarks[self.mp_pose.PoseLandmark.RIGHT_HIP.value].y]

                shoulder_avg_y = (left_shoulder[1] + right_shoulder[1]) / 2
                hip_avg_y = (left_hip[1] + right_hip[1]) / 2

                if shoulder_avg_y - hip_avg_y < 0.15:
                    pushup_stage = "down"
                    feedback_pushup = "Go Lower!"
                if shoulder_avg_y - hip_avg_y > 0.3 and pushup_stage == "down":
                    pushup_stage = "up"
                    pushup_counter += 1
                    feedback_pushup = "Complete Push-Up!"

                cv2.putText(image, f"Push-Ups: {pushup_counter}", (10, 40),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)
                cv2.putText(image, feedback_pushup, (10, 80),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)

                self.mp_drawing.draw_landmarks(image, results.pose_landmarks, self.mp_pose.POSE_CONNECTIONS,
                                               self.mp_drawing.DrawingSpec(color=(245, 117, 66), thickness=2, circle_radius=2),
                                               self.mp_drawing.DrawingSpec(color=(245, 66, 230), thickness=2, circle_radius=2))

            except Exception as e:
                feedback_pushup = "No Person Detected!"
                print(f"Error: {e}")

            cv2.imshow('Exercise Tracker', image)

            if cv2.waitKey(10) & 0xFF == ord('q'):
                break

        self.release_camera()

    def analyze_plank(self):
        plank_status = "Start Plank!"
        plank_time = 0  # Time in seconds for maintaining a good plank

        while True:
            ret, frame = self.cap.read()
            if not ret:
                print("Failed to capture video.")
                break

            # Flip the frame horizontally
            frame = cv2.flip(frame, 1)

            image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image.flags.writeable = False
            results = self.pose.process(image)
            image.flags.writeable = True
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

            try:
                landmarks = results.pose_landmarks.landmark

                left_shoulder = [landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER.value].x,
                                 landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER.value].y]
                left_hip = [landmarks[self.mp_pose.PoseLandmark.LEFT_HIP.value].x,
                            landmarks[self.mp_pose.PoseLandmark.LEFT_HIP.value].y]
                left_ankle = [landmarks[self.mp_pose.PoseLandmark.LEFT_ANKLE.value].x,
                              landmarks[self.mp_pose.PoseLandmark.LEFT_ANKLE.value].y]

                plank_angle = calculate_angle(left_shoulder, left_hip, left_ankle)

                if plank_angle > 160 and plank_angle < 180:
                    plank_status = "Good Plank!"
                    plank_time += 1 / 30  # Assuming 30 FPS for the webcam
                elif plank_angle <= 160:
                    plank_status = "Hips Too Low!"
                    plank_time = 0
                elif plank_angle >= 180:
                    plank_status = "Hips Too High!"
                    plank_time = 0

                cv2.putText(image, f"Angle: {int(plank_angle)}",
                            tuple(np.multiply(left_hip, [640, 480]).astype(int)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2, cv2.LINE_AA)

            except Exception as e:
                plank_status = "No Person Detected!"
                plank_time = 0
                print(f"Error: {e}")

            cv2.rectangle(image, (0, 0), (640, 100), (245, 117, 16), -1)
            cv2.putText(image, plank_status, (10, 40),
                        cv2.FONT_HERSHEY_SIMPLEX , 1, (255, 255, 255), 2, cv2.LINE_AA)
            cv2.putText(image, f"Time: {int(plank_time)} sec", (10, 80),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)

            self.mp_drawing.draw_landmarks(image, results.pose_landmarks, self.mp_pose.POSE_CONNECTIONS,
                                      self.mp_drawing.DrawingSpec(color=(245, 117, 66), thickness=2, circle_radius=2),
                                      self.mp_drawing.DrawingSpec(color=(245, 66, 230), thickness=2, circle_radius=2))

            cv2.imshow('Plank Tracker', image)

            if cv2.waitKey(10) & 0xFF == ord('q'):
                break

        self.release_camera()

app = PostureAnalyzer()