import cv2
import time
from datetime import datetime
import streamlit as st
import json
import google.generativeai as genai
import sqlite3
import hashlib
from ultralytics import YOLO
from streamlit.components.v1 import html

genai.configure(api_key="YOUR_GEMINI_API_KEY")  
model = genai.GenerativeModel("gemini-1.5-flash")

CONFIDENCE_THRESHOLD = 0.5
EXCLUDED_CLASSES = {"person", "face", "human face", "man", "woman", "boy", "girl", "hand", "foot", "eye", "mouth", "leg"}
DETECTION_DURATION = 10

def init_db():
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS leaderboard (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            score INTEGER,
            timestamp DATETIME
        )
    """)
    conn.commit()
    conn.close()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def register_user(username, password):
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hash_password(password)))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def login_user(username, password):
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, hash_password(password)))
    user = c.fetchone()
    conn.close()
    return user

# Save quiz score to the leaderboard
def save_quiz_score(username, score):
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("INSERT INTO leaderboard (username, score, timestamp) VALUES (?, ?, ?)",
              (username, score, datetime.now()))
    conn.commit()
    conn.close()

# Fetch leaderboard data
def get_leaderboard():
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("""
        SELECT username, score, timestamp
        FROM leaderboard
        ORDER BY score DESC, timestamp ASC
        LIMIT 10
    """)
    leaderboard_data = c.fetchall()
    conn.close()
    return leaderboard_data


    
    # Save the quiz score to the leaderboard
    


if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.username = ""
    st.session_state.detected_objects = []
    st.session_state.quiz_data = []
    st.session_state.quiz_answers = {}
    st.session_state.ai_response = {}

def logout():
    st.session_state.authenticated = False
    st.session_state.username = ""
    st.session_state.detected_objects = []
    st.session_state.quiz_data = []
    st.session_state.quiz_answers = {}
    st.session_state.ai_response = {}
    st.rerun()

def login_page():
    st.title("🔑 Login or Register")
    tab1, tab2 = st.tabs(["🔐 Login", "📝 Register"])

    with tab1:
        st.subheader("Login")
        username = st.text_input("Username", key="login_user")
        password = st.text_input("Password", type="password", key="login_pass")
        if st.button("Login"):
            if login_user(username, password):
                st.session_state.authenticated = True
                st.session_state.username = username
                st.success("✅ Login successful!")
                st.rerun()
            else:
                st.error("❌ Invalid username or password.")
    
    with tab2:
        st.subheader("Register")
        new_username = st.text_input("New Username", key="reg_user")
        new_password = st.text_input("New Password", type="password", key="reg_pass")
        if st.button("Register"):
            if register_user(new_username, new_password):
                st.success("✅ Registration successful! Please log in.")
            else:
                st.error("❌ Username already exists. Try another one.")

init_db()
if not st.session_state.authenticated:
    login_page()
else:
    st.sidebar.write(f"👤 Logged in as: {st.session_state.username}")
    if st.sidebar.button("Logout"):
        logout()
    
    st.title("📷 CurioScope: Real-Time Object Detection & AI Insights")
    st.write("Click 'Start Detection' to scan objects and get structured insights.")
    
    if st.button("🚀 Start Detection"):
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            st.error("Could not access the webcam. Please check your camera.")
            st.stop()

        model_yolo = YOLO("yolov8n.pt")
        frame_placeholder = st.empty()
        detected_objects = set()
        start_time = time.time()

        while time.time() - start_time < DETECTION_DURATION:
            ret, frame = cap.read()
            if not ret:
                st.error("Failed to capture frame.")
                break

            results = model_yolo(frame)

            for result in results:
                for box in result.boxes:
                    conf = float(box.conf[0])
                    cls = int(box.cls[0])
                    object_name = model_yolo.names[cls].lower().strip()

                    if conf > CONFIDENCE_THRESHOLD and object_name not in EXCLUDED_CLASSES:
                        detected_objects.add(object_name)

            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame_placeholder.image(frame, channels="RGB", use_container_width=True)

        cap.release()
        cv2.destroyAllWindows()

        st.session_state.detected_objects = list(detected_objects)
        print("Detected Objects:", st.session_state.detected_objects)  # Debugging

    if st.session_state.detected_objects:
        st.write("### ✅ Detected Objects:")
        for i in range(len(st.session_state.detected_objects)):
            st.session_state.detected_objects[i]

    if not st.session_state.ai_response:
        if st.session_state.detected_objects:
            object_prompt = f"""
            You are an AI that provides structured details about objects. Given a list of objects, return a JSON response with:

            1. *"detailed_explanation"* – A detailed explanation of the detected objects and their significance.
            2. *"combined_usage"* – If objects can interact, describe how they can be used together in a meaningful way.
            3. *"step_by_step_activity"* – Activities involving detected objects.
            4. *"quiz"* – At least *4 multiple-choice questions (MCQs)* with:
               - "question": The question text.
               - "options": {{"A": "Option A", "B": "Option B", "C": "Option C", "D": "Option D"}}
               - "correct_answer": The correct option as a string (e.g., "B").
            5. *"youtube_links"* – Provide at least *3 YouTube links*.

            Objects: {', '.join(st.session_state.detected_objects)}

            ### *Expected JSON Format*
            {{
                "detailed_explanation": "Extensive explanation...",
                "combined_usage": "How objects can be used together...",
                "step_by_step_activity": [
                    {{
                        "objects": ["Object1", "Object2"],
                        "steps": [
                            "Step 1: Do this...",
                            "Step 2: Then do this...",
                            "Step 3: Complete the action..."
                        ]
                    }}
                ],
                "youtube_links": ["https://youtube.com/video1", "https://youtube.com/video2"],
                "quiz": [
                    {{
                        "question": "Example question?",
                        "options": {{"A": "Option A", "B": "Option B", "C": "Option C", "D": "Option D"}},
                        "correct_answer": "B"
                    }}
                ]
            }}
            """

            response = model.generate_content(object_prompt)

            output_text = response.text.strip()
            if output_text.startswith("```json"):
                output_text = output_text[7:-3].strip()

            try:
                structured_output = json.loads(output_text)
                if not structured_output:
                    st.error("The AI did not return a valid response. Please try again.")
                else:
                    st.session_state.ai_response = structured_output
                    st.session_state.quiz_data = structured_output.get("quiz", [])
                    st.session_state.quiz_answers = {i: None for i in range(len(st.session_state.quiz_data))}
            except json.JSONDecodeError:
                st.error("Failed to parse the AI response. Please try again.")
        else:
            st.warning("No objects detected. Please try again.")
if st.sidebar.button("Reset Session"):
    st.session_state.detected_objects = []
    st.session_state.ai_response = {}
    st.session_state.quiz_answers = {}
    st.rerun()

def save_feedback(username, rating, feedback):
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            rating INTEGER,
            feedback TEXT,
            timestamp DATETIME
        )
    """)
    c.execute("INSERT INTO feedback (username, rating, feedback, timestamp) VALUES (?, ?, ?, ?)",
              (username, rating, feedback, datetime.now()))
    conn.commit()
    conn.close()

