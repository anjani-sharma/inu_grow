from flask import render_template, request, redirect, url_for, flash, session
from flask_login import logout_user, current_user
from services.auth_service import AuthService

def register():
    """Handle user registration"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        success, message = AuthService.register_user(username, password)
        flash(message)
        
        if success:
            return redirect(url_for('login'))
    
    return render_template('register.html')

def login():
    """Handle user login"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        success, message = AuthService.login_user_with_credentials(username, password)
        
        if not success:
            flash(message)
            return render_template('login.html')
        
        return redirect(url_for('index'))
    
    return render_template('login.html')

def logout():
    """Handle user logout"""
    session.clear()
    logout_user()
    flash("You have been logged out", "info")
    return redirect(url_for('index'))