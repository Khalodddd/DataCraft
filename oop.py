import streamlit as st
import sqlite3
import pandas as pd
import io
import sys
import uuid
from chatgpt_integration import ask_huggingface

# Database manager class
class DatabaseManager:
    def __init__(self, db_name):
        self.db_name = db_name
        self.init_db()

    def init_db(self):
        with sqlite3.connect(self.db_name) as conn:
            c = conn.cursor()
            c.execute('''CREATE TABLE IF NOT EXISTS users
                         (username TEXT PRIMARY KEY, password TEXT, score INTEGER)''')
            c.execute('''CREATE TABLE IF NOT EXISTS completed_exercises
                         (username TEXT, exercise TEXT, PRIMARY KEY(username, exercise))''')
            c.execute('''CREATE TABLE IF NOT EXISTS sessions
                         (session_id TEXT PRIMARY KEY, username TEXT)''')

    def execute_query(self, query, params=(), fetchone=False):
        with sqlite3.connect(self.db_name) as conn:
            c = conn.cursor()
            c.execute(query, params)
            conn.commit()
            return c.fetchone() if fetchone else c.fetchall()

    def get_user(self, username):
        return self.execute_query("SELECT * FROM users WHERE username = ?", (username,), fetchone=True)

    def update_score(self, username, score):
        self.execute_query("UPDATE users SET score = ? WHERE username = ?", (score, username))

    def mark_exercise_completed(self, username, exercise):
        self.execute_query("INSERT OR IGNORE INTO completed_exercises (username, exercise) VALUES (?, ?)", (username, exercise))

    def is_exercise_completed(self, username, exercise):
        return bool(self.execute_query("SELECT 1 FROM completed_exercises WHERE username = ? AND exercise = ?", (username, exercise), fetchone=True))

    def create_session(self, username):
        session_id = str(uuid.uuid4())
        self.execute_query("INSERT INTO sessions (session_id, username) VALUES (?, ?)", (session_id, username))
        return session_id

    def invalidate_session(self, session_id):
        self.execute_query("DELETE FROM sessions WHERE session_id = ?", (session_id,))

    def get_username_for_session(self, session_id):
        result = self.execute_query("SELECT username FROM sessions WHERE session_id = ?", (session_id,), fetchone=True)
        return result[0] if result else None

