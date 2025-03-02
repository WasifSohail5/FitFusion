from datetime import datetime

from supabase import create_client

# Supabase project URL and secret key
supabase_url = "https://bbxmstrrxwmmuyuzygmr.supabase.co"
supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJieG1zdHJyeHdtbXV5dXp5Z21yIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzI1MjQzNzAsImV4cCI6MjA0ODEwMDM3MH0.0qamevJin8cv6YtbTgQZOLBg8sZJQYwX1G6sAr6LwhY"

# Create a Supabase client instance
supabase = create_client(supabase_url, supabase_key)


# Login function with authentication
def login_database(users_email, users_password):
    """
    Attempts to log a user in using email and password.

    Args:
        users_email (str): The user's email address.
        users_password (str): The user's password.

    Returns:
        str | None: The user's ID on success, or an error message on failure.
    """

    try:
        # Try to authenticate user from database.
        response = supabase.auth.sign_in_with_password({
            "email": users_email,
            "password": users_password
        })

        # If Authentication successful
        if response.user:
            user_id = response.user.id

            # returning user's unique ID (i.e. Primary key of User's Table)
            return user_id
    except Exception as e:
        # If authentication fail from database
        return "Login failed. Error:", e


# Signup function with authentication
def signup_database(users_email, users_password, users_name):
    """
    Attempts to sign up a new user.

    Args:
        users_email (str): The user's email address.
        users_password (str): The user's password.
        users_name (str): The user's name.

    Returns:
        str: A message indicating success or failure.
    """

    # Try to authenticate user by sending verification mail
    try:
        # Sign-up Authentication
        response = supabase.auth.sign_up({
            "email": users_email,
            "password": users_password
        })

        # user's unique ID (i.e. Primary key of User's Table)
        user_id = response.user.id

        # Storing new user's info into database
        if response.user:

            # Storing user's detail into "user's" table
            supabase.table('users').insert({
                "id": user_id,
                "email": users_email,
                "password_hash": users_password,
                "name": users_name
            }).execute()

            # Setting the default streak as 0 when signup successful
            supabase.table('streaks').insert({
                'user_id': user_id,
                'streak_count': 0
            }).execute()

            # Setting the default bmi data as 0 when signup successful
            supabase.table('bmi_data').insert({
                "user_id": user_id,
                "bmi": 0.0,
                "new_bmi": 0.0,
                "age": 0,
                "weight": 0.0,
                "height": 0.0
            }).execute()

            # returning the confirmation message
            return "Signup successful, Please verify your email."
        else:

            # After authentication if unable to get user's ID
            return f"Signup failed...!!\nError: {response.get('error', 'Unknown error')}"

    except Exception as e:
        # If authentication failed
        return "Signup failed:", e


# function to set bmi
def set_bmi_database(user_id, age, height, weight, new_bmi):
    """
    Updates the user's BMI data in the database.

    Args:
        user_id (int): The user's ID.
        age (int): The user's age.
        height (float): The user's height in meters.
        weight (float): The user's weight in kilograms.
        new_bmi (float): The user's calculated new BMI.
    """

    # Retrieving the old bmi from database
    response = supabase.table('bmi_data').select('new_bmi').eq('user_id', user_id).execute()

    # Getting old bmi
    old_bmi = response.data[0]['new_bmi']

    # Update the bmi table by storing new bmi
    supabase.table('bmi_data').update({
        'bmi': old_bmi,
        'new_bmi': new_bmi,
        "age": age,
        "weight": weight,
        "height": height
    }).eq('user_id', user_id).execute()


def streak_count_database(user_id):
        """
        Updates the user's streak count in the database.

        Args:
            user_id (int): The user's ID.
        """
        today = datetime.date.today().isoformat()

        # Retrieve current streak data
        response = supabase.table('streaks').select('streak_count', 'last_streak_date').eq('user_id', user_id).execute()

        if not response.data:
            # If no data exists, initialize the streak
            supabase.table('streaks').insert({
                'user_id': user_id,
                'streak_count': 1,
                'last_streak_date': today
            }).execute()
            return

        streak_data = response.data[0]
        last_streak_date = streak_data['last_streak_date']
        streak_count = streak_data['streak_count']

        if last_streak_date == today:
            # No update if the streak has already been counted for today
            return

        elif last_streak_date == (datetime.date.today() - datetime.timedelta(days=1)).isoformat():
            # Continue the streak
            streak_count += 1
        else:
            # Reset to a new streak
            streak_count = 1

        # Update the database
        supabase.table('streaks').update({
            'streak_count': streak_count,
            'last_streak_date': today
        }).eq('user_id', user_id).execute()


def reset_streak(user_id):
        """
        Resets a user's streak count to 0.

        Args:
            user_id (int): The ID of the user whose streak to reset.
        """
        supabase.table('streaks').update({
            'streak_count': 0
        }).eq('user_id', user_id).execute()


# Example Testing
print("Welcome to Fit Fusion")
print("1. Login \n2. Signup")
choice = input("Press 1 for Login and 2 for Signup: ")

if choice == '1':
    email = input("Enter your Email: ")
    password = input("Enter your password: ")
    print(login_database(email, password))

elif choice == '2':
    email = input("Enter your Email: ")
    password = input("Enter your password: ")
    name = input("Enter your name: ")
    print(signup_database(email, password, name))

else:
    print("Invalid choice.")
