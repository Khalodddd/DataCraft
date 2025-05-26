import streamlit as st
import sqlite3
import io
import sys
import uuid
import smtplib
from email.message import EmailMessage
import random
import string
import hashlib
import re
import pandas as pd
from datetime import datetime
import time

# Email Configuration
EMAIL_ADDRESS = "Enter your email"
EMAIL_PASSWORD = "Enter you 16 digit password from gmail security"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

class DatabaseHandler:
    def __init__(self, db_name="app.db"):
        self.db_name = db_name
        self.init_db()

    def _get_connection(self):
        """Get a database connection with retry logic"""
        max_retries = 5
        for attempt in range(max_retries):
            try:
                conn = sqlite3.connect(self.db_name, timeout=10)
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA busy_timeout=5000")
                return conn
            except sqlite3.OperationalError as e:
                if "locked" in str(e) and attempt < max_retries - 1:
                    time.sleep(0.1 * (attempt + 1))
                    continue
                raise

    def init_db(self):
        conn = None
        try:
            conn = self._get_connection()
            c = conn.cursor()
            
            # Create tables with all columns (without problematic defaults)
            c.execute('''CREATE TABLE IF NOT EXISTS users
                         (username TEXT PRIMARY KEY, 
                          password TEXT, 
                          email TEXT,
                          score INTEGER DEFAULT 0,
                          verified INTEGER DEFAULT 0,
                          created_at TEXT)''')
            
            c.execute('''CREATE TABLE IF NOT EXISTS completed_exercises
                         (username TEXT, 
                          exercise TEXT, 
                          created_at TEXT,
                          PRIMARY KEY(username, exercise))''')
            
            c.execute('''CREATE TABLE IF NOT EXISTS sessions
                         (session_id TEXT PRIMARY KEY, 
                          username TEXT,
                          created_at TEXT)''')
            
            c.execute('''CREATE TABLE IF NOT EXISTS verification_codes
                         (email TEXT PRIMARY KEY,
                          code TEXT,
                          created_at TEXT)''')
            
            c.execute('''CREATE TABLE IF NOT EXISTS admin
                         (username TEXT PRIMARY KEY,
                          password TEXT,
                          created_at TEXT)''')
            
            # Initialize admin if not exists
            admin_exists = c.execute("SELECT 1 FROM admin WHERE username='admin'").fetchone()
            if not admin_exists:
                current_time = datetime.now().isoformat()
                c.execute('''INSERT INTO admin (username, password, created_at) 
                             VALUES (?, ?, ?)''', 
                             ('admin', hash_password('admin123'), current_time))
            
            # Add any missing columns without defaults
            self._add_missing_columns(conn)
            
            conn.commit()
        except sqlite3.Error as e:
            st.error(f"Database initialization error: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()

    def _add_missing_columns(self, conn):
        """Add missing columns without using non-constant defaults"""
        c = conn.cursor()
        
        tables = {
            'users': ['username', 'password', 'email', 'score', 'verified', 'created_at'],
            'completed_exercises': ['username', 'exercise', 'created_at'],
            'sessions': ['session_id', 'username', 'created_at'],
            'verification_codes': ['email', 'code', 'created_at'],
            'admin': ['username', 'password', 'created_at']
        }
        
        for table, columns in tables.items():
            c.execute(f"PRAGMA table_info({table})")
            existing_columns = [col[1] for col in c.fetchall()]
            
            for col in columns:
                if col not in existing_columns:
                    try:
                        # Add column without DEFAULT constraint
                        if col in ['score', 'verified']:
                            c.execute(f"ALTER TABLE {table} ADD COLUMN {col} INTEGER DEFAULT 0")
                        elif col == 'created_at':
                            c.execute(f"ALTER TABLE {table} ADD COLUMN {col} TEXT")
                        else:
                            c.execute(f"ALTER TABLE {table} ADD COLUMN {col} TEXT")
                    except sqlite3.OperationalError as e:
                        if "duplicate column name" not in str(e):
                            raise

    def execute_query(self, query, params=(), fetch_one=False, fetch_all=False):
        conn = None
        try:
            conn = self._get_connection()
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute(query, params)
            result = None
            if fetch_one:
                result = c.fetchone()
            elif fetch_all:
                result = c.fetchall()
            conn.commit()
            return result
        except sqlite3.Error as e:
            st.error(f"Database error: {e}")
            if conn:
                conn.rollback()
            return None
        finally:
            if conn:
                conn.close()

def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def generate_verification_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

def send_verification_email(recipient_email, code):
    try:
        msg = EmailMessage()
        msg['Subject'] = "DataCraft - Verify Your Email"
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = recipient_email
        msg.set_content(f"""Welcome to DataCraft!
        
Your verification code: {code}
        
This code will expire in 30 minutes.""")

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)
        return True, "Verification email sent"
    except Exception as e:
        return False, f"Email failed: {str(e)}"

