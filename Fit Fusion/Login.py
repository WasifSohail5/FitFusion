import datetime
import random
import sys
import sqlite3
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QStackedWidget, \
    QTabWidget, QSizePolicy, QHBoxLayout, QMessageBox, QTextEdit, QSlider, QComboBox, QDialog, QProgressBar, \
    QScrollArea, QGridLayout, QAction
from PyQt5.QtCore import Qt, QTimer, QSize
from PyQt5.QtGui import QPixmap, QBrush, QPalette, QIcon, QImage
import speech_recognition as sr  # Added for voice recognition
import threading
# Backend
import google.generativeai as genai
import requests
from PyQt5.QtGui import QMovie  # For animated GIFs
import time
import playsound  # To play audio cues


import pyttsx3  # For text-to-speech
from gtts import gTTS  # Optional alternative for text-to-speech
import os  # To handle audio playback

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import mplcursors

import cv2
import mediapipe as mp
import numpy as np

from Database import (login_database as supabase_login, signup_database as supabase_signup,
                      streak_count_database as supabase_streak
, reset_streak as supabase_streakReset, set_bmi_database as supabase_bmi, supabase)

from PoseTracker import *

class BMI:
    def __init__(self):
        self.weight_kg = 0.0
        self.height_m = 0.0
        self.age = 0

    def get_bmi_category(self, bmi):
        if bmi < 18.5:
            return "You are Underweight"
        elif 18.5 <= bmi <= 24.9:
            return "You are Normal weight"
        elif 25.0 <= bmi <= 29.9:
            return "You are Overweight"
        else:
            return "You are Suffering from obesity"

class BMIMetric(BMI):
    def __init__(self, weight_kg, height_cm, age):
        super().__init__()
        self.weight_kg = weight_kg
        self.height_m = height_cm / 100  # Convert height from cm to meters
        self.age = age

    def calculate_bmi(self):
        return self.weight_kg / (self.height_m ** 2)
class MealPlanner:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.spoonacular.com/mealplanner/generate"

        # Initialize Gemini AI
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-pro')
        self.chat = self.model.start_chat(history=[])

        self.system_prompt = """
        You are FitFusion AI, a health and nutrition expert. Provide meal plans based on calorie requirements,
        dietary preferences, and health goals. Ensure the meals are diverse, nutritious, and practical.
        """

    def get_meal_plan(self, target_calories, dietary_preferences=None):
        """Fetch a meal plan using Spoonacular or Gemini AI."""
        params = {
            "apiKey": self.api_key,
            "timeFrame": "day",
            "targetCalories": target_calories,
        }

        # Try Spoonacular API first
        try:
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Spoonacular API error: {e}")

        # Fall back to Gemini AI if Spoonacular fails
        try:
            user_query = f"Suggest meals for {target_calories} calories. Preferences: {dietary_preferences or 'None'}."
            self.chat.send_message(self.system_prompt)
            ai_response = self.chat.send_message(user_query)
            return {"ai_generated": ai_response.text}
        except Exception as e:
            print(f"Gemini AI error: {e}")
            return None


class FitnessAIAssistant:
    def __init__(self, api_key):
        self.api_key = api_key
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-pro')
        self.system_prompt = """
        You are FitFusion AI, an expert in fitness, nutrition, and health. Respond concisely to user queries.
        """
        self.chat = None
        self.initialize_chat()

    def initialize_chat(self):
        """Initialize the chat object with the system prompt."""
        try:
            self.chat = self.model.start_chat(history=[])
            self.chat.send_message(self.system_prompt)
        except Exception as e:
            print(f"Error initializing Gemini AI chat: {e}")

    def send_query(self, user_query: str) -> str:
        """Send a query to Gemini AI and return the response."""
        try:
            if not self.chat:
                self.initialize_chat()
            response = self.chat.send_message(user_query)
            return response.text
        except Exception as e:
            print(f"Error communicating with Gemini AI: {str(e)}")
            return "Sorry, I couldn't process your request at the moment."


class WorkoutPlanner:
    def __init__(self, api_key):
        self.api_key = api_key

    def get_exercises(self, muscle=None, name=None, exercise_type=None):
        base_url = 'https://api.api-ninjas.com/v1/exercises'
        params = {}

        # Add query parameters if they are provided
        if muscle:
            params['muscle'] = muscle
        if name:
            params['name'] = name
        if exercise_type:
            params['type'] = exercise_type

        response = requests.get(base_url, headers={'X-Api-Key': self.api_key}, params=params)

        if response.status_code == requests.codes.ok:
            return response.json()
        else:
            print(f"Error: {response.status_code} - {response.text}")
            return []

    def filter_exercises(self, exercises, filter_key, filter_value):
        return [exercise for exercise in exercises if exercise.get(filter_key) == filter_value]

    def format_exercise_details(self, exercises, total_time):
        if not exercises:
            return "No exercises found for the given criteria."

        time_per_exercise = total_time / len(exercises)
        details = "<h3>Workout Plan:</h3>"
        for idx, exercise in enumerate(exercises, start=1):
            details += f"<b>Exercise {idx}:</b> {exercise['name']}<br>"
            details += f"Type: {exercise['type']}<br>"
            details += f"Equipment: {exercise.get('equipment', 'N/A')}<br>"
            details += f"Difficulty: {exercise['difficulty']}<br>"
            details += f"Instructions: {exercise['instructions']}<br>"
            details += f"Allocated Time: {time_per_exercise:.2f} seconds<br><br>"
        return details

