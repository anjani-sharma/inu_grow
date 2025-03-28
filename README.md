
# INU Grow App

**INU Grow** is a Flask-based web application designed to assist job seekers in optimizing their CVs and job applications using AI-powered tools. It offers CV analysis, job matching, optimization, and more.

---

## 🚀 Features

- **CV Analysis**: Evaluates CVs for ATS compatibility, keyword optimization, and competitive fit.
- **Job Matching**: Compares CV skills to job descriptions, providing match percentages (technical, soft, weighted).
- **CV Optimization**: Generates an optimized CV tailored to a job description.
- **Cover Letter Generation**: Creates personalized cover letters.
- **Job Search**: Mock job search functionality (to be replaced with a real API).
- **Chat with CV**: Query your CV content using a RAG-based chat system.
- **User Authentication**: Secure registration and login with Flask-Login.

---

## 📦 Prerequisites

- Python 3.13+
- Git (optional, for version control)

---

## 🛠️ Setup

### 1. Navigate to the Project Directory

```bash
cd /Users/anjanisharma/projects/inu_grow_app
```

### 2. Create and Activate a Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows
```

### 3. Install Dependencies

```bash
pip install flask flask-login flask-sqlalchemy flask-migrate werkzeug langchain-openai sentence-transformers faiss-cpu reportlab pymupdf python-docx python-dotenv
```

### 4. Set Up Environment Variables

Create a `.env` file in the root directory with the following content:

```env
OPENAI_API_KEY=your-openai-api-key-here
```

> 🔐 Replace `your-openai-api-key-here` with your actual OpenAI API key.

### 5. Run the App

```bash
python app.py
```

Then, open your browser and visit: [http://localhost:5000](http://localhost:5000)

---

## 🧪 Usage

1. **Register/Login**: Create an account at `/register`, then log in at `/login`.
2. **Analyze CV**: Go to `/analyze`, upload a CV (PDF/DOCX), and enter a job description.
3. **View Results**: See match scores, optimized CV, and cover letter at `/results`.
4. **Job Search**: Use `/job_search` to search jobs (mock data for now).
5. **Chat**: Ask questions about your CV at `/chat`.
6. **Logout**: End your session via the "Logout" link.

---

## 🗂️ Project Structure

```
inu_grow_app/
├── .env                  # API keys (ignored by Git)
├── .gitignore            # Files to ignore in Git
├── README.md             # This file
├── app.py                # Main Flask app
├── langgraph_workflow.py # AI analysis workflow
├── models.py             # Database models
├── job_search.py         # Job search logic
├── rag.py                # RAG chat system
├── templates/            # HTML templates
│   ├── index.html
│   ├── register.html
│   ├── login.html
│   ├── analyze.html
│   ├── results.html
│   ├── preview_cv.html
│   ├── job_search.html
│   ├── chat.html
│   └── base.html
├── static/               # CSS and static assets
│   └── style.css
└── uploads/              # Uploaded CVs (ignored by Git)
```

---

## 🧰 Technologies Used

- Flask, Flask-Login, Flask-SQLAlchemy
- LangChain (OpenAI integration)
- Sentence-Transformers & FAISS (RAG)
- ReportLab & PyMuPDF (PDF handling)
- Bootstrap (Styling)

---

## 💻 Development

To contribute or modify the app:

### Initialize Git

```bash
git init
git add .
git commit -m "Initial commit"
```

### Create a Branch

```bash
git checkout -b feature/your-feature
```

### Commit Changes

```bash
git commit -m "Your change description"
```

---

## 🔮 Future Enhancements

- Integrate a real job search API.
- Improve ATS scoring precision.
- Support additional CV formats.

---

## 📝 Notes

- The database (`database.db`) is SQLite and auto-created on the first run.
- Ensure `.env` is not tracked by Git (already listed in `.gitignore`).

---
