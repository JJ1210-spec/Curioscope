# 📷 CurioScope – AI-Driven Object Detection & Insights

CurioScope is a Streamlit-based interactive app that combines **real-time object detection (YOLOv8)** with **Generative AI (Gemini)** to provide:
- 📌 Object-based explanations
- 🧠 Combined usage suggestions
- 🧩 Step-by-step activities
- 📝 MCQ-based quizzes
- 📺 Relevant YouTube links
- 🏆 Leaderboard & feedback system
- 🌗 Dark/Light theme toggle

---

## 🚀 Features

### 🔍 Real-Time Object Detection
- Uses YOLOv8 for detecting objects from webcam.
- Filters out faces and humans to maintain privacy.

### 🤖 Gemini AI-Powered Insights
- Structured JSON response using Google's Gemini API.
- Explains detected objects, combined use, and provides quizzes.

### 🧠 Quiz Engine
- AI-generated MCQs based on detected objects.
- User scores are recorded and shown in a leaderboard.

### 📊 Leaderboard System
- View top performers and timestamp of achievements.

### 💬 Feedback Module
- Collects user feedback with ratings and suggestions.

### 🌗 Theme Support
- Toggle between dark and light mode in real-time.

---

## 🛠️ Tech Stack

| Layer       | Technology                    |
|------------|-------------------------------|
| Frontend    | [Streamlit](https://streamlit.io) |
| Object Detection | [YOLOv8 (Ultralytics)](https://docs.ultralytics.com/) |
| AI Integration | [Gemini 1.5 Flash (Google Generative AI)](https://ai.google.dev/) |
| Database    | SQLite (via `sqlite3`)        |
| Language    | Python                        |

---

## 📦 Setup Instructions

### 1️⃣ Clone the Repository
```bash
git clone https://github.com/YOUR_USERNAME/curioscope.git
cd curioscope