# Application class
class KimitCodersApp:
    def __init__(self):
        self.db = DatabaseManager('app.db')
        self.instructions = {
            "hello-world-exercise": "Write your code below to print 'Hello World'.",
            "one-sided-anova": "Provide a code snippet to perform a one-sided ANOVA test.",
            "two-sided-anova": "Provide a code snippet to perform a two-sided ANOVA test."
        }
        self.init_session_state()

    def init_session_state(self):
        default_state = {
            'user': None,
            'score': 0,
            'page': 'login',
            'badge': 'Iron',
            'session_id': None
        }
        for key, value in default_state.items():
            if key not in st.session_state:
                st.session_state[key] = value

    def get_badge(self, score):
        if score >= 50:
            return "Gold"
        elif score >= 30:
            return "Silver"
        elif score >= 10:
            return "Bronze"
        return "Iron"

    def header(self):
        st.sidebar.title("User Info")
        if st.session_state.user:
            st.sidebar.image("path/to/image.jpg", width=100)
            st.sidebar.write(f"**Username:** {st.session_state.user}")
            st.sidebar.write(f"**Score:** {st.session_state.score}")
            st.sidebar.write(f"**Badge:** {st.session_state.badge}")
            if st.sidebar.button("Logout"):
                self.logout()
        else:
            st.sidebar.write("No user logged in.")

    def login_page(self):
        st.write("### Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type='password')

        if st.button("Login"):
            user = self.db.get_user(username)
            if user and user[1] == password:
                self.logout()  # Ensure no active session
                st.session_state.user = username
                st.session_state.score = user[2]
                st.session_state.badge = self.get_badge(user[2])
                st.session_state.page = 'main'
                st.session_state.session_id = self.db.create_session(username)
                st.experimental_rerun()
            else:
                st.error("Invalid username or password")

        if st.button("Register"):
            st.session_state.page = 'register'
            st.experimental_rerun()

    def registration_page(self):
        st.write("### Register")
        username = st.text_input("Username", key="reg_username")
        password = st.text_input("Password", type='password', key="reg_password")

        if st.button("Register"):
            if username and password:
                try:
                    self.db.execute_query("INSERT INTO users (username, password, score) VALUES (?, ?, 0)", (username, password))
                    st.success("Registration successful! Redirecting to login...")
                    st.session_state.page = 'login'
                    st.experimental_rerun()
                except sqlite3.IntegrityError:
                    st.error("Username already exists. Please choose another.")
            else:
                st.error("Both fields are required.")

        if st.button("Back to Login"):
            st.session_state.page = 'login'
            st.experimental_rerun()

    def main_page(self):
        self.header()
        st.write(f"### Welcome, {st.session_state.user}")
        st.write(f"Your Score: {st.session_state.score}")
        st.write(f"Your Badge: {st.session_state.badge}")

        data = [
            {"Method": "One-Sided ANOVA", "Description": "Focus on one side of the distribution.", "Link": "one-sided-anova"},
            {"Method": "Two-Sided ANOVA", "Description": "Considers both sides of the distribution.", "Link": "two-sided-anova"},
            {"Method": "Hello World Exercise", "Description": "Print 'Hello World'.", "Link": "hello-world-exercise"}
        ]
        df = pd.DataFrame(data)
        st.table(df)

        for row in data:
            button_label = f"Practice {row['Method']}"
            if self.db.is_exercise_completed(st.session_state.user, row['Link']):
                button_label = f"✅ {button_label}"
            if st.button(button_label):
                st.session_state.page = row['Link']
                st.experimental_rerun()

        if st.button("Chat with GPT"):
            st.session_state.page = "chatbot"
            st.experimental_rerun()

    def exercise_page(self):
        exercise_name = st.session_state.page
        st.write(f"### {exercise_name.replace('-', ' ').title()}")
        st.write(self.instructions.get(exercise_name, "Instructions not available."))

        code = st.text_area("Python Code", height=300, key=f"{exercise_name}_code")

        if st.button("Submit"):
            output = self.run_code(code)
            st.write("### Output:")
            st.code(output)

            if exercise_name == "hello-world-exercise" and output.strip() == "Hello World":
                self.complete_exercise(exercise_name)
                st.success("✅ Correct!")
            else:
                st.error("❌ Incorrect answer.")

        if st.button("Back to Main Page"):
            st.session_state.page = 'main'
            st.experimental_rerun()

    def chatbot_page(self):
        st.write("### Chat with GPT")
        user_query = st.text_input("Ask a question:")

        if st.button("Send"):
            if user_query.strip():
                response = ask_huggingface(user_query)
                st.write("### Response:")
                st.write(response)
            else:
                st.error("Please enter a valid question.")

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
        finally:
            sys.stdout = sys.__stdout__
        return buffer.getvalue()

    def complete_exercise(self, exercise_name):
        if not self.db.is_exercise_completed(st.session_state.user, exercise_name):
            st.session_state.score += 10
            st.session_state.badge = self.get_badge(st.session_state.score)
            self.db.update_score(st.session_state.user, st.session_state.score)
            self.db.mark_exercise_completed(st.session_state.user, exercise_name)

    def logout(self):
        if st.session_state.session_id:
            self.db.invalidate_session(st.session_state.session_id)
        for key in ['user', 'score', 'badge', 'page', 'session_id']:
            st.session_state[key] = None if key != 'page' else 'login'
        st.experimental_rerun()

    def run(self):
        pages = {
            'login': self.login_page,
            'register': self.registration_page,
            'main': self.main_page,
            'chatbot': self.chatbot_page
        }
        if st.session_state.page in self.instructions:
            self.exercise_page()
        else:
            pages.get(st.session_state.page, self.main_page)()

if __name__ == "__main__":
    app = KimitCodersApp()
    app.run()
