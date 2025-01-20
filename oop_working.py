import streamlit as st
from PIL import Image
import sqlite3
import pandas as pd
import io
import sys
import uuid  # For generating unique session IDs
from chatgpt_integration import *

# DatabaseHandler class
class DatabaseHandler:
    def __init__(self, db_name="app.db"):
        self.db_name = db_name
        self.init_db()

    def init_db(self):
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users
                     (username TEXT PRIMARY KEY, password TEXT, score INTEGER)''')
        c.execute('''CREATE TABLE IF NOT EXISTS completed_exercises
                     (username TEXT, exercise TEXT, PRIMARY KEY(username, exercise))''')
        c.execute('''CREATE TABLE IF NOT EXISTS sessions
                     (session_id TEXT PRIMARY KEY, username TEXT)''')
        conn.commit()
        conn.close()

    def execute_query(self, query, params=(), fetch_one=False, fetch_all=False):
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        c.execute(query, params)
        result = None
        if fetch_one:
            result = c.fetchone()
        elif fetch_all:
            result = c.fetchall()
        conn.commit()
        conn.close()
        return result

# Exercise class
class Exercise:
    def __init__(self, name, instructions, answer):
        self.name = name
        self.instructions = instructions
        self.answer = answer

    def is_correct(self, output):
        return self.answer in output.strip()

# UserManager class
class UserManager:
    def __init__(self, db_handler):
        self.db_handler = db_handler

    def get_user(self, username):
        return self.db_handler.execute_query("SELECT * FROM users WHERE username = ?", (username,), fetch_one=True)

    def update_score(self, username, score):
        self.db_handler.execute_query("UPDATE users SET score = ? WHERE username = ?", (score, username))

    def mark_exercise_completed(self, username, exercise):
        self.db_handler.execute_query("INSERT OR IGNORE INTO completed_exercises (username, exercise) VALUES (?, ?)", (username, exercise))

    def is_exercise_completed(self, username, exercise):
        result = self.db_handler.execute_query("SELECT * FROM completed_exercises WHERE username = ? AND exercise = ?", (username, exercise), fetch_one=True)
        return result is not None

# SessionManager class
class SessionManager:
    def __init__(self, db_handler):
        self.db_handler = db_handler

    def create_session(self, username):
        session_id = str(uuid.uuid4())
        self.db_handler.execute_query("INSERT INTO sessions (session_id, username) VALUES (?, ?)", (session_id, username))
        return session_id

    def invalidate_session(self, session_id):
        self.db_handler.execute_query("DELETE FROM sessions WHERE session_id = ?", (session_id,))

    def get_username_for_session(self, session_id):
        result = self.db_handler.execute_query("SELECT username FROM sessions WHERE session_id = ?", (session_id,), fetch_one=True)
        return result[0] if result else None

# StreamlitApp class
class StreamlitApp:
    def __init__(self):
        self.db_handler = DatabaseHandler()
        self.user_manager = UserManager(self.db_handler)
        self.session_manager = SessionManager(self.db_handler)
        self.exercises = {
            "hello-world-exercise": Exercise("Python", "Write your code below to print 'Hello World'.", "Hello World"),
            "one-sided-anova": Exercise("Data Structure", "Given a sorted array of integers arr and an integer target, find the index of the first and last position of target in arr. If target can't be found in arr, return [-1,-1]. Example: arr = [2,4,5,5,5,5,5,7,9,9], target = 5. The output should be printed list of 2 elements.", "[2,6]"),
            "two-sided-anova": Exercise("Data Science", "Provide a code snippet to perform a two-sided ANOVA test.", "anova_two"),
        }
        self.init_session_state()

    def init_session_state(self):
        if 'user' not in st.session_state:
            st.session_state.user = None
        if 'score' not in st.session_state:
            st.session_state.score = 0
        if 'page' not in st.session_state:
            st.session_state.page = 'login'
        if 'badge' not in st.session_state:
            st.session_state.badge = 'Iron'
        if 'session_id' not in st.session_state:
            st.session_state.session_id = None

    def get_badge(self, score):
        if score >= 50:
            return "Gold"
        elif score >= 30:
            return "Silver"
        elif score >= 10:
            return "Bronze"
        else:
            return "Iron"

    def run(self):
        if st.session_state.page == 'login':
            self.login_page()
        elif st.session_state.page == 'register':
            self.registration_page()
        elif st.session_state.page == 'chatbot':
            self.chatbot_page()
        elif st.session_state.page in self.exercises:
            self.exercise_page()
        else:
            self.main_page()

    def login_page(self):
        st.title('Data Craft')
        st.title("Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type='password')

        if st.button("Login"):
            user = self.user_manager.get_user(username)
            if user and user[1] == password:
                if st.session_state.session_id:
                    self.session_manager.invalidate_session(st.session_state.session_id)

                st.session_state.user = username
                st.session_state.score = user[2]
                st.session_state.badge = self.get_badge(st.session_state.score)
                st.session_state.page = 'main'
                st.session_state.session_id = self.session_manager.create_session(username)
                st.experimental_rerun()
            else:
                st.error("Invalid username or password")

        if st.button("Register"):
            st.session_state.page = 'register'
            st.experimental_rerun()

    def registration_page(self):
        st.title("Register")
        username = st.text_input("Username", key="reg_username")
        password = st.text_input("Password", type='password', key="reg_password")

        if st.button("Register"):
            self.db_handler.execute_query("INSERT OR IGNORE INTO users (username, password, score) VALUES (?, ?, 0)", (username, password))
            st.session_state.page = 'login'
            st.experimental_rerun()

        if st.button("Back to Login"):
            st.session_state.page = 'login'
            st.experimental_rerun()

    def main_page(self):
        st.image(r"WhatsApp Image 2024-12-13 at 20.47.24_3f75e257.jpg", width = 300)
        st.title("DataCraft")
        st.write('### Learn data and AI skill')
        st.write('Unlock the power of data and AI by learning Python, ChatGPT, SQL, Power BI, and earn Certifications.')

        st.sidebar.title("User Info")
        if st.session_state.user:
            st.sidebar.image(r"93d3e31639a4d07613de9dccdc8bd5e8.jpg", width=100)
            st.sidebar.write(f"**Username:** {st.session_state.user}")
            st.sidebar.write(f"**Score:** {st.session_state.score}")
            st.sidebar.write(f"**Badge:** {st.session_state.badge}")

            if st.sidebar.button("Logout"):
                self.logout()
        else:
            st.sidebar.write("No user logged in.")

        st.write(f"### Welcome, {st.session_state.user}")
        st.write("Your Score: ", st.session_state.score)
        st.write("Your Badge: ", st.session_state.badge)
        st.write('### Available Tracks')

        for exercise_name, exercise in self.exercises.items():
            button_label = f"Practice {exercise.name}"
            if self.user_manager.is_exercise_completed(st.session_state.user, exercise_name):
                button_label = f"✅ {button_label}"

            if st.button(button_label):
                st.session_state.page = exercise_name
                st.experimental_rerun()
    
        if st.button("Ask Ai 🤖",help="Click the robot button!"):
            st.session_state.page = "chatbot"
            st.experimental_rerun()
  
        
    


    def exercise_page(self):
        exercise_name = st.session_state.page
        exercise = self.exercises.get(exercise_name)

        if not exercise:
            st.error("Exercise not found.")
            return

        st.title(exercise.name)
        st.write("### Instructions")
        st.write(exercise.instructions)

        code_key = f"{exercise_name}_code"
        code = st.text_area("Python Code", height=300, key=code_key)

        if st.button("Submit"):
            output = self.run_code(code)
            st.write("### Output:")
            st.code(output)

            if exercise.is_correct(output):
                st.success("✅ Your answer is correct.")
                if not self.user_manager.is_exercise_completed(st.session_state.user, exercise_name):
                    st.session_state.score += 10
                    st.session_state.badge = self.get_badge(st.session_state.score)
                    self.user_manager.update_score(st.session_state.user, st.session_state.score)
                    self.user_manager.mark_exercise_completed(st.session_state.user, exercise_name)
            else:
                st.error("❌ Your answer is incorrect.")

        if st.button("Back to Main Page"):
            st.session_state.page = 'main'
            st.experimental_rerun()

    def chatbot_page(self):
        st.title("Ask Zelda🤖")
        user_query = st.text_input("Ask a question:")

        if st.button("Send"):
            if user_query.strip():
                response = ask_huggingface(user_query)
                st.write("### Response:")
                st.write("Hi, I'm your Zelda AI! I'm here to help you practice and improve your coding skills. Let's tackle challenges together!")
                
            # Use an expander for the detailed response
            with st.expander("See detailed response"):
                st.write(response)

        if st.button("Back to Main Page"):
            st.session_state.page = 'main'
            st.experimental_rerun()

    def run_code(self, code):
        buffer = io.StringIO()
        sys.stdout = buffer
        try:
            exec(code)
        except Exception as e:
            return str(e)
        return buffer.getvalue()

    def logout(self):
        if st.session_state.session_id:
            self.session_manager.invalidate_session(st.session_state.session_id)
        st.session_state.user = None
        st.session_state.score = 0
        st.session_state.badge = 'Iron'
        st.session_state.page = 'login'
        st.session_state.session_id = None
        st.experimental_rerun()

# Run the app
if __name__ == '__main__':
    app = StreamlitApp()
    app.run()