class Exercise:
    def __init__(self, name, instructions, answer):
        self.name = name
        self.instructions = instructions
        self.answer = answer

    def is_correct(self, output):
        return self.answer in output.strip()

class UserManager:
    def __init__(self, db_handler):
        self.db_handler = db_handler

    def get_user(self, username):
        user = self.db_handler.execute_query(
            "SELECT * FROM users WHERE username = ?", 
            (username,), 
            fetch_one=True
        )
        return user

    def register_user(self, username, password, email):
        if not validate_email(email):
            return False, "Invalid email format"
        
        code = generate_verification_code()
        success, message = send_verification_email(email, code)
        if not success:
            return False, message
        
        hashed_pw = hash_password(password)
        current_time = datetime.now().isoformat()
        try:
            self.db_handler.execute_query(
                "INSERT INTO users (username, password, email, created_at) VALUES (?, ?, ?, ?)",
                (username, hashed_pw, email, current_time)
            )
            self.db_handler.execute_query(
                "INSERT OR REPLACE INTO verification_codes (email, code, created_at) VALUES (?, ?, ?)",
                (email, code, current_time)
            )
            return True, "Verification email sent"
        except sqlite3.IntegrityError as e:
            return False, f"Registration failed: {str(e)}"

    def verify_email(self, email, code):
        db_code = self.db_handler.execute_query(
            """SELECT code, created_at FROM verification_codes WHERE email = ?""",
            (email,),
            fetch_one=True
        )
        
        if not db_code or not db_code['created_at']:
            return False, "No verification request found"
            
        try:
            # Check if code is expired (30 minutes)
            code_time = datetime.fromisoformat(db_code['created_at'])
            time_diff = (datetime.now() - code_time).total_seconds()
            
            if time_diff > 1800:  # 30 minutes in seconds
                return False, "Verification code expired"
                
            if code != db_code['code']:
                return False, "Invalid verification code"
        except (ValueError, TypeError) as e:
            return False, "Invalid timestamp format"
        
        self.db_handler.execute_query(
            "UPDATE users SET verified = 1 WHERE email = ?",
            (email,)
        )
        self.db_handler.execute_query(
            "DELETE FROM verification_codes WHERE email = ?",
            (email,)
        )
        return True, "Email verified"

    def update_score(self, username, score):
        self.db_handler.execute_query(
            "UPDATE users SET score = ? WHERE username = ?",
            (score, username)
        )

    def mark_exercise_completed(self, username, exercise):
        current_time = datetime.now().isoformat()
        self.db_handler.execute_query(
            "INSERT OR IGNORE INTO completed_exercises (username, exercise, created_at) VALUES (?, ?, ?)",
            (username, exercise, current_time)
        )

    def is_exercise_completed(self, username, exercise):
        result = self.db_handler.execute_query(
            "SELECT 1 FROM completed_exercises WHERE username = ? AND exercise = ?",
            (username, exercise),
            fetch_one=True
        )
        return result is not None

    def is_verified(self, username):
        result = self.db_handler.execute_query(
            "SELECT verified FROM users WHERE username = ?",
            (username,),
            fetch_one=True
        )
        return result and result['verified'] == 1

    def get_all_users(self):
        return self.db_handler.execute_query(
            "SELECT username, email, score, verified, created_at FROM users",
            fetch_all=True
        )

    def delete_user(self, username):
        self.db_handler.execute_query(
            "DELETE FROM users WHERE username = ?",
            (username,)
        )

    def update_user(self, username, new_data):
        self.db_handler.execute_query(
            """UPDATE users SET 
               username = ?, email = ?, score = ?, verified = ? 
               WHERE username = ?""",
            (new_data['username'], new_data['email'], 
             new_data['score'], new_data['verified'], username)
        )

