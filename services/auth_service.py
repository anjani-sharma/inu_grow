from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user
from models import User, db

class AuthService:
    @staticmethod
    def register_user(username, password):
        """Register a new user"""
        # Check if username already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            return False, "Username already taken"
        
        # Hash the password
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        
        # Create a new user
        new_user = User(username=username, password=hashed_password)
        
        try:
            db.session.add(new_user)
            db.session.commit()
            return True, "Registration successful! Please log in."
        except Exception as e:
            db.session.rollback()
            return False, f"Registration failed: {e}"
    
    @staticmethod
    def login_user_with_credentials(username, password):
        """Login a user with username and password"""
        user = User.query.filter_by(username=username).first()
        
        if not user or not check_password_hash(user.password, password):
            return False, "Invalid username or password"
        
        # Log the user in
        login_user(user)
        return True, "Login successful"
    
    @staticmethod
    def logout_current_user():
        """Logout the current user"""
        logout_user()
        return True, "Logout successful"