import streamlit as st
import sqlite3
import pandas as pd
import io
import sys
import uuid  # For generating unique session IDs
from chatgpt_integration import ask_huggingface  # Import Hugging Face function


# Initialize the database
def init_db():
    conn = sqlite3.connect('app.db')
    c = conn.cursor()
    # Create tables
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (username TEXT PRIMARY KEY, password TEXT, score INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS completed_exercises
                 (username TEXT, exercise TEXT, PRIMARY KEY(username, exercise))''')
    c.execute('''CREATE TABLE IF NOT EXISTS sessions
                 (session_id TEXT PRIMARY KEY, username TEXT)''')
    conn.commit()
    conn.close()

# Function to get user data
def get_user(username):
    conn = sqlite3.connect('app.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = c.fetchone()
    conn.close()
    return user

# Function to update user score
def update_score(username, score):
    conn = sqlite3.connect('app.db')
    c = conn.cursor()
    c.execute("UPDATE users SET score = ? WHERE username = ?", (score, username))
    conn.commit()
    conn.close()

# Function to get badge based on score
def get_badge(score):
    if score >= 50:
        return "Gold"
    elif score >= 30:
        return "Silver"
    elif score >= 10:
        return "Bronze"
    else:
        return "Iron"

# Function to mark exercise as completed
def mark_exercise_completed(username, exercise):
    conn = sqlite3.connect('app.db')
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO completed_exercises (username, exercise) VALUES (?, ?)", (username, exercise))
    conn.commit()
    conn.close()

# Function to check if exercise is completed
def is_exercise_completed(username, exercise):
    conn = sqlite3.connect('app.db')
    c = conn.cursor()
    c.execute("SELECT * FROM completed_exercises WHERE username = ? AND exercise = ?", (username, exercise))
    completed = c.fetchone() is not None
    conn.close()
    return completed

# Function to create a new session
def create_session(username):
    session_id = str(uuid.uuid4())
    conn = sqlite3.connect('app.db')
    c = conn.cursor()
    c.execute("INSERT INTO sessions (session_id, username) VALUES (?, ?)", (session_id, username))
    conn.commit()
    conn.close()
    return session_id

# Function to invalidate a session
def invalidate_session(session_id):
    conn = sqlite3.connect('app.db')
    c = conn.cursor()
    c.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
    conn.commit()
    conn.close()

# Function to get the username for a session ID
def get_username_for_session(session_id):
    conn = sqlite3.connect('app.db')
    c = conn.cursor()
    c.execute("SELECT username FROM sessions WHERE session_id = ?", (session_id,))
    username = c.fetchone()
    conn.close()
    return username[0] if username else None

# Initialize the database
init_db()

# Initialize session state
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

# Define instructions for each exercise
instructions = {
    "hello-world-exercise": "Write your code below to print 'Hello World'.",
    "one-sided-anova": "Provide a code snippet to perform a one-sided ANOVA test.",
    "two-sided-anova": "Provide a code snippet to perform a two-sided ANOVA test."
}

# Streamlit app
st.title("KimitCoders")

# Function to render the header
def header():
    st.sidebar.title("User Info")
    if st.session_state.user:
        user = st.session_state.user
        st.sidebar.image(r"C:\Users\Blu-Ray\Desktop\mygit\Cv\Part1\main-qimg-6aa2cd5346b32a1a939af348bd186d1d-lq.jpg", width=100)
        st.sidebar.write(f"**Username:** {user}")
        st.sidebar.write(f"**Score:** {st.session_state.score}")
        st.sidebar.write(f"**Badge:** {st.session_state.badge}")
        if st.sidebar.button("Logout"):
            logout()
    else:
        st.sidebar.write("No user logged in.")

# Login Page
def login_page():
    st.write("### Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type='password')

    if st.button("Login"):
        user = get_user(username)
        if user and user[1] == password:
            # Invalidate any existing session
            if st.session_state.session_id:
                invalidate_session(st.session_state.session_id)

            st.session_state.user = username
            st.session_state.score = user[2]
            st.session_state.badge = get_badge(st.session_state.score)
            st.session_state.page = 'main'

            # Create a new session
            st.session_state.session_id = create_session(username)
            st.experimental_rerun()
        else:
            st.error("Invalid username or password")

    if st.button("Register"):
        st.session_state.page = 'register'
        st.experimental_rerun()

# Registration Page
def registration_page():
    st.write("### Register")
    username = st.text_input("Username", key="reg_username")
    password = st.text_input("Password", type='password', key="reg_password")

    if st.button("Register"):
        conn = sqlite3.connect('app.db')
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO users (username, password, score) VALUES (?, ?, 0)", (username, password))
        conn.commit()
        conn.close()
        st.session_state.page = 'login'
        st.experimental_rerun()

    if st.button("Back to Login"):
        st.session_state.page = 'login'
        st.experimental_rerun()

# Main Page
def main_page():
    header()
    st.write(f"### Welcome, {st.session_state.user}")
    st.write("Your Score: ", st.session_state.score)
    st.write("Your Badge: ", st.session_state.badge)

    # Display options for exercises
    data = [
        {
            "Method": "One-Sided ANOVA",
            "Description": "Tests if the means of several groups are significantly different from each other, focusing on one side of the distribution.",
            "Application": "Testing for differences in group means when focusing on one side of the distribution.",
            "Link": "one-sided-anova"
        },
        {
            "Method": "Two-Sided ANOVA",
            "Description": "Tests if the means of several groups are significantly different from each other, considering both sides of the distribution.",
            "Application": "Testing for differences in group means considering both sides of the distribution.",
            "Link": "two-sided-anova"
        },
        {
            "Method": "Hello World Exercise",
            "Description": "A simple exercise to print 'Hello World' and check the output.",
            "Application": "Testing basic Python code execution.",
            "Link": "hello-world-exercise"
        }
    ]
    df = pd.DataFrame(data)
    st.write(df)

    for index, row in df.iterrows():
        method_name = row["Method"]
        practice_link = row["Link"]
        button_label = f"Practice {method_name}"
        if is_exercise_completed(st.session_state.user, practice_link):
            button_label = f"✅ {button_label}"
        if st.button(button_label):
            st.session_state.page = practice_link
            st.experimental_rerun()

    # Add a chatbot button
    if st.button("Chat with GPT"):
        st.session_state.page = "chatbot"
        st.experimental_rerun()

#Chatbot page
# Chatbot page function
def chatbot_page():
    st.write("### Chat with GPT-2")
    user_query = st.text_input("Ask a question:")

    if st.button("Send"):
        if user_query.strip():
            response = ask_huggingface(user_query)  # Call the Hugging Face function
            st.write("### Response:")
            st.write(response)
        else:
            st.error("Please enter a valid question.")

    if st.button("Back to Main Page"):
        st.session_state.page = 'main'
        st.experimental_rerun()

def exercise_page():
    exercise_name = st.session_state.page
    st.write(f"### {exercise_name.replace('-', ' ').title()}")

    # Display instructions
    if exercise_name in instructions:
        st.write("### Instructions:")
        st.write(instructions[exercise_name])
    else:
        st.write("### Instructions not available.")

    st.write("Write your code below and submit it to solve the exercise.")

    code_key = f"{exercise_name}_code"
    code = st.text_area("Python Code", height=300, key=code_key)

    # Submission button
    if st.button("Submit"):
        output = run_code(code)  # Run the user-provided code
        st.write("### Output:")
        st.code(output)

        # Check correctness
        if exercise_name == "hello-world-exercise" and "Hello World" in output.strip():
            st.success("✅ Your answer is correct.")
            if not is_exercise_completed(st.session_state.user, exercise_name):
                st.session_state.score += 10
                st.session_state.badge = get_badge(st.session_state.score)
                update_score(st.session_state.user, st.session_state.score)
                mark_exercise_completed(st.session_state.user, exercise_name)
        else:
            st.error("❌ Your answer is incorrect.")

    # Add navigation buttons
    if st.button("Back to Main Page"):
        st.session_state.page = 'main'
        st.experimental_rerun()

        
        

# Function to run the code and capture the output
def run_code(code):
    buffer = io.StringIO()
    sys.stdout = buffer
    try:
        exec(code)
    except Exception as e:
        return str(e)
    return buffer.getvalue()

# Logout function
def logout():
    if st.session_state.session_id:
        invalidate_session(st.session_state.session_id)
    st.session_state.user = None
    st.session_state.score = 0
    st.session_state.badge = 'Iron'
    st.session_state.page = 'login'
    st.session_state.session_id = None
    st.experimental_rerun()

# Page routing
if st.session_state.page == 'login':
    login_page()
elif st.session_state.page == 'register':
    registration_page()
elif st.session_state.page in instructions:
    exercise_page()
elif st.session_state.page == 'chatbot':
    chatbot_page()
else:
    main_page()