class SessionManager:
    def __init__(self, db_handler):
        self.db_handler = db_handler

    def create_session(self, username):
        session_id = str(uuid.uuid4())
        current_time = datetime.now().isoformat()
        self.db_handler.execute_query(
            "INSERT INTO sessions (session_id, username, created_at) VALUES (?, ?, ?)",
            (session_id, username, current_time)
        )
        return session_id

    def invalidate_session(self, session_id):
        self.db_handler.execute_query(
            "DELETE FROM sessions WHERE session_id = ?",
            (session_id,)
        )

    def get_username_for_session(self, session_id):
        result = self.db_handler.execute_query(
            "SELECT username FROM sessions WHERE session_id = ?",
            (session_id,),
            fetch_one=True
        )
        return result[0] if result else None

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
        if 'email' not in st.session_state:
            st.session_state.email = None
        if 'score' not in st.session_state:
            st.session_state.score = 0
        if 'page' not in st.session_state:
            st.session_state.page = 'login'
        if 'reg_step' not in st.session_state:
            st.session_state.reg_step = 'initial'
        if 'badge' not in st.session_state:
            st.session_state.badge = 'Iron'
        if 'session_id' not in st.session_state:
            st.session_state.session_id = None
        if 'is_admin' not in st.session_state:
            st.session_state.is_admin = False

    def get_badge(self, score):
        if score is None:
            return "Iron"
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
        elif st.session_state.page == 'verify':
            self.verification_page()
        elif st.session_state.page == 'admin_dashboard':
            self.admin_dashboard()
        elif st.session_state.page == 'chatbot':
            self.chatbot_page()
        elif st.session_state.page in self.exercises:
            self.exercise_page()
        else:
            self.main_page()

    def login_page(self):
        st.title('Data Craft')
        st.title("Login")
        
        admin_mode = st.checkbox("Admin Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type='password')

        if st.button("Login"):
            if admin_mode:
                admin = self.db_handler.execute_query(
                    "SELECT password FROM admin WHERE username = ?",
                    (username,),
                    fetch_one=True
                )
                if admin and hash_password(password) == admin['password']:
                    st.session_state.user = username
                    st.session_state.is_admin = True
                    st.session_state.page = 'admin_dashboard'
                    st.session_state.session_id = self.session_manager.create_session(username)
                    st.rerun()
                else:
                    st.error("Invalid admin credentials")
            else:
                user = self.user_manager.get_user(username)
                if user and hash_password(password) == user['password']:
                    if not self.user_manager.is_verified(username):
                        st.error("Account not verified. Please check your email.")
                        return
                    
                    if st.session_state.session_id:
                        self.session_manager.invalidate_session(st.session_state.session_id)

                    st.session_state.user = username
                    st.session_state.email = user['email']
                    st.session_state.score = user['score'] if user['score'] is not None else 0
                    st.session_state.badge = self.get_badge(st.session_state.score)
                    st.session_state.page = 'main'
                    st.session_state.is_admin = False
                    st.session_state.session_id = self.session_manager.create_session(username)
                    st.rerun()
                else:
                    st.error("Invalid username or password")

        if st.button("Register"):
            st.session_state.page = 'register'
            st.rerun()

    def registration_page(self):
        if st.session_state.reg_step == 'initial':
            st.title("Register")
            username = st.text_input("Username (minimum 4 characters)")
            password = st.text_input("Password (minimum 6 characters)", type='password')
            email = st.text_input("Email")

            if st.button("Register"):
                if len(username) < 4:
                    st.error("Username must be at least 4 characters")
                    return
                if len(password) < 6:
                    st.error("Password must be at least 6 characters")
                    return
                if not validate_email(email):
                    st.error("Please enter a valid email address")
                    return
                
                success, message = self.user_manager.register_user(username, password, email)
                if success:
                    st.session_state.reg_step = 'verify'
                    st.session_state.temp_user = username
                    st.session_state.temp_email = email
                    st.rerun()
                else:
                    st.error(message)

            if st.button("Back to Login"):
                st.session_state.page = 'login'
                st.rerun()
        
        elif st.session_state.reg_step == 'verify':
            st.title("Verify Your Email")
            st.write(f"Verification code sent to: {st.session_state.temp_email}")
            code = st.text_input("Enter verification code (8 characters)", max_chars=8)
            
            if st.button("Verify"):
                if len(code) != 8:
                    st.error("Please enter a valid 8-digit code")
                    return
                
                success, message = self.user_manager.verify_email(st.session_state.temp_email, code)
                if success:
                    st.success("Account verified! You can now login.")
                    st.session_state.reg_step = 'initial'
                    st.session_state.page = 'login'
                    st.rerun()
                else:
                    st.error(message)
            
            if st.button("Resend Code"):
                new_code = generate_verification_code()
                current_time = datetime.now().isoformat()
                self.db_handler.execute_query(
                    """UPDATE verification_codes 
                       SET code = ?, created_at = ?
                       WHERE email = ?""",
                    (new_code, current_time, st.session_state.temp_email)
                )
                send_verification_email(st.session_state.temp_email, new_code)
                st.success("New verification code sent!")
            
            if st.button("Back to Registration"):
                st.session_state.reg_step = 'initial'
                st.rerun()

    def admin_dashboard(self):
        st.title("👨‍💻 Admin Dashboard")
        
        st.subheader("User Management")
        users = self.user_manager.get_all_users()
        
        if users:
            df = pd.DataFrame(users, columns=["Username", "Email", "Score", "Verified", "Created At"])
            edited_df = st.data_editor(
                df,
                num_rows="dynamic",
                disabled=["Username"],
                use_container_width=True
            )
            
            if st.button("Save Changes"):
                for _, row in edited_df.iterrows():
                    self.user_manager.update_user(
                        row['Username'],
                        {
                            'username': row['Username'],
                            'email': row['Email'],
                            'score': row['Score'] if pd.notna(row['Score']) else 0,
                            'verified': row['Verified'] if pd.notna(row['Verified']) else 0
                        }
                    )
                st.success("Changes saved!")
                st.rerun()
            
            st.subheader("Add New User")
            with st.form("add_user_form"):
                new_username = st.text_input("Username")
                new_email = st.text_input("Email")
                new_password = st.text_input("Password", type="password")
                new_score = st.number_input("Score", min_value=0, value=0)
                
                if st.form_submit_button("Add User"):
                    hashed_pw = hash_password(new_password)
                    current_time = datetime.now().isoformat()
                    self.db_handler.execute_query(
                        """INSERT INTO users 
                           (username, email, password, score, verified, created_at)
                           VALUES (?, ?, ?, ?, 1, ?)""",
                        (new_username, new_email, hashed_pw, new_score, current_time)
                    )
                    st.success("User added!")
                    st.rerun()
            
            st.subheader("Delete User")
            user_to_delete = st.selectbox(
                "Select user to delete",
                [user['username'] for user in users]
            )
            
            if st.button("Delete User"):
                if user_to_delete != "admin":
                    self.user_manager.delete_user(user_to_delete)
                    st.success(f"User {user_to_delete} deleted!")
                    st.rerun()
                else:
                    st.error("Cannot delete admin user")
        else:
            st.warning("No users found")
        
        if st.button("Logout"):
            self.logout()
            st.rerun()

    def main_page(self):
        st.image("WhatsApp Image 2024-12-13 at 20.47.24_3f75e257.jpg", width=300)
        st.title("DataCraft")
        st.write('### Learn data and AI skill')
        st.write('Unlock the power of data and AI by learning Python, ChatGPT, SQL, Power BI, and earn Certifications.')

        st.sidebar.title("User Info")
        if st.session_state.user:
            st.sidebar.image("93d3e31639a4d07613de9dccdc8bd5e8.jpg", width=100)
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
                st.rerun()
    
        if st.button("Ask Ai 🤖", help="Click the robot button!"):
            st.session_state.page = "chatbot"
            st.rerun()

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
                    new_score = (st.session_state.score or 0) + 10
                    st.session_state.score = new_score
                    st.session_state.badge = self.get_badge(new_score)
                    self.user_manager.update_score(st.session_state.user, new_score)
                    self.user_manager.mark_exercise_completed(st.session_state.user, exercise_name)
            else:
                st.error("❌ Your answer is incorrect.")

        if st.button("Back to Main Page"):
            st.session_state.page = 'main'
            st.rerun()

    def chatbot_page(self):
        st.title("Ask Zelda🤖")
        user_query = st.text_input("Ask a question:")

        if st.button("Send"):
            if user_query.strip():
                st.write("### Response:")
                st.write("Hi, I'm your Zelda AI! I'm here to help you practice and improve your coding skills. Let's tackle challenges together!")
                
            with st.expander("See detailed response"):
                st.write("This is a placeholder for the actual AI response. In a real implementation, you would connect to an AI service here.")

        if st.button("Back to Main Page"):
            st.session_state.page = 'main'
            st.rerun()

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
        st.session_state.email = None
        st.session_state.score = 0
        st.session_state.badge = 'Iron'
        st.session_state.page = 'login'
        st.session_state.session_id = None
        st.session_state.is_admin = False
        st.rerun()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

if __name__ == '__main__':
    if not all([EMAIL_ADDRESS, EMAIL_PASSWORD]):
        st.error("Email credentials not configured. Please set your Gmail and app password.")
    else:
        try:
            app = StreamlitApp()
            app.run()
        except Exception as e:
            st.error(f"Application error: {e}")
            st.stop()