def embed_youtube_video(url):
    try:
        video_id = url.split("v=")[1].split("&")[0]  # Extract video ID from URL
        html_code = f"""
        <iframe width="560" height="315" src="https://www.youtube.com/embed/{video_id}" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>
        """
        html(html_code, width=560, height=315)
    except Exception as e:
        st.warning(f" Here's the link : [🔗 Watch Here]({url})")

# Add this to the session state initialization
if "feedback_submitted" not in st.session_state:
    st.session_state.feedback_submitted = False

if st.session_state.ai_response:
    structured_output = st.session_state.ai_response
    tab1, tab2, tab3, tab4,tab5,tab6 = st.tabs(["📜 AI Insights", "🛠 Step-by-Step Activity", "📝 Quiz", "📺 YouTube Videos","feedback","LeaderBoard"])

    with tab1:
        explanation_text = f"""
        🏷 *Detailed Explanation:*
        ----------------------------
        {structured_output.get('detailed_explanation', 'No explanation available.')}

        🎭 *Combined Usage:*
        ----------------------------
        {structured_output.get('combined_usage', 'No combined usage available.')}
        """
        st.text_area("📜 AI Insights", explanation_text, height=300)

    with tab2:
        st.subheader("🛠 Step-by-Step Activities")
        activities = structured_output.get("step_by_step_activity", [])
        if activities:
            for idx, activity in enumerate(activities):
                st.write(f"### Activity {idx+1}")
                st.write(f"*Objects:* {', '.join(activity['objects'])}")
                st.write("*Steps:*")
                for step in activity["steps"]:
                    st.write(f"- {step}")
        else:
            st.write("No activities available.")

    with tab3:
        st.subheader("📝 Take the Quiz!")
        score = 0
        total_questions = len(st.session_state.quiz_data)

        for idx, q in enumerate(st.session_state.quiz_data):
            st.write(f"*Q{idx+1}: {q['question']}*")
            options = q["options"]  
            correct_option = options[q["correct_answer"]]

            selected_answer = st.radio(
                f"Select an answer for Q{idx+1}:",
                list(options.values()),
                key=f"quiz_{idx}",
                index=None
            )

            if selected_answer:
                st.session_state.quiz_answers[idx] = selected_answer

        if st.button("Submit Quiz"):
            for idx, q in enumerate(st.session_state.quiz_data):
                if st.session_state.quiz_answers[idx] == q["options"][q["correct_answer"]]:
                    score += 1
            st.success(f"🎉 You scored {score}/{total_questions}!")

            save_quiz_score(st.session_state.username, score)

    with tab4:
        st.session_state.active_tab = "📺 YouTube Videos"
        st.markdown(f"<h3 style='text-align: center;'>📺 Recommended YouTube Videos:</h3>", unsafe_allow_html=True)
        for link in structured_output.get("youtube_links", []):
            embed_youtube_video(link)

    with tab5:
        st.session_state.active_tab = "📝 Feedback"
        st.markdown(f"<h3 style='text-align: center;'>📝 Feedback</h3>", unsafe_allow_html=True)

        if not st.session_state.feedback_submitted:
            st.write("We value your feedback! Please rate your learning session and let us know how we can improve.")
            rating = st.slider("Rate your learning session (1 = Poor, 10 = Excellent)", 1, 10, 5)
            feedback = st.text_area("Any suggestions for improvement?")

            if st.button("Submit Feedback"):
                save_feedback(st.session_state.username, rating, feedback)
                st.session_state.feedback_submitted = True
                st.success("Thank you for your feedback!")

                # Suggest improvements based on the rating
                if rating <= 5:
                    st.warning("We're sorry to hear that your experience wasn't great.")
                    
                elif 6 <= rating <= 8:
                    st.info("Thank you for your feedback! Here are some ways we can make your experience even better:")
                    
                else:
                    st.success("We're thrilled you enjoyed the session! Here are some ideas for future enhancements:")
                    
        else:
            st.write("Thank you for your feedback! We appreciate your input.")
    # --- Leaderboard Tab ---
    with tab6:
        st.session_state.active_tab = "🏆 Leaderboard"
        st.markdown(f"<h3 style='text-align: center;'>🏆 Leaderboard</h3>", unsafe_allow_html=True)

            # Fetch leaderboard data
        leaderboard_data = get_leaderboard()

        if leaderboard_data:
            st.write("Here are the top performers:")
    
    # Theme-specific table styling
        if st.session_state.theme == "dark":
            table_style = """
            <style>
            .leaderboard-table {
                width: 100%;
                border-collapse: collapse;
                color: #ffffff;
            }
            .leaderboard-table th, .leaderboard-table td {
                padding: 12px;
                text-align: left;
                border-bottom: 1px solid #444;
            }
            .leaderboard-table th {
                background-color: #4CAF50;
                color: white;
            }
            .leaderboard-table tr:nth-child(even) {
                background-color: #2d2d2d;
            }
            .leaderboard-table tr:hover {
                background-color: #444;
            }
            </style>
        """
        else:
            table_style = """
            <style>
            .leaderboard-table {
                width: 50%;
                border-collapse: collapse;
                color: #000000;
            }
            .leaderboard-table th, .leaderboard-table td {
                padding: 12px;
                text-align: left;
                border-bottom: 1px solid #ddd;
            }
            .leaderboard-table th {
                background-color: #4CAF50;
                color: white;
            }
            .leaderboard-table tr:nth-child(even) {
                background-color: #f2f2f2;
            }
            .leaderboard-table tr:hover {
                background-color: #ddd;
            }
            </style>
        """
    
    # Inject the table style
    st.markdown(table_style, unsafe_allow_html=True)
    
    # Start the table
    st.markdown("""
        <table class="leaderboard-table">
            <tr>
                <th>Rank</th>
                <th>Username</th>
                <th>Score</th>
                <th>Date</th>
            </tr>
    """, unsafe_allow_html=True)
    
    # Add rows to the table
    for rank, (username, score, timestamp) in enumerate(leaderboard_data, start=1):
        st.markdown(f"""
            <tr>
                <td>{rank}</td>
                <td>{username}</td>
                <td>{score}</td>
                <td>{timestamp}</td>
            </tr>
        """, unsafe_allow_html=True)
    
    # Close the table
    st.markdown("</table>", unsafe_allow_html=True)
