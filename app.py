from flask import Flask
from flask_login import LoginManager
from flask_migrate import Migrate
import os
from models import db, User
from config.config import Config

# Import controllers
from controllers.auth_controller import register, login, logout
from controllers.cv_controller import upload_cv_dashboard, delete_cv, preview_cv
from controllers.analysis_controller import analyze, download_optimized_cv, download_cover_letter, get_formatted_cv, download_formatted_cv
from controllers.job_controller import job_search, job_description
from controllers.chat_controller import chat
from controllers.index_controller import index
from controllers.resume_controller import resume_builder, get_cv_data, generate_resume, download_resume, ai_edit_section

def create_app(config_object=Config):
    app = Flask(__name__)
    app.config.from_object(config_object)
    
    # Ensure upload folder exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Initialize database
    db.init_app(app)
    migrate = Migrate(app, db)
    
    # Initialize login manager
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Register routes
    
    # Index route
    app.route('/')(index)
    
    # Authentication routes
    app.route('/register', methods=['GET', 'POST'])(register)
    app.route('/login', methods=['GET', 'POST'])(login)
    app.route('/logout')(logout)
    
    # CV management routes
    app.route('/upload_cv_dashboard', methods=['POST'])(upload_cv_dashboard)
    app.route('/delete_cv/<int:cv_id>', methods=['POST'])(delete_cv)
    app.route('/preview_cv/<int:cv_id>')(preview_cv)
    
    # Analysis routes
    app.route('/analyze', methods=['GET', 'POST'])(analyze)
    app.route('/download_optimized_cv/<content>')(download_optimized_cv)
    app.route('/download_cover_letter/<content>')(download_cover_letter)
    app.route('/get_formatted_cv', methods=['POST'])(get_formatted_cv)
    app.route('/download_formatted_cv/<template_id>')(download_formatted_cv)
    
    # Job routes
    app.route('/job_search', methods=['GET', 'POST'])(job_search)
    app.route('/job/<int:job_id>')(job_description)
    
    # Chat route
    app.route('/chat', methods=['GET', 'POST'])(chat)
    
    # Resume builder routes
    app.route('/resume_builder')(resume_builder)
    app.route('/get_cv_data/<int:cv_id>')(get_cv_data)
    app.route('/generate_resume', methods=['POST'])(generate_resume)
    app.route('/download_resume/<int:cv_id>/<template_id>')(download_resume)
    app.route('/ai_edit_section', methods=['POST'])(ai_edit_section)
    
    return app

# Create the app instance
app = create_app()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000)