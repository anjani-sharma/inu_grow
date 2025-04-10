from flask import Flask, render_template, request, redirect, url_for, flash, session, make_response
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
import os
import secrets
from models import db, User, CV, JobDescription
from langgraph_workflow import matching_workflow
from job_search import JobSearchAgent
from rag import RAG
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO
import fitz  # PyMuPDF

app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(16)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['SESSION_PERMANENT'] = True
app.config['SESSION_TYPE'] = 'filesystem'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db.init_app(app)
migrate = Migrate(app, db)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

rag = RAG()
job_search_agent = JobSearchAgent()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'pdf', 'docx'}

def extract_text_from_pdf(filepath):
    try:
        doc = fitz.open(filepath)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text.strip()
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        return ""

def extract_text_from_docx(filepath):
    from docx import Document
    try:
        doc = Document(filepath)
        text = ''
        for para in doc.paragraphs:
            if para.text.strip():
                text += para.text + '\n'
        return text.strip()
    except Exception as e:
        print(f"Error extracting text from DOCX: {e}")
        return ""

@app.route('/download_optimized_cv/<content>')
@login_required
def download_optimized_cv(content):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    p.setFont("Helvetica", 12)
    y = 750
    for line in content.split('\n'):
        if y < 50:
            p.showPage()
            p.setFont("Helvetica", 12)
            y = 750
        p.drawString(50, y, line)
        y -= 15
    p.showPage()
    p.save()
    buffer.seek(0)
    response = make_response(buffer.getvalue())
    response.headers['Content-Disposition'] = 'attachment; filename=optimized_cv.pdf'
    response.headers['Content-Type'] = 'application/pdf'
    return response

@app.route('/download_cover_letter/<content>')
@login_required
def download_cover_letter(content):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    p.setFont("Helvetica", 12)
    y = 750
    for line in content.split('\n'):
        if y < 50:
            p.showPage()
            p.setFont("Helvetica", 12)
            y = 750
        p.drawString(50, y, line)
        y -= 15
    p.showPage()
    p.save()
    buffer.seek(0)
    response = make_response(buffer.getvalue())
    response.headers['Content-Disposition'] = 'attachment; filename=cover_letter.pdf'
    response.headers['Content-Type'] = 'application/pdf'
    return response

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, password=hashed_password)
        try:
            db.session.add(new_user)
            db.session.commit()
            flash('Registration successful! Please log in.')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash(f'Registration failed: {e}')
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('index'))
        flash('Invalid username or password')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    session.clear()
    logout_user()
    return redirect(url_for('index'))

@app.route('/upload_cv_dashboard', methods=['POST'])
@login_required
def upload_cv_dashboard():
    if 'cv_file' not in request.files:
        flash('No file part in request', 'danger')
        return redirect(url_for('index'))

    file = request.files['cv_file']
    if file.filename == '':
        flash('No file selected', 'danger')
        return redirect(url_for('index'))

    if not allowed_file(file.filename):
        flash('Invalid file type. Only PDF or DOCX allowed.', 'danger')
        return redirect(url_for('index'))

    user_cvs = CV.query.filter_by(user_id=current_user.id).all()
    if len(user_cvs) >= 5:
        flash('You can only save up to 5 CVs.', 'warning')
        return redirect(url_for('index'))

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(filepath)

    # ✅ Add duplicate filename check
    existing_cv_by_name = CV.query.filter_by(user_id=current_user.id, filename=file.filename).first()
    if existing_cv_by_name:
        flash("You have already uploaded a CV with this filename.", "warning")
        return redirect(url_for('index'))

    # ✅ Extract text
    if file.filename.endswith('.pdf'):
        cv_text = extract_text_from_pdf(filepath)
    else:
        cv_text = extract_text_from_docx(filepath)

    if not cv_text:
        flash('Failed to extract text from the CV.', 'danger')
        return redirect(url_for('index'))

    # ✅ Add duplicate content check
    existing_cv_by_content = CV.query.filter_by(user_id=current_user.id, content=cv_text).first()
    if existing_cv_by_content:
        flash("This CV has already been uploaded before.", "warning")
        return redirect(url_for('index'))

    # Extract text and parse
    if file.filename.endswith('.pdf'):
        cv_text = extract_text_from_pdf(filepath)
    else:
        cv_text = extract_text_from_docx(filepath)

    if not cv_text:
        flash('Failed to extract text from the CV.', 'danger')
        return redirect(url_for('index'))

    # Use your hybrid parser
    from cv_parser_utils import parse_and_enhance_cv
    result = parse_and_enhance_cv(cv_text)
    parsed_data = result["parsed_data"]
    skills = result["enhanced_skills"]

    new_cv = CV(
        user_id=current_user.id,
        filename=file.filename,
        content=cv_text,
        skills=",".join(skills),
        summary=parsed_data.get("summary", "")
    )
    db.session.add(new_cv)
    db.session.commit()

    # Add CV to semantic index
    
    rag.add_document(cv_text, doc_id=str(new_cv.id))

    flash("CV uploaded and parsed successfully.", "success")
    return redirect(url_for('index'))