else:
    st.write("No scores yet. Be the first to take the quiz!")

if "theme" not in st.session_state:
    st.session_state.theme = "light"

# Function to toggle theme
def toggle_theme():
    if st.session_state.theme == "light":
        st.session_state.theme = "dark"
    else:
        st.session_state.theme = "light"

# Add a toggle button in the sidebar
st.sidebar.button("Toggle Theme (Light/Dark)", on_click=toggle_theme)

def apply_theme():
    if st.session_state.theme == "dark":
        st.markdown(
            """
            <style>
            /* General app background and text color */
            .stApp {
                background-color: #1e1e1e;
                color: #ffffff;
            }
            /* Sidebar background and text color */
            .css-18e3th9 {
                background-color: #1e1e1e;
                color: #ffffff;
            }
            /* Main content area background and text color */
            .css-1d391kg {
                background-color: #1e1e1e;
                color: #ffffff;
            }
            /* Text input fields */
            .stTextInput>div>div>input {
                background-color: #2d2d2d;
                color: #ffffff;
            }
            /* Text area fields */
            .stTextArea>div>div>textarea {
                background-color: #2d2d2d;
                color: #ffffff;
            }
            /* Buttons */
            .stButton>button {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px 24px;
                text-align: center;
                text-decoration: none;
                display: inline-block;
                font-size: 16px;
                margin: 4px 2px;
                cursor: pointer;
                border-radius: 12px;
            }
            /* Headers and titles */
            h1, h2, h3, h4, h5, h6 {
                color: #ffffff !important;
            }
            /* Regular text */
            p, div, span, label {
                color: #ffffff !important;
            }
            /* Tables */
            table, th, td {
                color: #ffffff !important;
            }
            /* Links */
            a {
                color: #4CAF50 !important;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <style>
            /* General app background and text color */
            .stApp {
                background-color: #ffffff;
                color: #000000;
            }
            /* Sidebar background and text color */
            .css-18e3th9 {
                background-color: #ffffff;
                color: #000000;
            }
            /* Main content area background and text color */
            .css-1d391kg {
                background-color: #ffffff;
                color: #000000;
            }
            /* Text input fields */
            .stTextInput>div>div>input {
                background-color: #ffffff;
                color: #000000;
            }
            /* Text area fields */
            .stTextArea>div>div>textarea {
                background-color: #ffffff;
                color: #000000;
            }
            /* Buttons */
            .stButton>button {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px 24px;
                text-align: center;
                text-decoration: none;
                display: inline-block;
                font-size: 16px;
                margin: 4px 2px;
                cursor: pointer;
                border-radius: 12px;
            }
            /* Headers and titles */
            h1, h2, h3, h4, h5, h6 {
                color: #000000 !important;
            }
            /* Regular text */
            p, div, span, label {
                color: #000000 !important;
            }
            /* Tables */
            table, th, td {
                color: #000000 !important;
            }
            /* Links */
            a {
                color: #4CAF50 !important;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

# Apply the selected theme
apply_theme()