class LoginSignupApp(QWidget):
    def __init__(self, api_key,gemini_api_key):
        super().__init__()
        self.PALE_BLUE = "#B0E0E6"
        self.DARK_BLUE = "#0057B7"
        self.VERY_LIGHT_BLUE = "#E0FFFF"
        self.FONT_FAMILY = "'Segoe UI', Arial, sans-serif"

        self.fitness_ai_assistant = FitnessAIAssistant(gemini_api_key)
        self.meal_planner = MealPlanner(api_key)  # Create an instance of MealPlanner

        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone(sample_rate=16000, chunk_size=1024)
        self.voice_assistant_active = False
        # Pre-adjust ambient noise once during initialization
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source)

        self.central_widget = QStackedWidget(self)

        self.setWindowTitle('FitFusion: Fitness Tracker')
        self.setGeometry(100, 100, 800, 600)  # Set window size
        self.central_widget = QStackedWidget(self)

        self.setLayout(QVBoxLayout())
        self.layout().addWidget(self.central_widget)

        # Add back and forward buttons
        self.back_button = QPushButton("Back")
        self.forward_button = QPushButton("Forward")
        self.get_current_user_id()
        # Set button styles
        self.set_back_button_style(self.back_button)
        self.set_forward_button_style(self.forward_button)

        # Connect buttons to their respective functions
        self.back_button.clicked.connect(self.go_back)
        self.forward_button.clicked.connect(self.go_forward)

        # Add buttons to the layout
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.back_button)
        button_layout.addWidget(self.forward_button)

        self.layout().addLayout(button_layout)

        # Initialize history stack
        self.history = []
        self.current_index = -1
        # Call the initialize_database function at the start of your application
        self.initialize_database()
        self.init_main_ui()
        self.init_login_ui()
        self.init_signup_ui()
        self.init_forgot_password_ui()
        self.init_welcome_ui()


        self.central_widget.setCurrentIndex(0)  # Start with the main UI
        self.add_to_history(0)  # Add main UI to history

    def set_button_style(self, button):
        button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.PALE_BLUE}; 
                color: {self.DARK_BLUE}; 
                font-size: 18px;
                padding: 10px 20px;
                border: 1px solid {self.DARK_BLUE}; 
                border-radius: 4px;
                cursor: pointer;
                transition: all 0.3s ease;
            }}
            QPushButton:hover {{
                background-color: {self.VERY_LIGHT_BLUE}; 
                transform: scale(1.05);
            }}
        """)

    def set_text_field_style(self, text_field):
        text_field.setStyleSheet(f"""
            font-size: 24px;
            padding: 12px;
            border: 2px solid {self.DARK_BLUE}; 
            border-radius: 5px;
            background-color: {self.VERY_LIGHT_BLUE}; 
        """)

    def set_navigation_button_style(self, button):
        button.setStyleSheet(f"""
            QPushButton {{
                font-size: 18px;
                color: {self.DARK_BLUE}; 
                background: transparent;
                border: none;
            }}
            QPushButton:hover {{
                color: {self.PALE_BLUE}; 
                text-decoration: underline;
            }}
        """)

    def set_cta_button_style(self, button):
        button.setStyleSheet(f"""
            QPushButton {{
                font-size: 20px;
                font-weight: bold;
                color: white;
                background: linear-gradient(90deg, {self.DARK_BLUE}, {self.PALE_BLUE}); 
                padding: 15px 30px;
                border: none;
                border-radius: 25px;
            }}
            QPushButton:hover {{
                background: linear-gradient(90deg, {self.DARK_BLUE}, {self.VERY_LIGHT_BLUE}); 
            }}
        """)

    '''def set_background_image(self, image_path):
        self.central_widget.setStyleSheet(f"""
            QStackedWidget {{
                border-image: url({image_path}) 0 0 0 0 stretch stretch;
                animation: background-animation 30s linear infinite;
            }}
            @keyframes background-animation {{
                0% {{ background-position: 0% 50%; }}
                50% {{ background-position: 100% 50%; }}
                100% {{ background-position: 0% 50%; }}
            }}
        """)'''

    def set_back_button_style(self, button):
        button.setStyleSheet("""
            QPushButton {
                background-color: #B0E0E6;  /* Pale Blue */
                color: #0057B7;             /* Dark Blue */
                font-size: 14px;            /* Reduced font size */
                padding: 5px 10px;          /* Reduced padding on x-axis */
                width: 100px;               /* Fixed width */
                border: 1px solid #0057B7;  /* Dark Blue Border */
                border-radius: 4px;         /* Subtle rounded corners */
                cursor: pointer;
                transition: all 0.3s ease;
            }
            QPushButton:hover {
                background-color: #E0FFFF;  /* Very Light Blue */
                transform: scale(1.05);
            }
        """)

    def set_forward_button_style(self, button):
        button.setStyleSheet("""
            QPushButton {
                background-color: #B0E0E6;  /* Pale Blue */
                color: #0057B7;             /* Dark Blue */
                font-size: 14px;            /* Reduced font size */
                padding: 5px 10px;          /* Reduced padding on x-axis */
                width: 100px;               /* Fixed width */
                border: 1px solid #0057B7;  /* Dark Blue Border */
                border-radius: 4px;         /* Subtle rounded corners */
                cursor: pointer;
                transition: all 0.3s ease;
            }
            QPushButton:hover {
                background-color: #E0FFFF;  /* Very Light Blue */
                transform: scale(1.05);
            }
        """)

    def add_to_history(self, index):
        """Add the current index to the history."""
        if self.current_index + 1 < len(self.history):
            self.history = self.history[:self.current_index + 1]

        self.history.append(index)
        self.current_index += 1

    def go_back(self):
        """Navigate to the previous view."""
        if self.current_index > 0:
            self.current_index -= 1
            self.central_widget.setCurrentIndex(self.history[self.current_index])

    def go_forward(self):
        """Navigate to the next view."""
        if self.current_index < len(self.history) - 1:
            self.current_index += 1
            self.central_widget.setCurrentIndex(self.history[self.current_index])

    def init_main_ui(self):

        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)

        # Set background image
        self.set_background_image("background_image_blue.png")

        # HEADER SECTION
        self.create_header(main_layout)

        # About Us, Features, Contact Sections
        self.create_info_sections(main_layout)

        # CENTERED LOGIN/REGISTER BOX
        self.create_login_register_box(main_layout)

        # Motivational Quote Section
        self.create_quote_section(main_layout)

        self.central_widget.addWidget(main_widget)

    def create_header(self, layout):
        header_layout = QHBoxLayout()
        header_layout.setSpacing(15)

        # Logo Section
        logo_label = QLabel("🏋️ FitFusion", self)
        logo_label.setStyleSheet("""
            font-size: 35px;
            font-weight: bold;
            color: #B0E0E6;  /* Pale Blue */
            font-family: 'Segoe UI', Arial, sans-serif;
        """)
        logo_label.setAlignment(Qt.AlignLeft)
        header_layout.addWidget(logo_label)

        additional_logo_label = QLabel(self)
        additional_logo_label.setPixmap(QPixmap("email_logo.png"))  # Replace with actual image path
        additional_logo_label.setScaledContents(True)
        additional_logo_label.setMaximumSize(100, 100)
        header_layout.addWidget(additional_logo_label)

        # Navigation Section
        nav_layout = QHBoxLayout()
        nav_links = {
            "About Us": self.toggle_about_us,
            "Features": self.toggle_features,
            "Contact": self.toggle_contact
        }

        for link, function in nav_links.items():
            nav_button = QPushButton(link, self)
            nav_button.setStyleSheet("""
                QPushButton {
                    background-color: #B0E0E6;  /* Pale Blue */
                    border: 1px solid #0057B7;  /* Dark Blue Border */
                    color: #0057B7;  /* Dark Blue */
                    font-family: 'Segoe UI', Arial, sans-serif;
                    font-size: 15px;
                    padding: 10px;
                    border-radius: 5px;
                    margin-left: 10px;
                }
                QPushButton:hover {
                    background-color: #E0FFFF;  /* Very Light Blue */
                }
            """)
            nav_button.setToolTip(f"Learn more about {link}")
            nav_button.clicked.connect(function)
            nav_layout.addWidget(nav_button)

        nav_widget = QWidget()
        nav_widget.setLayout(nav_layout)
        nav_widget.setStyleSheet("""
            QWidget {
                background-color: white;  
                border-radius: 15px;
                padding: 0px;
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
            }
        """)

        header_layout.addWidget(nav_widget)
        header_layout.addStretch(1)

        layout.addLayout(header_layout)

    def create_info_sections(self, layout):
        self.about_us_section = self.create_info_section(
            "About FitFusion",
            "FitFusion is your personal fitness companion, helping you achieve your goals. "
            "Our mission is to make fitness accessible, enjoyable, and efficient for everyone. "
            "Whether you're a beginner or a pro, FitFusion has something for you."
        )
        layout.addWidget(self.about_us_section)

        self.features_section = self.create_info_section(
            "Features",
            "<ul>"
            "<li><strong>Meal Planning:</strong> Personalized meal plans to meet your nutritional needs.</li>"
            "<li><strong>Fitness Tracking:</strong> Track your workouts, progress, and set goals.</li>"
            "<li><strong>AI-Driven Advice:</strong> Get tailored fitness advice based on your data and preferences.</li>"
            "<li><strong>Community Support:</strong> Join groups, share your progress, and get motivated.</li>"
            "</ul>"
        )
        layout.addWidget(self.features_section)

        self.contact_section = self.create_info_section(
            "Contact Us",
            "Have questions or need support? Reach out to us!<br>"
            "Email: <a href='mailto:contact@fitfusion.com' style='color: #0057B7;'>contact@fitfusion.com</a><br>"
            "Phone: +1-800-123-4567<br>"
            "Follow us on social media for updates and tips:<br>"
            "<a href='https://twitter.com/fitfusion' style='color: #0057B7;'>Twitter</a> | "
            "<a href='https://www.facebook.com/fitfusion' style='color: #0057B7;'>Facebook</a> | "
            "<a href='https://www.instagram.com/fitfusion' style='color: #0057B7;'>Instagram</a>"
        )
        layout.addWidget(self.contact_section)

    def create_info_section(self, title, content):
        section = QWidget()
        layout = QVBoxLayout(section)
        section.setStyleSheet("""
            QWidget {
                background-color: #E0FFFF; 
                border-radius: 15px;
                padding: 5px;
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
                margin-top: 10px;
            }
        """)

        title_label = QLabel(f"<h2 style='color: #0057B7;'>{title}</h2>")  # Use direct color code
        content_label = QLabel(content)
        content_label.setStyleSheet("font-size: 16px; font-family: 'Segoe UI', Arial, sans-serif; color: #333;")
        content_label.setWordWrap(True)  # Enable word wrap to properly display multiline text

        layout.addWidget(title_label)
        layout.addWidget(content_label)
        section.hide()
        return section

    def create_login_register_box(self, layout):
        box_widget = QWidget()
        box_layout = QVBoxLayout(box_widget)
        box_widget.setStyleSheet("""
               QWidget {
                   background-color: white; 
                   border-radius: 15px;
                   padding: 20px;
                   max-width: 400px;
                   margin: 0 auto;
                   box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
               }
           """)

        tagline_label = QLabel("Your Fitness Journey Starts Today!", self)
        tagline_label.setStyleSheet(f"""
               font-size: 20px;
               font-weight: bold;
               color: {self.DARK_BLUE}; 
               font-family: {self.FONT_FAMILY};
               margin-bottom: 15px;
           """)
        tagline_label.setAlignment(Qt.AlignCenter)
        box_layout.addWidget(tagline_label)

        box_layout.addSpacing(10)

        btn_login = QPushButton("Login", self)

        self.set_button_style(btn_login)
        btn_login.setToolTip("Click to login to your account")
        btn_login.clicked.connect(self.switch_to_login)
        box_layout.addWidget(btn_login)

        btn_signup = QPushButton("Sign Up", self)
        self.set_button_style(btn_signup)
        btn_signup.setToolTip("Click to create a new account")
        btn_signup.clicked.connect(self.switch_to_signup)
        box_layout.addWidget(btn_signup)

        layout.addStretch(1)
        layout.addWidget(box_widget, alignment=Qt.AlignCenter)
        layout.addStretch(1)


    def create_quote_section(self, layout):
        quotes = [
            "Believe you can and you're halfway there.",
            "Your limitation—it's only your imagination.",
            "Push yourself, because no one else is going to do it for you.",
            "Great things never come from comfort zones.",
            "Success doesn’t just find you. You have to go out and get it."
        ]
        random_quote = random.choice(quotes)
        quote_box_widget = QWidget()
        quote_box_layout = QVBoxLayout(quote_box_widget)
        quote_box_widget.setStyleSheet("""
                   QWidget {
                       background-color: white; 
                       border-radius: 15px;
                       padding: 20px;
                       max-width: 400px;
                       margin: 0 auto;
                       box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
                   }
               """)

        quote_label = QLabel(f"\"{random_quote}\"", self)
        quote_label.setStyleSheet("""
                   font-size: 18px;
                   font-weight: bold;
                   color: #333;
                   font-family: 'Segoe UI', Arial, sans-serif;
                   text-align: center;
               """)
        quote_box_layout.addWidget(quote_label)

        layout.addWidget(quote_box_widget, alignment=Qt.AlignCenter)


    def toggle_about_us(self):
        self.features_section.hide()
        self.contact_section.hide()
        self.about_us_section.setVisible(not self.about_us_section.isVisible())


    def toggle_features(self):
        self.about_us_section.hide()
        self.contact_section.hide()
        self.features_section.setVisible(not self.features_section.isVisible())


    def toggle_contact(self):
        self.about_us_section.hide()
        self.features_section.hide()
        self.contact_section.setVisible(not self.contact_section.isVisible())



    def switch_to_login(self):
        self.central_widget.setCurrentIndex(1)  # Switch to login
        self.add_to_history(1)  # Add login UI to history

    def switch_to_signup(self):
        self.central_widget.setCurrentIndex(2)  # Switch to signup
        self.add_to_history(2)  # Add signup UI to history

    def init_login_ui(self):
        """Login UI with enhanced interaction"""
        login_widget = QWidget()
        layout = QVBoxLayout(login_widget)

        # Login Box
        box_widget = QWidget()
        box_layout = QVBoxLayout(box_widget)
        box_widget.setStyleSheet("""
            QWidget {
                background-color: white;  /* Very Light Blue */
                border-radius: 15px;
                padding: 30px;  /* Increased padding for better spacing */
                max-width: 600px;  /* Increased width for a larger box */
                margin: 20px auto;  /* Increased margin for better positioning */
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
            }
        """)

        # Login Form UI with Custom Styling
        email_label = QLabel("Email: ", self)
        email_label.setStyleSheet("font-size: 30px; color: #0057B7; font-weight: bold;")  # Dark Blue
        box_layout.addWidget(email_label)

        self.login_email = QLineEdit(self)
        self.set_text_field_style(self.login_email)
        self.login_email.setPlaceholderText("Enter your email")
        box_layout.addWidget(self.login_email)

        password_label = QLabel("Password: ", self)
        password_label.setStyleSheet("font-size: 30px; color: #0057B7; font-weight: bold;")  # Dark Blue
        box_layout.addWidget(password_label)

        self.login_password = QLineEdit(self)
        self.set_text_field_style(self.login_password)
        self.login_password.setEchoMode(QLineEdit.Password)
        self.login_password.setPlaceholderText("Enter your password")
        box_layout.addWidget(self.login_password)

        # Login button with animation and feedback
        btn_login = QPushButton("Login", self)
        self.set_button_style(btn_login)
        btn_login.setStyleSheet(btn_login.styleSheet() + "font-size: 25px; margin-top: 20px; font-weight: bold;")
        btn_login.clicked.connect(self.on_login_button_click)
        box_layout.addWidget(btn_login)

        # Feedback label
        self.login_feedback = QLabel("", self)
        self.login_feedback.setStyleSheet("font-size: 25px; color: #0057B7;")  # Dark Blue
        box_layout.addWidget(self.login_feedback)

        # Forgot Password Button
        btn_forgot_password = QPushButton("Forgot Password?", self)
        self.set_button_style(btn_forgot_password)
        btn_forgot_password.clicked.connect(self.open_forgot_password_window)
        box_layout.addWidget(btn_forgot_password)

        layout.addStretch(1)
        layout.addWidget(box_widget, alignment=Qt.AlignCenter)
        layout.addStretch(1)

        self.central_widget.addWidget(login_widget)

    def on_login_button_click(self):
        """Triggered when the login button is clicked."""
        email = self.login_email.text().strip()
        password = self.login_password.text().strip()

        if not email:
            self.login_feedback.setText("Please enter your email.")
            return
        if not password:
            self.login_feedback.setText("Please enter your password.")
            return

        self.login_feedback.setText("")  # Clear previous feedback
        self.login_database()


    def login_database(self):
        """Check credentials in the Supabase database for login"""
        email = self.login_email.text().strip()
        password = self.login_password.text().strip()

        try:
            # Call the Supabase login function
            result = supabase_login(email, password)

            if isinstance(result, str):  # If login is successful and a user ID is returned
                self.current_user_id = result  # Store the user ID
                self.login_feedback.setStyleSheet("font-size: 25px; color: #0057B7;")
                self.login_feedback.setText(f"Login successful. Welcome User ID: {result}!")
                self.show_welcome_frame(result)  # Show welcome frame upon successful login
            else:
                self.login_feedback.setStyleSheet("font-size: 25px; color: #0057B7;")
                self.login_feedback.setText("Account not recognized. Please sign up.")
        except Exception as e:
            # Handle any exceptions from the Supabase login
            self.login_feedback.setStyleSheet("font-size: 25px; color: red;")
            self.login_feedback.setText(f"Login failed. Error: {e}")

    def open_forgot_password_window(self, event):
        """Open the forgot password dialog"""
        self.central_widget.setCurrentIndex(3)  # Switch to forgot password UI
        self.add_to_history(3)  # Add forgot password UI to history

    def init_forgot_password_ui(self):
        """Forgot Password UI"""
        forgot_widget = QWidget()
        layout = QVBoxLayout(forgot_widget)

        # Forgot Password Box
        box_widget = QWidget()
        box_layout = QVBoxLayout(box_widget)
        box_widget.setStyleSheet("""
            QWidget {
                background-color: white;  /* Very Light Blue */
                border-radius: 15px;
                padding: 20px;
                max-width: 400px;
                margin: 0 auto;
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
            }
        """)

        # Label and input for email
        email_label = QLabel("Enter your registered email:", self)
        email_label.setStyleSheet("font-size: 25px; color: #0057B7; font-weight: bold;")  # Dark Blue
        box_layout.addWidget(email_label)

        self.forgot_email = QLineEdit(self)
        self.set_text_field_style(self.forgot_email)
        self.forgot_email.setPlaceholderText("Enter your email")
        box_layout.addWidget(self.forgot_email)

        # Submit button for password reset
        btn_reset = QPushButton("Reset Password", self)
        self.set_button_style(btn_reset)
        btn_reset.setStyleSheet(btn_reset.styleSheet() + "font-size: 25px; margin-top: 20px; font-weight: bold;")
        btn_reset.clicked.connect(self.reset_password)
        box_layout.addWidget(btn_reset)

        # Feedback label
        self.forgot_password_feedback = QLabel("", self)
        self.forgot_password_feedback.setStyleSheet("font-size: 25px; color: #0057B7;")  # Dark Blue
        box_layout.addWidget(self.forgot_password_feedback)

        layout.addStretch(1)
        layout.addWidget(box_widget, alignment=Qt.AlignCenter)
        layout.addStretch(1)

        self.central_widget.addWidget(forgot_widget)

    def reset_password(self):
        """Simulate password reset process (for now just a placeholder)"""
        email = self.forgot_email.text().strip()

        if not email:
            self.forgot_password_feedback.setText("Please enter your email.")
            return

        # Here you would typically send the email for password reset
        # For now, we will simulate this with a message
        self.forgot_password_feedback.setText(
            "Password reset instructions sent")
        # Do not switch back to the main UI; stay on the forgot password screen

    def init_login_ui(self):
        login_widget = QWidget()
        layout = QVBoxLayout(login_widget)

        # Login Box
        box_widget = QWidget()
        box_layout = QVBoxLayout(box_widget)
        box_widget.setStyleSheet("""
            QWidget {
                background-color: #E0FFFF; /* Very Light Blue */
                border-radius: 15px;
                padding: 20px;
                max-width: 400px;
                margin: 0 auto;
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
            }
        """)

        # Login Form UI with Custom Styling
        email_label = QLabel("Email: ", self)
        email_label.setStyleSheet("font-size: 30px; color: #0057B7; font-weight: bold;")  # Dark Blue
        box_layout.addWidget(email_label)

        self.login_email = QLineEdit(self)
        self.set_text_field_style(self.login_email)
        self.login_email.setPlaceholderText("Enter your email")
        box_layout.addWidget(self.login_email)

        password_label = QLabel("Password: ", self)
        password_label.setStyleSheet("font-size: 30px; color: #0057B7; font-weight: bold;")  # Dark Blue
        box_layout.addWidget(password_label)

        self.login_password = QLineEdit(self)
        self.set_text_field_style(self.login_password)
        self.login_password.setEchoMode(QLineEdit.Password)
        self.login_password.setPlaceholderText("Enter your password")
        box_layout.addWidget(self.login_password)

        # Login button with animation and feedback
        btn_login = QPushButton("Login", self)
        self.set_button_style(btn_login)
        btn_login.setStyleSheet(btn_login.styleSheet() + "font-size: 25px; margin-top: 20px; font-weight: bold;")
        btn_login.clicked.connect(self.on_login_button_click)
        box_layout.addWidget(btn_login)

        # Feedback label
        self.login_feedback = QLabel("", self)
        self.login_feedback.setStyleSheet("font-size: 25px; color: #0057B7;")  # Dark Blue
        box_layout.addWidget(self.login_feedback)

        # Forgot Password Button
        btn_forgot_password = QPushButton("Forgot Password?", self)
        self.set_button_style(btn_forgot_password)
        btn_forgot_password.clicked.connect(self.open_forgot_password_window)
        box_layout.addWidget(btn_forgot_password)

        layout.addStretch(1)
        layout.addWidget(box_widget, alignment=Qt.AlignCenter)
        layout.addStretch(1)

        self.central_widget.addWidget(login_widget)

    def initialize_database(self):
        """Test Supabase connection and streak table availability."""
        try:
            # Check if the 'streaks' table exists
            response = supabase.table('streaks').select('*').limit(1).execute()
            print("Supabase connection successful. Streaks table is available.")
        except Exception as e:
            print(f"Error connecting to Supabase: {e}")

    def init_signup_ui(self):
        # Signup UI
        signup_widget = QWidget()
        layout = QVBoxLayout(signup_widget)
        layout.setAlignment(Qt.AlignCenter)

        # Main Signup Box
        box_widget = QWidget()
        box_layout = QVBoxLayout(box_widget)
        box_widget.setStyleSheet("""
            QWidget {
                background-color: white;  /* Background color */
                border-radius: 20px;
                padding: 40px;
                max-width: 800px;  /* Increased width for better fitting elements */
                margin: 30px auto;
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
            }
        """)

        # Header
        header_label = QLabel("Create Your Account", self)
        header_label.setStyleSheet("font-size: 36px; color: #0057B7; font-weight: bold; margin-bottom: 20px;")
        header_label.setAlignment(Qt.AlignCenter)
        box_layout.addWidget(header_label)

        # User Name Box
        user_name_box = QWidget()
        user_name_layout = QVBoxLayout(user_name_box)
        user_name_box.setStyleSheet("""
            QWidget {
                background-color: #E0FFFF;  /* Very Light Blue */
                border-radius: 10px;
                padding: 1px;
                margin-bottom: 0px;  /* Spacing between boxes */
            }
        """)
        self.signup_name = self.create_labeled_input(user_name_layout, "User Name:", "Enter your name",
                                                     "profile_6915911.png")
        box_layout.addWidget(user_name_box)

        # User Email Box
        user_email_box = QWidget()
        user_email_layout = QVBoxLayout(user_email_box)
        user_email_box.setStyleSheet("""
            QWidget {
                background-color: #E0FFFF;  /* Very Light Blue */
                border-radius: 10px;
                padding: 1px;
                margin-bottom: 0px;  /* Spacing between boxes */
            }
        """)
        self.signup_email = self.create_labeled_input(user_email_layout, "User Email:", "Enter your email",
                                                      "email_552486.png")
        box_layout.addWidget(user_email_box)

        # Password Box
        password_box = QWidget()
        password_layout = QVBoxLayout(password_box)
        password_box.setStyleSheet("""
            QWidget {
                background-color: #E0FFFF;  /* Very Light Blue */
                border-radius: 10px;
                padding: 1px;
                margin-bottom: 0px;  /* Spacing between boxes */
            }
        """)
        self.signup_password = self.create_labeled_input(password_layout, "Password:", "Enter your password",
                                                         "lock_17777135.png", is_password=True)
        box_layout.addWidget(password_box)

        # Confirm Password Box
        confirm_password_box = QWidget()
        confirm_password_layout = QVBoxLayout(confirm_password_box)
        confirm_password_box.setStyleSheet("""
            QWidget {
                background-color: #E0FFFF;  /* Very Light Blue */
                border-radius: 10px;
                padding: 1px;
                margin-bottom: 0px;  /* Spacing between boxes */
            }
        """)
        self.confirm_password = self.create_labeled_input(confirm_password_layout, "Confirm Password:",
                                                          "Re-enter your password",
                                                          "lock_17777135.png", is_password=True)
        box_layout.addWidget(confirm_password_box)

        # Feedback label
        self.signup_feedback = QLabel("", self)
        self.signup_feedback.setStyleSheet("font-size: 20px; color:#0057B7; margin-top: 15px;")  # Red for feedback
        self.signup_feedback.setAlignment(Qt.AlignCenter)
        box_layout.addWidget(self.signup_feedback)

        # Sign up button
        btn_signup = QPushButton("Signup", self)
        self.set_button_style(btn_signup)
        btn_signup.setStyleSheet(btn_signup.styleSheet() + """
            font-size: 25px; 
            margin-top: 20px; 
            font-weight: bold;
            min-width: 150px;  /* Minimum width */
            min-height: 40px;  /* Minimum height */
        """)
        btn_signup.clicked.connect(self.on_signup_button_click)
        box_layout.addWidget(btn_signup)

        # Footer with Terms and Conditions
        footer_label = QLabel("By signing up, you agree to our Terms and Conditions.", self)
        footer_label.setStyleSheet("font-size: 14px; color: #808080; margin-top: 20px;")
        footer_label.setAlignment(Qt.AlignCenter)
        box_layout.addWidget(footer_label)

        layout.addWidget(box_widget)
        self.central_widget.addWidget(signup_widget)

    def create_labeled_input(self, layout, label_text, placeholder_text, logo_path, is_password=False):
        """Helper method to create labeled input fields with logo placeholders."""
        container_widget = QWidget()
        container_layout = QHBoxLayout(container_widget)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(10)

        label = QLabel(label_text, self)
        label.setStyleSheet("font-size: 24px; color: #0057B7; font-weight: bold; margin-right: 10px;")
        container_layout.addWidget(label)

        input_field = QLineEdit(self)
        self.set_text_field_style(input_field)
        input_field.setPlaceholderText(placeholder_text)
        input_field.setFixedHeight(50)
        input_field.setStyleSheet("""
            QLineEdit {
                font-size: 18px;
                padding-left: 2px;
            }
            QLineEdit::placeholder {
                font-size: 18px;
                color: #999;
            }
        """)

        # Add logo
        icon_pixmap = QPixmap(logo_path).scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        action = QAction(self)
        action.setIcon(QIcon(icon_pixmap))
        input_field.addAction(action, QLineEdit.LeadingPosition)

        if is_password:
            input_field.setEchoMode(QLineEdit.Password)

        container_layout.addWidget(input_field)
        layout.addWidget(container_widget)
        return input_field

    def on_signup_button_click(self):
        """Handle the signup button click event."""
        password = self.signup_password.text()
        confirm_password = self.confirm_password.text()

        if password != confirm_password:
            self.signup_feedback.setText("Passwords do not match. Please try again.")
        else:
            self.signup_feedback.setText("")
            self.signup_database()

    from Database import signup_database as supabase_signup  # Import the Supabase signup function

    def signup_database(self):
        """Handle Supabase-based actions for signup"""
        name = self.signup_name.text().strip()
        email = self.signup_email.text().strip()
        password = self.signup_password.text().strip()

        # Validate that all fields are filled
        if not name or not email or not password:
            self.signup_feedback.setText("Please fill in all fields.")
            return

        try:
            # Call the Supabase signup function
            result = supabase_signup(email, password, name)

            if "Signup successful" in result:
                # If signup is successful, clear inputs and provide feedback
                self.signup_feedback.setStyleSheet("font-size: 25px; color: #0057B7;")
                self.signup_feedback.setText(result)
                self.signup_name.clear()
                self.signup_email.clear()
                self.signup_password.clear()
                self.central_widget.setCurrentIndex(0)  # Go back to the main UI
                self.add_to_history(0)  # Add main UI to history
            else:
                # If signup fails, display the error message
                self.signup_feedback.setStyleSheet("font-size: 25px; color: red;")
                self.signup_feedback.setText(result)

        except Exception as e:
            # Handle unexpected errors
            self.signup_feedback.setStyleSheet("font-size: 25px; color: red;")
            self.signup_feedback.setText(f"An error occurred: {e}")

    def init_welcome_ui(self):
        """Show a welcome frame after successful login"""
        welcome_widget = QWidget()
        layout = QVBoxLayout(welcome_widget)

        # Welcome message
        self.welcome_msg = QLabel("", self)
        self.welcome_msg.setStyleSheet("font-size: 40px; font-weight: bold; color: #333333;")
        self.welcome_msg.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.welcome_msg)

        # No Logout button here
        self.central_widget.addWidget(welcome_widget)

    def show_welcome_frame(self, user_name):
        """Show welcome message and initialize tabs after successful login"""
        self.central_widget.setCurrentIndex(5)  # Switch to a new index for tabs
        self.init_tabs(user_name)  # Initialize tabs
        self.add_to_history(5)  # Add tabs UI to history

    def init_tabs(self, user_name):
        """Initialize the tabbed interface after login with Logout as the last tab"""
        tabs_widget = QWidget()
        tabs_layout = QVBoxLayout(tabs_widget)

        # Create QTabWidget
        self.tabs = QTabWidget()

        # Apply the updated style sheet for colorful and fitting tab buttons
        self.tabs.setStyleSheet("""
            QTabBar::tab {
                background-color: #B0E0E6;  /* Pale Blue Background */
                color: #0057B7;             /* Dark Blue Text */
                font-size: 14px;            /* Font size */
                padding: 10px 25px;         /* Ensure proper padding for better visibility */
                border: 1px solid #0057B7;  /* Dark Blue Border */
                border-bottom: none;        /* Smooth look */
                border-radius: 4px;         /* Rounded corners */
                min-width: 100px;           /* Minimum width to prevent truncation */
            }

            QTabBar::tab:selected {
                background-color: #0057B7;  /* Dark Blue for Selected Tab */
                color: #FFFFFF;             /* White Text for Contrast */
                font-weight: bold;          /* Bold text for selected tab */
            }

            QTabBar::tab:hover {
                background-color: #87CEEB;  /* Light Sky Blue on Hover */
                color: #0057B7;             /* Dark Blue Text */
            }

            QTabWidget::pane {
                border: 2px solid #0057B7;  /* Dark Blue Border Around Tab Content */
                background-color: #E0FFFF;  /* Very Light Blue Background for Pane */
            }
        """)

        # Create individual tabs
        self.create_workout_planner_tab()
        self.create_pose_tracker_tab()
        self.create_streak_tab()
        self.create_bmi_visualization_tab()
        self.create_meal_planner_tab()
        self.create_interactive_assistant_tab()
        self.create_help_tab()

        # Add the Logout button as a tab
        logout_tab = QWidget()
        logout_layout = QVBoxLayout(logout_tab)

        # Create Logout button
        btn_logout = QPushButton("Logout", self)
        btn_logout.setStyleSheet("""
            QPushButton {
                background-color: #0057B7;
                color: white;
                font-size: 16px;
                padding: 10px 15px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #003C88;
            }
        """)
        btn_logout.clicked.connect(self.logout)

        # Add Logout button to the tab layout
        logout_layout.addWidget(btn_logout)
        logout_layout.addStretch()  # Add stretch to center the button in the tab

        # Add the Logout tab
        self.tabs.addTab(logout_tab, "Logout")

        # Add the QTabWidget to the layout
        tabs_layout.addWidget(self.tabs)

        # Set the tabs widget as the central widget
        self.central_widget.addWidget(tabs_widget)
        self.central_widget.setCurrentWidget(tabs_widget)  # Show the tabs widget

    def create_pose_tracker_tab(self):
        pose_tab = QWidget()
        layout = QVBoxLayout(pose_tab)

        # Title
        label = QLabel("Pose Tracker", self)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("""
            font-size: 20px;
            font-weight: bold;
            color: #0057B7;  /* Dark Blue for the label text */
            background-color: #B0E0E6;  /* Pale Blue for the background */
            padding: 10px;
            border-radius: 5px;
        """)
        layout.addWidget(label)

        # Instructions
        instructions_label = QLabel("Choose an exercise to track:", self)
        instructions_label.setStyleSheet("""
            font-size: 20px;
            font-weight: bold;
            color: #0057B7;  /* Dark Blue for the label text */
            background-color: #B0E0E6;  /* Pale Blue for the background */
            padding: 10px;
            border-radius: 5px;
        """)
        instructions_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(instructions_label)

        # Exercise Selection Label
        exercise_selection_label = QLabel("Select Exercise:", self)
        exercise_selection_label.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: #0057B7;  /* Dark Blue text */
            background-color: white;  /* Light Blue background */
            padding: 5px;
            border-radius: 5px;
        """)
        exercise_selection_label.setFixedWidth(exercise_selection_label.sizeHint().width())  # Adjust width to text
        layout.addWidget(exercise_selection_label)

        # Exercise Selection ComboBox
        self.exercise_combo = QComboBox(self)
        self.exercise_combo.addItems(["Biceps Curl", "Squat", "Push Up", "Plank"])
        self.exercise_combo.setStyleSheet("""
            background-color: #E0FFFF;  /* Very Light Blue */
            font-size: 16px;
            padding: 5px;
            border: 2px solid #0057B7;  /* Dark Blue Border */
            border-radius: 5px;
            color: #0057B7;  /* Dark Blue Text */
        """)
        layout.addWidget(self.exercise_combo)

        # Start Tracking Button
        start_button = QPushButton("Start Tracking", self)
        start_button.setStyleSheet("""
            QPushButton {
                background-color: #0057B7;
                color: white;
                font-size: 18px;
                padding: 10px 20px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #003C88;
            }
        """)
        start_button.clicked.connect(self.start_pose_tracking)
        layout.addWidget(start_button)

        # Feedback Area Label
        feedback_label = QLabel("Feedback:", self)
        feedback_label.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: #0057B7;  /* Dark Blue text */
            background-color: white;  /* Light Blue background */
            padding: 5px;
            border-radius: 5px;
        """)
        feedback_label.setFixedWidth(feedback_label.sizeHint().width())  # Adjust width to text
        layout.addWidget(feedback_label)

        # Feedback Area
        self.pose_feedback = QTextEdit(self)
        self.pose_feedback.setReadOnly(True)
        self.pose_feedback.setStyleSheet("""
            background-color: #E0FFFF;
            font-size: 16px;
            padding: 10px;
            border: 2px solid #0057B7;
            border-radius: 5px;
            color: #0057B7;
        """)
        layout.addWidget(self.pose_feedback)

        # Video Feed Label
     #   self.video_feed_label = QLabel(self)
      #  self.video_feed_label.setFixedSize(640, 480)  # Set size for the video feed
       # layout.addWidget(self.video_feed_label)

        # Add tab
        self.tabs.addTab(pose_tab, "Pose Tracker")

    def start_pose_tracking(self):
        selected_exercise = self.exercise_combo.currentText()
        self.pose_feedback.append(f"Starting {selected_exercise} analysis...")

        # Start the pose tracking in a separate thread
        self.pose_thread = threading.Thread(target=self.run_pose_tracker, args=(selected_exercise,))
        self.pose_thread.start()

    def run_pose_tracker(self, exercise):
        # Initialize the posture analyzer
        posture_analyzer = PostureAnalyzer()

        # Start the video capture
        posture_analyzer.cap = cv2.VideoCapture(0)

        while True:
            ret, frame = posture_analyzer.cap.read()
            if not ret:
                break

            # Process the frame with the posture analyzer
            # Here you can call the specific analysis method based on the selected exercise
            if exercise == "Biceps Curl":
                posture_analyzer.analyze_biceps_curl()
            elif exercise == "Squat":
                posture_analyzer.analyze_squat()
            elif exercise == "Push Up":
                posture_analyzer.analyze_pushups()
            elif exercise == "Plank":
                posture_analyzer.analyze_plank()

            '''# Convert the frame to RGB format for displaying in QLabel
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = frame.shape
            bytes_per_line = ch * w
            q_img = QImage(frame.data, w, h, bytes_per_line, QImage.Format_RGB888)

            # Update the QLabel with the new frame
            self.video_feed_label.setPixmap(QPixmap.fromImage(q_img))
            '''
            # Allow the GUI to process events
            QApplication.processEvents()

        posture_analyzer.cap.release()







    def create_workout_planner_tab(self):
        workout_tab = QWidget()
        layout = QVBoxLayout(workout_tab)

        # Title with updated label color matching the blue theme
        label = QLabel("Workout Planner", self)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("""
            font-size: 20px;
            font-weight: bold;
            color: #0057B7;  /* Dark Blue for the label text */
            background-color: #B0E0E6;  /* Pale Blue for the background */
            padding: 10px;
            border-radius: 5px;
        """)
        layout.addWidget(label)

        # Muscle Group Label
        muscle_group_label = QLabel("Muscle Group:", self)
        muscle_group_label.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: #0057B7;  /* Dark Blue text */
            background-color: white;  /* Light Blue background */
            padding: 5px;
            border-radius: 5px;
        """)
        muscle_group_label.setFixedWidth(muscle_group_label.sizeHint().width())  # Adjust width to text
        layout.addWidget(muscle_group_label)

        # Muscle Group ComboBox
        self.muscle_group_combo = QComboBox(self)
        self.muscle_group_combo.addItems([
            "", "Abdominals", "Abductors", "Adductors", "Biceps", "Calves",
            "Chest", "Forearms", "Glutes", "Hamstrings", "Lats", "Lower Back",
            "Middle Back", "Neck", "Quadriceps", "Traps", "Triceps"
        ])
        self.muscle_group_combo.setStyleSheet("""
            background-color: #E0FFFF;  /* Very Light Blue */
            font-size: 16px;
            padding: 5px;
            border: 2px solid #0057B7;  /* Dark Blue Border */
            border-radius: 5px;
            color: #0057B7;             /* Dark Blue Text */
        """)
        layout.addWidget(self.muscle_group_combo)

        # Exercise Name Label
        exercise_name_label = QLabel("Exercise Name:", self)
        exercise_name_label.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: #0057B7;
            background-color: white;  /* Light Blue background */
            padding: 5px;
            border-radius: 5px;
        """)
        exercise_name_label.setFixedWidth(exercise_name_label.sizeHint().width())  # Adjust width to text
        layout.addWidget(exercise_name_label)

        # Exercise Name Input
        self.exercise_name_input = QLineEdit(self)
        self.exercise_name_input.setPlaceholderText("Partial Exercise Name (e.g., press, squat)")
        self.exercise_name_input.setStyleSheet("""
            background-color: #E0FFFF;
            font-size: 16px;
            padding: 5px;
            border: 2px solid #0057B7;
            border-radius: 5px;
            color: #0057B7;
        """)
        layout.addWidget(self.exercise_name_input)

        # Exercise Type Label
        exercise_type_label = QLabel("Exercise Type:", self)
        exercise_type_label.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: #0057B7;
            background-color: white;  /* Light Blue background */
            padding: 5px;
            border-radius: 5px;
        """)
        exercise_type_label.setFixedWidth(exercise_type_label.sizeHint().width())  # Adjust width to text
        layout.addWidget(exercise_type_label)

        # Exercise Type ComboBox
        self.exercise_type_combo = QComboBox(self)
        self.exercise_type_combo.addItems([
            "", "Cardio", "Olympic Weightlifting", "Plyometrics", "Powerlifting",
            "Strength", "Stretching", "Strongman"
        ])
        self.exercise_type_combo.setStyleSheet("""
            background-color: #E0FFFF;
            font-size: 16px;
            padding: 5px;
            border: 2px solid #0057B7;
            border-radius: 5px;
            color: #0057B7;
        """)
        layout.addWidget(self.exercise_type_combo)

        # Difficulty Label
        difficulty_label = QLabel("Difficulty Level:", self)
        difficulty_label.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: #0057B7;
            background-color: white;
            padding: 5px;
            border-radius: 5px;
        """)
        difficulty_label.setFixedWidth(difficulty_label.sizeHint().width())  # Adjust width to text
        layout.addWidget(difficulty_label)

        # Difficulty ComboBox
        self.difficulty_combo = QComboBox(self)
        self.difficulty_combo.addItems(["", "Beginner", "Intermediate", "Expert"])
        self.difficulty_combo.setStyleSheet("""
            background-color: #E0FFFF;
            font-size: 16px;
            padding: 5px;
            border: 2px solid #0057B7;
            border-radius: 5px;
            color: #0057B7;
        """)
        layout.addWidget(self.difficulty_combo)

        # Duration Label
        duration_label = QLabel("Workout Duration (minutes):", self)
        duration_label.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: #0057B7;
            background-color: white;
            padding: 5px;
            border-radius: 5px;
        """)
        duration_label.setFixedWidth(duration_label.sizeHint().width())  # Adjust width to text
        layout.addWidget(duration_label)

        # Duration Input
        self.workout_duration_input = QLineEdit(self)
        self.workout_duration_input.setPlaceholderText("Workout Duration (minutes, e.g., 45)")
        self.workout_duration_input.setStyleSheet("""
            background-color: #E0FFFF;
            font-size: 16px;
            padding: 5px;
            border: 2px solid #0057B7;
            border-radius: 5px;
            color: #0057B7;
        """)
        layout.addWidget(self.workout_duration_input)

        # Generate Button
        generate_button = QPushButton("Generate Workout Plan", self)
        generate_button.setStyleSheet("""
            QPushButton {
                background-color: #0057B7;
                color: white;
                font-size: 18px;
                padding: 10px 20px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #003C88;
            }
        """)
        generate_button.clicked.connect(self.generate_workout_plan)
        layout.addWidget(generate_button)

        # Output Area
        self.workout_plan_output = QTextEdit(self)
        self.workout_plan_output.setReadOnly(True)
        self.workout_plan_output.setStyleSheet("""
            background-color: #E0FFFF;
            font-size: 16px;
            padding: 10px;
            border: 2px solid #0057B7;
            border-radius: 5px;
            color: #0057B7;
        """)
        layout.addWidget(self.workout_plan_output)

        # Add tab
        self.tabs.addTab(workout_tab, "Workouts")

    def generate_workout_plan(self):
        muscle_group = self.muscle_group_combo.currentText()
        exercise_name = self.exercise_name_input.text().strip()
        exercise_type = self.exercise_type_combo.currentText()
        difficulty = self.difficulty_combo.currentText()

        try:
            total_time = float(self.workout_duration_input.text().strip())
        except ValueError:
            self.workout_plan_output.setPlainText("Please enter a valid number for duration.")
            return

        if not muscle_group and not exercise_name and not exercise_type:
            self.workout_plan_output.setPlainText("Please specify at least one filter.")
            return

        # Fetch exercises using the API
        planner = WorkoutPlanner(api_key="1c55tgO/oZW1c40Dtz+PxQ==hGupNoi6khvXO6Xv")
        exercises = planner.get_exercises(muscle=muscle_group, name=exercise_name, exercise_type=exercise_type)

        if difficulty:
            exercises = planner.filter_exercises(exercises, 'difficulty', difficulty)

        # Format and display the workout plan
        formatted_plan = planner.format_exercise_details(exercises, total_time)
        self.workout_plan_output.setHtml(formatted_plan)

    def create_streak_tab(self):
        """Create the Streak Tab UI with a blue-themed design and functionality."""
        streak_tab = QWidget()
        layout = QVBoxLayout(streak_tab)
        layout.setContentsMargins(20, 20, 20, 20)

        # Title label for Streak Tracker
        title_label = QLabel("Streak Tracker")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("""
            font-size: 30px;
            font-weight: bold;
            color: #0057B7;  /* Dark Blue for the label text */
            background-color: #B0E0E6;  /* Pale Blue for the background */
            padding: 10px;
            border-radius: 5px;
        """)
        layout.addWidget(title_label)

        # Sub-heading label for current streak status
        current_status_label = QLabel("Track your streaks and progress!")
        current_status_label.setAlignment(Qt.AlignCenter)
        current_status_label.setStyleSheet("""
            font-size: 20px;
            color: #0057B7;  /* Dark Blue text */
            background-color: #E0FFFF;  /* Very Light Blue background */
            padding: 10px;  /* Add padding inside the box */
            margin-bottom: 20px;  /* Space below the label */
            border: 2px solid #0057B7;  /* Dark Blue border */
            border-radius: 5px;  /* Rounded corners */
        """)
        layout.addWidget(current_status_label)

        # Display streak statistics
        stats_layout = QHBoxLayout()

        # Current Streak
        self.current_streak_label = QLabel("Current Streak: 0 Days")
        self.current_streak_label.setAlignment(Qt.AlignCenter)
        self.current_streak_label.setStyleSheet("""
            font-size: 18px;
            color: white;
            background-color: #0057B7;  /* Dark Blue */
            padding: 10px;
            border-radius: 5px;
        """)
        stats_layout.addWidget(self.current_streak_label)

        # Longest Streak
        self.longest_streak_label = QLabel("Longest Streak: 0 Days")
        self.longest_streak_label.setAlignment(Qt.AlignCenter)
        self.longest_streak_label.setStyleSheet("""
            font-size: 18px;
            color: white;
            background-color: #003C88;  /* Darker Blue */
            padding: 10px;
            border-radius: 5px;
        """)
        stats_layout.addWidget(self.longest_streak_label)

        layout.addLayout(stats_layout)

        # Streak Progress Bar
        self.streak_progress_bar = QProgressBar()
        self.streak_progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #0057B7;  /* Dark Blue Border */
                border-radius: 5px;
                background: #E0FFFF;       /* Very Light Blue */
                text-align: center;
                font-size: 16px;
                color: #0057B7;            /* Dark Blue Text */
            }
            QProgressBar::chunk {
                background-color: #0057B7; /* Dark Blue for progress chunks */
                width: 20px;
            }
        """)
        self.streak_progress_bar.setMaximum(7)  # Assuming streaks reset after 7 days
        self.streak_progress_bar.setValue(0)
        layout.addWidget(self.streak_progress_bar)

        # Display streak progress in detail
        self.streak_progress_label = QLabel("Your current streak progress: 0/7 days")
        self.streak_progress_label.setAlignment(Qt.AlignCenter)
        self.streak_progress_label.setStyleSheet("""
            font-size: 16px;
            color: #0057B7;  /* Dark Blue */
            margin-top: 10px;
            padding: 20px;  /* Increase padding inside the box */
            border: 3px solid #0057B7;  /* Dark Blue border */
            background-color: #E0FFFF;  /* Very Light Blue background */
            border-radius: 10px;  /* Rounded corners for a smoother look */
        """)
        layout.addWidget(self.streak_progress_label)

        # Add the streak tab to the main tab widget
        self.tabs.addTab(streak_tab, "Streak")

        # Center the layout contents
        layout.setAlignment(Qt.AlignCenter)

        # Set the layout of the container (streak_tab or parent widget)
        streak_tab.setLayout(layout)

        # Ensure the tab switch signal is connected only once
        if not hasattr(self, '_streak_signal_connected'):
            self.tabs.currentChanged.connect(self.update_streak_progress)
            self._streak_signal_connected = True  # Prevent re-connecting the signal

    def update_streak_progress(self):
        """Update the streak progress display in the Streak tab using Supabase."""
        if self.tabs.tabText(self.tabs.currentIndex()) != "Streak":
            return  # Not the streak tab, ignore

        user_id = self.get_current_user_id()
        if not user_id:
            self.streak_progress_label.setText("No user logged in.")
            return

        try:
            # Fetch streak data for the current user
            response = supabase.table('streaks').select('streak_count', 'last_streak_date').eq('user_id',
                                                                                               user_id).execute()

            if response.data:
                streak_data = response.data[0]
                streak_count = streak_data['streak_count']

                self.current_streak_label.setText(f"Current Streak: {streak_count} Days")
                self.streak_progress_bar.setValue(streak_count)
                self.streak_progress_label.setText(f"Your current streak progress: {streak_count}/7 days")
            else:
                self.streak_progress_label.setText("No streak data available.")
        except Exception as e:
            self.streak_progress_label.setText(f"Error fetching streak data: {e}")

    def update_streak(self, user_id):
        """Update the user's streak in Supabase."""
        today = datetime.datetime.today().date().isoformat()

        try:
            # Fetch the current streak data
            response = supabase.table('streaks').select(
                'last_streak_date, streak_count, current_streak, longest_streak'
            ).eq('user_id', user_id).execute()

            if response.data:
                streak_data = response.data[0]
                last_streak_date = streak_data['last_streak_date']
                streak_count = streak_data['streak_count']
                current_streak = streak_data['current_streak']
                longest_streak = streak_data['longest_streak']

                if last_streak_date == today:
                    return  # No update needed
                elif last_streak_date == (datetime.datetime.today() - datetime.timedelta(days=1)).date().isoformat():
                    streak_count += 1
                    current_streak += 1
                else:
                    current_streak = 1  # Reset current streak
                    streak_count += 1

                if current_streak > longest_streak:
                    longest_streak = current_streak

                # Update the streak in Supabase
                supabase.table('streaks').update({
                    'last_streak_date': today,
                    'streak_count': streak_count,
                    'current_streak': current_streak,
                    'longest_streak': longest_streak
                }).eq('user_id', user_id).execute()
            else:
                # Insert a new streak entry for the user
                supabase.table('streaks').insert({
                    'user_id': user_id,
                    'last_streak_date': today,
                    'streak_count': 1,
                    'current_streak': 1,
                    'longest_streak': 1
                }).execute()

        except Exception as e:
            print(f"Error updating streak: {e}")

    def display_streak_data(self, streak_data):
        """Update UI elements with streak data."""
        current_streak = streak_data['current_streak']
        longest_streak = streak_data['longest_streak']
        streak_count = streak_data['streak_count']

        self.current_streak_label.setText(f"Current Streak: {current_streak} Days")
        self.longest_streak_label.setText(f"Longest Streak: {longest_streak} Days")
        self.streak_progress_bar.setValue(current_streak)

    def initialize_user_streak(self, user_id):
        """Initialize a new streak for the user."""
        today = datetime.datetime.today().date().isoformat()
        supabase.table('streaks').insert({
            'user_id': user_id,
            'last_streak_date': today,
            'streak_count': 1,
            'current_streak': 1,
            'longest_streak': 1
        }).execute()
        self.streak_progress_label.setText(
            "Total Streak: 1 day\nCurrent Streak: 1 day\nLongest Streak: 1 day"
        )
        self.streak_progress_bar.setValue(1)

    def get_current_user_id(self):
        user_id = getattr(self, 'current_user_id', None)
        print(f"get_current_user_id() returned: {user_id}")
        return user_id

    from Database import set_bmi_database  # Import the function to update BMI in Supabase

    def create_bmi_visualization_tab(self):
        bmi_tab = QWidget()
        layout = QVBoxLayout(bmi_tab)

        # Title Label for BMI Visualization
        label = QLabel("BMI Visualization", self)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("""
            font-size: 30px;
            font-weight: bold;
            color: #0057B7;  /* Dark Blue for the label text */
            background-color: #B0E0E6;  /* Pale Blue for the background */
            padding: 10px;
            border-radius: 5px;
        """)
        layout.addWidget(label)

        # Weight Input
        self.weight_input = QLineEdit(self)
        self.weight_input.setPlaceholderText("Weight (kg)")
        self.weight_input.setStyleSheet("""
            font-size: 16px;
            padding: 5px;
            color: #0057B7;  /* Dark Blue Text */
            border: 2px solid #0057B7;  /* Dark Blue Border */
            background-color: #E0FFFF;  /* Very Light Blue */
            border-radius: 5px;
            margin-bottom: 10px;
        """)
        layout.addWidget(self.weight_input)

        # Height Input
        self.height_input = QLineEdit(self)
        self.height_input.setPlaceholderText("Height (cm)")
        self.height_input.setStyleSheet("""
            font-size: 16px;
            padding: 5px;
            color: #0057B7;  /* Dark Blue Text */
            border: 2px solid #0057B7;  /* Dark Blue Border */
            background-color: #E0FFFF;  /* Very Light Blue */
            border-radius: 5px;
            margin-bottom: 10px;
        """)
        layout.addWidget(self.height_input)

        # Age Input
        self.age_input = QLineEdit(self)
        self.age_input.setPlaceholderText("Age")
        self.age_input.setStyleSheet("""
            font-size: 16px;
            padding: 5px;
            color: #0057B7;  /* Dark Blue Text */
            border: 2px solid #0057B7;  /* Dark Blue Border */
            background-color: #E0FFFF;  /* Very Light Blue */
            border-radius: 5px;
            margin-bottom: 10px;
        """)
        layout.addWidget(self.age_input)

        # Calculate BMI Button
        calculate_button = QPushButton("Calculate & Save BMI", self)
        calculate_button.setStyleSheet("""
            QPushButton {
                background-color: #0057B7;  /* Dark Blue Background */
                color: white;               /* White Text for Contrast */
                font-size: 18px;            /* Increased font size */
                padding: 10px 20px;         /* Padding for better usability */
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #003C88;  /* Darker Blue on Hover */
            }
        """)
        calculate_button.clicked.connect(self.calculate_and_save_bmi)  # Updated to include Supabase integration
        layout.addWidget(calculate_button)

        # BMI Output
        self.bmi_output = QLineEdit(self)
        self.bmi_output.setReadOnly(True)  # Make it read-only
        self.bmi_output.setPlaceholderText("Your BMI will be displayed here")
        self.bmi_output.setStyleSheet("""
            background-color: #E0FFFF;  /* Very Light Blue */
            font-size: 18px;
            font-weight: bold;
            color: #0057B7;            /* Dark Blue Text */
            padding: 5px;
            border: 2px solid #0057B7; /* Dark Blue Border */
            border-radius: 5px;
            margin-top: 10px;
        """)
        layout.addWidget(self.bmi_output)

        # Canvas for Plotting BMI Visualization
        self.canvas = FigureCanvas(Figure(figsize=(6, 6)))
        layout.addWidget(self.canvas)

        # Add the BMI Tab
        self.tabs.addTab(bmi_tab, "BMI")

    def calculate_and_save_bmi(self):
        try:
            # Get user inputs
            weight = float(self.weight_input.text())
            height_cm = float(self.height_input.text())
            age = int(self.age_input.text())
            user_id = self.current_user_id  # Assuming the user is logged in

            # Convert height to meters and calculate BMI
            height_m = height_cm / 100
            bmi_value = weight / (height_m ** 2)

            # Determine BMI category
            if bmi_value < 18.5:
                bmi_category = "Underweight"
            elif 18.5 <= bmi_value <= 24.9:
                bmi_category = "Normal weight"
            elif 25.0 <= bmi_value <= 29.9:
                bmi_category = "Overweight"
            else:
                bmi_category = "Obesity"

            # Display BMI value and category
            self.bmi_output.setText(f"BMI Value: {bmi_value:.2f}, Category: {bmi_category}")

            # Save BMI to Supabase
            supabase_bmi(user_id, age, height_m, weight, bmi_value)

            # Plot the BMI
            self.plot_bmi(bmi_value, bmi_category)

        except ValueError:
            self.bmi_output.setText("Please enter valid numbers for weight, height, and age.")

    def plot_bmi(self, bmi_value, bmi_category):
        categories = ['Underweight', 'Normal weight', 'Overweight', 'Obesity']
        values = [18.5, 24.9, 29.9, 40]

        # Clear the canvas
        self.canvas.figure.clear()

        # Create the plot
        ax = self.canvas.figure.add_subplot(111)
        bars = ax.bar(categories, values, color=['#42a5f5', '#66bb6a', '#ffa726', '#ef5350'], edgecolor='white',
                      linewidth=2, alpha=0.9, zorder=3)

        # Highlight the user's BMI value
        user_bmi_bar = ax.axhline(bmi_value, color='#0057B7', linestyle='--', linewidth=2)  # Dark Blue for BMI line
        ax.text(3.5, bmi_value, f'Your BMI: {bmi_value:.2f}', color='#0057B7', fontsize=12, ha='right', va='bottom',
                zorder=4)

        # Set background and grid style
        ax.set_facecolor('#E0FFFF')  # Very Light Blue background for the plot
        ax.grid(color='white', linestyle='--', linewidth=0.7, zorder=0)

        # Add labels and title with modern fonts
        ax.set_title("BMI Categories", fontsize=20, fontweight='bold', color='#0057B7')  # Dark Blue title
        ax.set_xlabel("Categories", fontsize=16, color='#0057B7')
        ax.set_ylabel("BMI Values", fontsize=16, color='#0057B7')
        ax.tick_params(axis='x', labelsize=12, colors='#0057B7')
        ax.tick_params(axis='y', labelsize=12, colors='#0057B7')

        # Add interactive tooltips
        cursor = mplcursors.cursor(bars, hover=True)
        cursor.connect("add", lambda sel: sel.annotation.set_text(
            f'BMI Category: {categories[sel.index]}\nBMI Value: {values[sel.index]}'))
        cursor.connect("add", lambda sel: sel.annotation.set_bbox(
            {"boxstyle": "round,pad=0.5", "fc": "#E1BEE7", "ec": "#0057B7"}))  # Light Blue background for tooltips

        # Update canvas
        self.canvas.draw()

    def create_meal_planner_tab(self):
        meal_tab = QWidget()
        layout = QVBoxLayout(meal_tab)

        label = QLabel("Meal Planner", self)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("""
            font-size: 30px;
            font-weight: bold;
            color: #0057B7;  /* Dark Blue for the label text */
            background-color: #B0E0E6;  /* Pale Blue for the background */
            padding: 10px;
            border-radius: 5px;
        """)
        layout.addWidget(label)

        # Target Calories Input
        self.calories_input = QLineEdit(self)
        self.calories_input.setPlaceholderText("Enter Target Calories")
        self.set_text_field_style(self.calories_input)
        self.calories_input.setStyleSheet(self.calories_input.styleSheet() + "margin-bottom: 15px;")
        layout.addWidget(self.calories_input)

        # Generate Meal Plan Button
        generate_meal_button = QPushButton("Generate Meal Plan", self)
        self.set_button_style(generate_meal_button)
        generate_meal_button.clicked.connect(self.generate_meal_plan)
        layout.addWidget(generate_meal_button)

        # Meal Plan Output
        self.meal_plan_output = QTextEdit(self)
        self.meal_plan_output.setReadOnly(True)
        self.meal_plan_output.setStyleSheet("""
            background-color: #E0FFFF;  /* Very Light Blue */
            border: 2px solid #0057B7;  /* Dark Blue Border */
            font-size: 14px;
            line-height: 1.5;
            color: #0057B7;  /* Dark Blue Text */
            padding: 10px;
        """)
        layout.addWidget(self.meal_plan_output)

        self.tabs.addTab(meal_tab, "Meal Planner")

    def generate_meal_plan(self):
        try:
            target_calories = int(self.calories_input.text())
            meal_plan = self.meal_planner.get_meal_plan(target_calories)

            if meal_plan and "meals" in meal_plan:
                meals = ""
                for meal in meal_plan["meals"]:
                    meals += f"<b>- {meal['title']}</b><br>"
                    meals += f"  Ready in: {meal['readyInMinutes']} minutes<br>"
                    meals += f"  Servings: {meal['servings']}<br>"
                    meals += f"  Recipe Link: {meal['sourceUrl']}<br><br>"  # Display URL directly

                self.meal_plan_output.setHtml(f"<h3>Recommended Meals:</h3>{meals}")
            else:
                self.meal_plan_output.setPlainText("Failed to generate meal plan.")
        except ValueError:
            self.meal_plan_output.setPlainText("Please enter a valid number for target calories.")
        except Exception as e:
            self.meal_plan_output.setPlainText(f"An error occurred: {e}")

    def activate_voice_assistant(self):
        """Activate the voice assistant with enhanced visual and audio feedback."""
        self.voice_assistant_active = True
        self.dynamic_button.setText("Stop Recording")  # Change button label
        self.assistant_status_label.setText("🎤 Listening...")
        self.assistant_status_label.setStyleSheet(
            "font-size: 20px; color: #0057B7; font-weight: bold;")  # Dark Blue color

        # Start animated visual feedback
        self.start_recording_visual_feedback()

        # Play a sound to indicate recording start
        threading.Thread(target=lambda: self.play_sound("start_sound.mp3"), daemon=True).start()

        def listen():
            try:
                while self.voice_assistant_active:
                    with self.microphone as source:
                        # Adjust for ambient noise and start listening
                        self.recognizer.adjust_for_ambient_noise(source)
                        audio = self.recognizer.listen(source, timeout=1, phrase_time_limit=2)

                    # Stop recording if the user presses "Stop"
                    if not self.voice_assistant_active:
                        break

                    # Play a sound to indicate recording stop
                    threading.Thread(target=lambda: self.play_sound("stop_sound.mp3"), daemon=True).start()

                    # Stop visual feedback
                    self.stop_recording_visual_feedback()

                    # Process the audio input
                    try:
                        command = self.recognizer.recognize_google(audio)
                        self.chat_output.append(
                            f"<b>You (Voice)</b> ({datetime.datetime.now().strftime('%H:%M')}): {command}")
                        self.process_voice_command(command)
                    except sr.UnknownValueError:
                        self.chat_output.append("<b>Assistant</b>: Sorry, I couldn't understand that.")
                    except sr.RequestError as e:
                        self.chat_output.append(f"<b>Assistant</b>: Error with voice recognition service: {e}")
            except sr.WaitTimeoutError:
                self.chat_output.append("<b>Assistant</b>: No input detected. Please try again.")
                self.stop_recording_visual_feedback()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Voice Assistant Error: {str(e)}")
                self.stop_recording_visual_feedback()
            finally:
                self.deactivate_voice_assistant()  # Ensure cleanup

        threading.Thread(target=listen, daemon=True).start()

    def start_recording_visual_feedback(self):
        """Start the visual feedback for recording."""
        self.mic_animation = QMovie("mic_listening.gif")  # Animated microphone icon
        self.mic_label.setMovie(self.mic_animation)
        self.mic_animation.start()

        self.recording_timer_start = time.time()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_recording_timer)
        self.timer.start(1000)

    def stop_recording_visual_feedback(self):
        """Stop the visual feedback for recording."""
        self.assistant_status_label.setText("🔴 Recording Stopped.")
        self.assistant_status_label.setStyleSheet("font-size: 20px; color: gray;")  # Light gray color after stop
        if hasattr(self, "mic_animation") and self.mic_animation:
            self.mic_animation.stop()
            self.mic_label.clear()
        if hasattr(self, "timer") and self.timer:
            self.timer.stop()

    def update_recording_timer(self):
        """Update the timer for how long the recording has been active."""
        elapsed_time = int(time.time() - self.recording_timer_start)
        minutes, seconds = divmod(elapsed_time, 60)
        self.assistant_status_label.setText(f"🎤 Listening... {minutes}:{seconds:02}")

    def play_sound(self, file_path):
        """Play a sound file."""
        try:
            playsound.playsound(file_path)
        except Exception as e:
            print(f"Error playing sound: {e}")

    def process_voice_command(self, command: str):
        """Process commands received from voice input with intent detection."""
        command = command.lower()
        if "login" in command:
            self.switch_to_login()
        elif "sign up" in command or "register" in command:
            self.switch_to_signup()
        elif "meal plan" in command:
            self.central_widget.setCurrentIndex(3)  # Navigate to meal planner
        elif "calculate bmi" in command or "bmi" in command:
            self.central_widget.setCurrentIndex(4)  # Navigate to BMI calculator
        elif "exit" in command or "logout" in command:
            self.logout()
        else:
            self.chat_output.append("<b>Assistant</b>: Let me think about that...")
            response = self.fitness_ai_assistant.send_query(command)
            formatted_response = self.format_response(response)
            self.chat_output.append(f"<b>Assistant</b>: {formatted_response}")

    def deactivate_voice_assistant(self):
        """Deactivate the voice assistant and reset UI state."""
        self.voice_assistant_active = False
        self.assistant_status_label.setText("🔴 Status: Inactive")
        self.assistant_status_label.setStyleSheet("font-size: 20px; color: gray;")
        self.dynamic_button.setText("Record")  # Reset button label
        self.stop_recording_visual_feedback()
        self.chat_output.append("<b>Assistant</b>: Voice assistant deactivated.")

    def toggle_button_mode(self):
        """Toggle the dynamic button mode based on chat input or recording state."""
        if self.dynamic_button.text() == "Deactivate":
            return  # If actively recording, the button stays as "Deactivate"
        elif self.chat_input.text().strip():  # If chat input is not empty
            self.dynamic_button.setText("Send")
            self.dynamic_button.setStyleSheet(
                "background-color: #0057B7; color: white;")  # Blue background for 'Send' state
        else:  # If the chat input is empty
            self.dynamic_button.setText("Record")
            self.dynamic_button.setStyleSheet(
                "background-color: #42a5f5; color: white;")  # Light blue background for 'Record'

    def handle_dynamic_button_action(self):
        """Handle actions for the dynamic button based on its current state."""
        current_text = self.dynamic_button.text()
        if current_text == "Send":
            self.send_chat_message()
        elif current_text == "Record":
            self.activate_voice_assistant()
        elif current_text == "Stop Recording":
            self.deactivate_voice_assistant()

    def create_interactive_assistant_tab(self):
        """Create the interactive assistant tab with enhanced chat and voice features."""
        assistant_tab = QWidget()
        layout = QVBoxLayout(assistant_tab)

        # Tab title
        label = QLabel("AI Assistant", self)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("""
            font-size: 30px;
            font-weight: bold;
            color: #0057B7;  /* Dark Blue for the label text */
            background-color: #B0E0E6;  /* Pale Blue for the background */
            padding: 10px;
            border-radius: 5px;
        """)
        layout.addWidget(label)

        # Chat output area
        self.chat_output = QTextEdit(self)
        self.chat_output.setStyleSheet("""
            QTextEdit {
                background-color: #E0FFFF;  /* Very Light Blue */
                border: 2px solid #0057B7;  /* Dark Blue Border */
                border-radius: 5px;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 14px;
                color: #0057B7;  /* Dark Blue Text */
                padding: 8px;
                line-height: 1.5;
            }
        """)
        self.chat_output.setReadOnly(True)
        layout.addWidget(self.chat_output)

        # Input area and dynamic button
        input_layout = QHBoxLayout()

        self.chat_input = QLineEdit(self)
        self.chat_input.setPlaceholderText("Type your message here or press record...")
        self.set_text_field_style(self.chat_input)
        self.chat_input.textChanged.connect(self.toggle_button_mode)
        input_layout.addWidget(self.chat_input)

        # Microphone icon or animation (You can add here)
        self.mic_label = QLabel(self)
        self.mic_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.mic_label)

        # Dynamic button
        self.dynamic_button = QPushButton("Record", self)
        self.set_button_style(self.dynamic_button)
        self.dynamic_button.clicked.connect(self.handle_dynamic_button_action)
        input_layout.addWidget(self.dynamic_button)

        layout.addLayout(input_layout)

        # Status label for assistant state
        self.assistant_status_label = QLabel("Status: Inactive", self)
        self.assistant_status_label.setAlignment(Qt.AlignCenter)
        self.assistant_status_label.setStyleSheet("""
            font-size: 20px;
            color: #0057B7;  /* Dark Blue for status text */
        """)
        layout.addWidget(self.assistant_status_label)

        # Add the tab to the QTabWidget
        self.tabs.addTab(assistant_tab, "AI Assistant")

    def send_chat_message(self):
        """Handle user input and communicate with Gemini AI."""
        message = self.chat_input.text().strip()
        if message:
            self.chat_output.append(f"<b>You</b> ({datetime.datetime.now().strftime('%H:%M')}): {message}")
            self.chat_input.clear()

            self.chat_output.append("<b>Assistant</b> is typing...")
            self.chat_output.repaint()

            def process_message():
                try:
                    response = self.fitness_ai_assistant.send_query(message)
                    formatted_response = self.format_response(response)
                    self.chat_output.append(
                        f"<b>Assistant</b> ({datetime.datetime.now().strftime('%H:%M')}): {formatted_response}")
                except Exception as e:
                    self.chat_output.append(f"<b>Assistant</b>: Sorry, I encountered an error: {e}")
                finally:
                    self.chat_output.append("")  # Remove the typing indicator

            threading.Thread(target=process_message, daemon=True).start()
        else:
            self.chat_output.append("<b>Assistant</b>: Please enter a message or use the voice assistant.")

    def format_response(self, response: str) -> str:
        """Format the assistant's response to ensure consistency and readability."""
        return response.strip().replace("*", "").replace("\n", " ")

    def create_help_tab(self):
        help_tab = QWidget()
        layout = QVBoxLayout(help_tab)

        # Title Label
        label = QLabel("Help & FAQs", self)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("""
            font-size: 30px;
            font-weight: bold;
            color: #0057B7;  /* Dark Blue for the label text */
            background-color: #B0E0E6;  /* Pale Blue for the background */
            padding: 10px;
            border-radius: 5px;
        """)
        layout.addWidget(label)

        # FAQ Section Header
        faq_header = QLabel("Frequently Asked Questions", self)
        faq_header.setAlignment(Qt.AlignCenter)
        faq_header.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            color: #0057B7;  /* Dark Blue for FAQ header */
            margin-bottom: 20px;
        """)
        layout.addWidget(faq_header)

        # FAQs with collapsible sections
        faqs = [
            ("How do I reset my password?", "Click on 'Forgot Password?' on the login screen."),
            ("How can I contact support?", "Please use the contact form on our website."),
            ("What features does this app offer?",
             "The app provides posture tracking, meal planning, fitness tracking, and workout planning."),
            ("Is my data secure?", "Yes, we use encryption to protect your data."),
            ("Can I sync my progress with other devices?", "Yes, you can sync your data across multiple devices.")
        ]

        for question, answer in faqs:
            question_label = QPushButton(question, self)
            self.set_button_style(question_label)
            question_label.setStyleSheet("""
                background-color: #0057B7;  /* Dark Blue for question button */
                color: white;               /* White text for contrast */
                font-size: 16px;
                padding: 10px;
                border-radius: 5px;
            """)

            answer_label = QLabel(answer, self)
            answer_label.setWordWrap(True)
            answer_label.setStyleSheet("""
                font-size: 16px;
                color: #0057B7;             /* Dark Blue for the answer text */
                padding: 10px;
                background-color: #E0FFFF; /* Very Light Blue */
                border: 1px solid #0057B7; /* Dark Blue Border */
                border-radius: 5px;
                margin-left: 20px;  /* Indent the answer */
            """)
            answer_label.setVisible(False)

            # Toggle answer visibility on question click
            def toggle_answer(checked, answer_label=answer_label):
                answer_label.setVisible(not answer_label.isVisible())
                if answer_label.isVisible():
                    answer_label.setStyleSheet("""
                        font-size: 16px;
                        color: #0057B7;  /* Dark Blue text for visible answers */
                        padding: 10px;
                        background-color: #D0EFFF;  /* Slightly darker blue when visible */
                        border: 1px solid #0057B7; 
                        border-radius: 5px;
                        margin-left: 20px; 
                    """)
                else:
                    answer_label.setStyleSheet("""
                        font-size: 16px;
                        color: #0057B7;  /* Dark Blue text for collapsed answers */
                        padding: 10px;
                        background-color: #E0FFFF;
                        border: 1px solid #0057B7; /* Dark Blue Border */
                        border-radius: 5px;
                        margin-left: 20px; 
                    """)

            question_label.clicked.connect(toggle_answer)
            layout.addWidget(question_label)
            layout.addWidget(answer_label)

        # Add a feedback section at the bottom
        feedback_label = QLabel("Still have questions? Reach out to our support team!", self)
        feedback_label.setAlignment(Qt.AlignCenter)
        feedback_label.setStyleSheet("""
            font-size: 18px;
            color: #0057B7;  /* Dark Blue for feedback text */
            margin-top: 30px;
        """)
        layout.addWidget(feedback_label)

        # Contact Support Button
        contact_button = QPushButton("Contact Support", self)
        self.set_button_style(contact_button)
        contact_button.setStyleSheet("""
            background-color: #0057B7;  /* Dark Blue for button background */
            color: white;               /* White text for contrast */
            font-size: 18px;
            padding: 12px;
            border-radius: 5px;
        """)
        contact_button.clicked.connect(
            self.open_contact_form)  # Connect to a method that opens a contact form or support page
        layout.addWidget(contact_button)

        # Add the tab to the QTabWidget
        self.tabs.addTab(help_tab, "Help")

    def open_contact_form(self):
        """Open the contact form for user inquiries."""
        # Create and display a contact form dialog
        contact_dialog = QDialog(self)
        contact_dialog.setWindowTitle("Contact Support")
        contact_dialog.setFixedSize(400, 400)

        layout = QVBoxLayout(contact_dialog)

        # Title label
        label = QLabel("Contact Support", contact_dialog)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("""
            font-size: 20px;
            font-weight: bold;
            color: #0057B7;  /* Dark Blue for the label text */
            margin-bottom: 10px;
        """)
        layout.addWidget(label)

        # Name input field
        name_input = QLineEdit(contact_dialog)
        name_input.setPlaceholderText("Name")
        name_input.setStyleSheet("""
            font-size: 16px;
            padding: 8px;
            border: 1px solid #0057B7;  /* Dark Blue border */
            border-radius: 5px;
            margin-bottom: 10px;
            background-color: #E0FFFF;  /* Very Light Blue background */
        """)
        layout.addWidget(name_input)

        # Email input field
        email_input = QLineEdit(contact_dialog)
        email_input.setPlaceholderText("Email")
        email_input.setStyleSheet("""
            font-size: 16px;
            padding: 8px;
            border: 1px solid #0057B7;  /* Dark Blue border */
            border-radius: 5px;
            margin-bottom: 10px;
            background-color: #E0FFFF;  /* Very Light Blue background */
        """)
        layout.addWidget(email_input)

        # Message input field
        message_input = QTextEdit(contact_dialog)
        message_input.setPlaceholderText("Message")
        message_input.setStyleSheet("""
            font-size: 16px;
            padding: 8px;
            border: 1px solid #0057B7;  /* Dark Blue border */
            border-radius: 5px;
            margin-bottom: 10px;
            background-color: #E0FFFF;  /* Very Light Blue background */
        """)
        layout.addWidget(message_input)

        # Submit button
        submit_button = QPushButton("Submit", contact_dialog)
        self.set_button_style(submit_button)
        submit_button.setStyleSheet("""
            background-color: #0057B7;  /* Dark Blue background */
            color: white;               /* White text for contrast */
            font-size: 16px;
            padding: 12px;
            border-radius: 5px;
        """)
        layout.addWidget(submit_button)

        # Success label for feedback
        success_label = QLabel("", contact_dialog)
        success_label.setAlignment(Qt.AlignCenter)
        success_label.setStyleSheet("""
            font-size: 16px;
            color: #42a5f5;  /* Light Blue color for success message */
            margin-top: 10px;
            font-weight: bold;
        """)
        layout.addWidget(success_label)

        def submit_contact_form():
            """Handle the submission of the contact form."""
            name = name_input.text()
            email = email_input.text()
            message = message_input.toPlainText()

            if not name or not email or not message:
                success_label.setText("Please fill in all fields.")
                success_label.setStyleSheet("""
                    font-size: 16px;
                    color: red;  /* Red color for error message */
                    margin-top: 10px;
                    font-weight: bold;
                """)
                return

            # Confirmation message after submission
            success_label.setText("Message sent! We'll get back to you shortly.")
            success_label.setStyleSheet("""
                font-size: 16px;
                color: #42a5f5;  /* Light Blue for success message */
                margin-top: 10px;
                font-weight: bold;
            """)

            # Clear input fields after submission
            name_input.clear()
            email_input.clear()
            message_input.clear()

        submit_button.clicked.connect(submit_contact_form)

        # Execute the dialog
        contact_dialog.exec_()

    def show_message(self, message):
        """Display a message in a dialog."""
        msg_box = QMessageBox()
        msg_box.setText(message)
        msg_box.exec_()



    def set_background_image(self, image_path=None):
        """Set a gradient or image background."""
        if image_path:
            pixmap = QPixmap(image_path)
            if pixmap.isNull():
                print("Failed to load background image.")
                return
            palette = QPalette()
            palette.setBrush(QPalette.Window, QBrush(pixmap))
            self.setPalette(palette)
        else:
            self.setStyleSheet("""
                QWidget {
                    background: linear-gradient(to bottom, #3C3B3F, #605C3C);
                }
            """)

    def logout(self):
        """Handle the logout process."""
        self.current_user_id = None  # Clear the current user ID
        self.login_feedback.setText("You have been logged out.")  # Optional feedback
        self.central_widget.setCurrentIndex(0)  # Go back to the main UI (login/signup)
        self.add_to_history(0)  # Add main UI to history

if __name__ == "__main__":

    api_key = "e5968cb05a3b42a4845c016350e83f17"
    gemini_api_key = "AIzaSyA1RJISbzG7WJ0T_ZRQIEVj_WWkhiHKml4"

    app = QApplication(sys.argv)
    window = LoginSignupApp(api_key, gemini_api_key)
    window.show()
    sys.exit(app.exec_())