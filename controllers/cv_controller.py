import os
from flask import render_template, request, redirect, url_for, flash, current_app
from flask_login import current_user, login_required
from services.cv_service import CVService
from services.document_service import DocumentService

def upload_cv_dashboard():
    """Handle uploading a CV from the dashboard"""
    if 'cv_file' not in request.files:
        flash('No file part in request', 'danger')
        return redirect(url_for('index'))

    file = request.files['cv_file']
    if file.filename == '':
        flash('No file selected', 'danger')
        return redirect(url_for('index'))

    if not DocumentService.allowed_file(file.filename):
        flash('Invalid file type. Only PDF or DOCX allowed.', 'danger')
        return redirect(url_for('index'))

    # Check if user has reached their CV limit
    user_cvs = CVService.get_user_cvs(current_user.id)
    if len(user_cvs) >= 5:
        flash('You can only save up to 5 CVs.', 'warning')
        return redirect(url_for('index'))

    # Save the file
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], file.filename)
    file.save(filepath)
    
    # Process the CV
    cv, message = CVService.process_cv(file, current_user.id, filepath)
    
    flash(message, "success" if cv else "danger")
    return redirect(url_for('index'))

def delete_cv(cv_id):
    """Handle deleting a CV"""
    success, message = CVService.delete_cv(cv_id, current_user.id)
    
    flash(message, "success" if success else "danger")
    return redirect(request.referrer or url_for('index'))

def preview_cv(cv_id):
    """Preview a CV"""
    cv = CVService.get_cv_by_id(cv_id, current_user.id)
    
    if not cv:
        flash('CV not found.')
        return redirect(url_for('analyze'))
        
    return render_template('preview_cv.html', cv=cv)