@app.route('/analyze', methods=['GET', 'POST'])
@login_required
def analyze():
    pre_uploaded_cvs = CV.query.filter_by(user_id=current_user.id).all()
    cv_count = len(pre_uploaded_cvs)
    max_cvs = 5
    can_upload_new = cv_count < max_cvs

    if request.method == 'POST':
        job_desc = request.form.get('job_desc', '').strip()
        if not job_desc:
            flash('Please provide a job description.')
            return redirect(request.url)

        session['job_desc'] = job_desc

        cv_selection = request.form.get('cv_selection', '')
        cv_text = None
        cv_filename = None
        cv_skills = []

        if cv_selection == 'new' or not pre_uploaded_cvs:
            if not can_upload_new:
                flash(f'You have reached the maximum limit of {max_cvs} CVs.')
                return redirect(request.url)
            if 'cv_file' not in request.files:
                flash('No CV file part')
                return redirect(request.url)
            file = request.files['cv_file']
            if file.filename == '':
                flash('No CV file selected')
                return redirect(request.url)
            if not allowed_file(file.filename):
                flash('Invalid file type. Only PDF or DOCX allowed.')
                return redirect(request.url)

            filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filepath)
            if file.filename.endswith('.pdf'):
                cv_text = extract_text_from_pdf(filepath)
            else:
                cv_text = extract_text_from_docx(filepath)

            if not cv_text:
                flash('Failed to extract text from the CV.')
                return redirect(request.url)
            cv_filename = file.filename
        else:
            selected_cv_id = request.form.get('pre_uploaded_cv', '')
            if not selected_cv_id:
                flash('Please select a pre-uploaded CV.')
                return redirect(request.url)
            selected_cv = CV.query.filter_by(id=selected_cv_id, user_id=current_user.id).first()
            if not selected_cv:
                flash('Selected CV not found.')
                return redirect(request.url)
            cv_text = selected_cv.content
            cv_filename = selected_cv.filename
            cv_skills = selected_cv.skills.split(',') if selected_cv.skills else []

        rag.add_document(cv_text)
        state = {"cv_text": cv_text, "job_desc": job_desc}
        result = matching_workflow.invoke(state)
        cv_skills = result['cv_skills']
        matches = result['matches']
        match_percentage = result['match_percentage']
        optimized_cv = result['optimized_cv']
        cover_letter = result['cover_letter']
        analysis_results = result['analysis_results']
        weighted_match_percentage = result['weighted_match_percentage']
        tech_match_percentage = result['tech_match_percentage']
        soft_match_percentage = result['soft_match_percentage']
        job_technical_skills = result['job_technical_skills']
        job_soft_skills = result['job_soft_skills']

        missing_keywords = analysis_results['keyword_analysis']['missing_keywords']
        missing_technical_keywords = [kw for kw in missing_keywords if kw in job_technical_skills]
        missing_soft_keywords = [kw for kw in missing_keywords if kw in job_soft_skills]

        if cv_selection == 'new' or not pre_uploaded_cvs:
            try:
                new_cv = CV(user_id=current_user.id, filename=cv_filename, content=cv_text, skills=','.join(cv_skills))
                db.session.add(new_cv)
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                flash(f"Error saving CV: {e}")

        try:
            new_job_desc = JobDescription(user_id=current_user.id, content=job_desc)
            db.session.add(new_job_desc)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            flash(f"Error saving job description: {e}")

        return render_template('results.html',
                              matches=matches,
                              match_percentage=match_percentage,
                              optimized_cv=optimized_cv,
                              cover_letter=cover_letter,
                              analysis_results=analysis_results,
                              weighted_match_percentage=weighted_match_percentage,
                              tech_match_percentage=tech_match_percentage,
                              soft_match_percentage=soft_match_percentage,
                              job_technical_skills=job_technical_skills,
                              job_soft_skills=job_soft_skills,
                              cv_text=cv_text,
                              missing_technical_keywords=missing_technical_keywords,
                              missing_soft_keywords=missing_soft_keywords,
                              cv_skill_freq=analysis_results['keyword_analysis']['cv_skill_freq'],
                              job_skill_freq=analysis_results['keyword_analysis']['job_skill_freq'])

    job_desc = session.get('job_desc', '')
    return render_template('analyze.html', pre_uploaded_cvs=pre_uploaded_cvs, can_upload_new=can_upload_new, max_cvs=max_cvs, job_desc=job_desc)

@app.route('/delete_cv/<int:cv_id>', methods=['POST'])
@login_required
def delete_cv(cv_id):
    cv = CV.query.filter_by(id=cv_id, user_id=current_user.id).first()
    if not cv:
        flash('CV not found.', 'danger')
        return redirect(request.referrer or url_for('index'))  

    try:
        db.session.delete(cv)
        db.session.commit()
        flash('CV deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting CV: {e}', 'danger')

    return redirect(request.referrer or url_for('index'))  

@app.route('/preview_cv/<int:cv_id>')
@login_required
def preview_cv(cv_id):
    cv = CV.query.filter_by(id=cv_id, user_id=current_user.id).first()
    if not cv:
        flash('CV not found.')
        return redirect(url_for('analyze'))
    return render_template('preview_cv.html', cv=cv)

@app.route('/job_search', methods=['GET', 'POST'])
@login_required
def job_search():
    if request.method == 'POST':
        query = request.form['query']
        location = request.form['location']
        jobs = job_search_agent.search_jobs(query, location)
        return render_template('job_search.html', jobs=jobs)
    return render_template('job_search.html', jobs=None)

@app.route('/chat', methods=['GET', 'POST'])
@login_required
def chat():
    if request.method == 'POST':
        user_input = request.form['user_input']
        response = rag.query(user_input)
        return render_template('chat.html', response=response, user_input=user_input)
    return render_template('chat.html', response=None, user_input=None)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000)