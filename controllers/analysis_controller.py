import os
from flask import render_template, request, redirect, url_for, flash, current_app, session, jsonify, send_file
from flask_login import current_user
from services.cv_service import CVService
from services.document_service import DocumentService
from services.analysis_service import AnalysisService
from controllers.resume_controller import CV_TEMPLATES

def analyze():
    """Handle CV analysis with job description"""
    # Get pre-uploaded CVs
    pre_uploaded_cvs = CVService.get_user_cvs(current_user.id)
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
        cv_id = None

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
            if not DocumentService.allowed_file(file.filename):
                flash('Invalid file type. Only PDF or DOCX allowed.')
                return redirect(request.url)

            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filepath)
            
            file_type = file.filename.rsplit('.', 1)[1].lower()
            cv_text = DocumentService.extract_text(filepath, file_type)

            if not cv_text:
                flash('Failed to extract text from the CV.')
                return redirect(request.url)
            cv_filename = file.filename
            save_cv = True
        else:
            selected_cv_id = request.form.get('pre_uploaded_cv', '')
            if not selected_cv_id:
                flash('Please select a pre-uploaded CV.')
                return redirect(request.url)
            selected_cv = CVService.get_cv_by_id(selected_cv_id, current_user.id)
            if not selected_cv:
                flash('Selected CV not found.')
                return redirect(request.url)
            cv_text = selected_cv.content
            cv_filename = selected_cv.filename
            cv_skills = selected_cv.skills_list()
            cv_id = selected_cv.id
            save_cv = False

        # Get analysis results
        results = AnalysisService.analyze_cv_job_match(
            cv_text=cv_text,
            job_desc=job_desc,
            user_id=current_user.id,
            cv_filename=cv_filename if save_cv else None,
            cv_skills=cv_skills,
            save_cv=save_cv
        )
        
        # If a CV was saved or used from existing, store the ID for template use
        if save_cv and 'cv_id' in results:
            cv_id = results['cv_id']
        
        if cv_id:
            results['cv_id'] = cv_id
            # Store in session for template previewing
            session['analyzed_cv_id'] = cv_id
        
        # Always store the optimized content
        session['optimized_cv'] = results['optimized_cv']
            
        return render_template('results.html', **results, templates=CV_TEMPLATES)

    job_desc = session.get('job_desc', '')
    return render_template('analyze.html', 
                          pre_uploaded_cvs=pre_uploaded_cvs, 
                          can_upload_new=can_upload_new, 
                          max_cvs=max_cvs, 
                          job_desc=job_desc)

def get_formatted_cv():
    """Get a CV formatted with a specific template"""
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
    
    data = request.json
    template_id = data.get('template', 'modern')
    
    # Try to get the optimized content directly from the request data
    optimized_content = data.get('optimized_content')
    
    # If not in request, try session
    if not optimized_content:
        optimized_content = session.get('optimized_cv', '')
    
    # If still no content, return error
    if not optimized_content:
        return jsonify({"error": "No optimized content found. Please analyze your CV again."}), 404
    
    # Try to get CV ID from request or session
    cv_id = data.get('cv_id') or session.get('analyzed_cv_id')
    
    if not cv_id or cv_id == 0:
        # Get the first available CV for the user as a fallback
        cvs = CVService.get_user_cvs(current_user.id)
        if not cvs:
            return jsonify({"error": "No CVs found for this user. Please upload a CV first."}), 404
            
        cv = cvs[0]
    else:
        # Get the CV model using the ID
        cv = CVService.get_cv_by_id(cv_id, current_user.id)
        if not cv:
            # Fallback to first CV
            cvs = CVService.get_user_cvs(current_user.id)
            if not cvs:
                return jsonify({"error": "No CVs found for this user. Please upload a CV first."}), 404
            cv = cvs[0]
    
    # Store this optimized content in session for later use
    session['optimized_cv'] = optimized_content
    
    # Generate formatted resume with template
    formatted_cv = CVService.format_optimized_cv(cv, optimized_content, template_id)
    
    return jsonify({
        'success': True,
        'formattedResume': formatted_cv,
        'downloadUrl': url_for('download_formatted_cv', template_id=template_id)
    })

def download_optimized_cv(content):
    """Generate and download an optimized CV (legacy format)"""
    return DocumentService.generate_pdf(content, 'optimized_cv.pdf')

def download_formatted_cv(template_id):
    """Download a template-formatted CV"""
    # Try to get CV ID from session
    cv_id = session.get('analyzed_cv_id')
    
    # Get the optimized content
    optimized_content = session.get('optimized_cv', '')
    
    if not optimized_content:
        flash('No optimized CV content found. Please analyze your CV again.', 'danger')
        return redirect(url_for('analyze'))
    
    # Get CV to use for formatting
    if not cv_id:
        # Use the first available CV as a fallback
        cvs = CVService.get_user_cvs(current_user.id)
        if not cvs:
            flash('No CVs found. Please upload a CV first.', 'danger')
            return redirect(url_for('analyze'))
        cv = cvs[0]
    else:
        # Get the CV model
        cv = CVService.get_cv_by_id(cv_id, current_user.id)
        if not cv:
            # Use the first available CV as a fallback
            cvs = CVService.get_user_cvs(current_user.id)
            if not cvs:
                flash('No CVs found. Please upload a CV first.', 'danger')
                return redirect(url_for('analyze'))
            cv = cvs[0]
    
    # Generate formatted CV with the selected template
    formatted_cv = CVService.format_optimized_cv(cv, optimized_content, template_id)
    
    # Convert to HTML and then PDF
    html_content = format_text_as_html(formatted_cv)
    
    # Create temp directory if it doesn't exist
    temp_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'temp')
    os.makedirs(temp_dir, exist_ok=True)
    
    # Generate PDF
    pdf_path = os.path.join(temp_dir, f'optimized_cv_{current_user.id}_{template_id}.pdf')
    DocumentService.html_to_pdf(html_content, pdf_path)
    
    return send_file(
        pdf_path,
        as_attachment=True,
        download_name=f'optimized_cv_{template_id}.pdf',
        mimetype='application/pdf'
    )

def download_cover_letter(content):
    """Generate and download a cover letter"""
    return DocumentService.generate_pdf(content, 'cover_letter.pdf')

# HTML formatter for CV text (copied from resume controller)
def format_text_as_html(text):
    """Convert plain text resume to HTML"""
    # Split the text into lines
    lines = text.split('\n')
    html = []
    
    # Add HTML header with styles
    html.append("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Optimized CV</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            margin: 0;
            padding: 20px;
            max-width: 800px;
            margin: 0 auto;
        }
        h1 {
            font-size: 24px;
            text-align: center;
            margin-top: 0;
            margin-bottom: 5px;
            color: #2c3e50;
        }
        .contact-info {
            text-align: center;
            margin-bottom: 20px;
            font-size: 14px;
            color: #555;
        }
        h2 {
            font-size: 16px;
            text-transform: uppercase;
            margin-top: 15px;
            margin-bottom: 10px;
            color: #2980b9;
            border-bottom: 1px solid #e0e0e0;
            padding-bottom: 5px;
        }
        p {
            margin-bottom: 10px;
        }
        ul {
            margin-left: 20px;
            margin-bottom: 10px;
            padding-left: 0;
        }
        ul li {
            margin-bottom: 5px;
            list-style-type: disc;
        }
        .skills-list {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            list-style-type: none;
            margin-left: 0;
        }
        .skills-list li {
            background-color: #f8f9fa;
            border-radius: 3px;
            padding: 2px 8px;
            font-size: 14px;
            display: inline-block;
        }
        @media print {
            body {
                padding: 0;
                font-size: 12px;
                line-height: 1.4;
            }
            h1 {
                font-size: 18px;
            }
            h2 {
                font-size: 14px;
            }
            .skills-list li {
                background-color: transparent;
                border: 1px solid #ddd;
                padding: 1px 6px;
                font-size: 12px;
            }
        }
    </style>
</head>
<body>""")
    
    inSkillsSection = False
    inList = False
    
    # Process the first line as the name (assuming it's the name)
    if lines:
        html.append(f"<h1>{lines[0]}</h1>")
    
    # Process the second line as contact info
    if len(lines) > 1:
        html.append(f'<div class="contact-info">{lines[1]}</div>')
    
    # Process the rest of the lines
    for i in range(2, len(lines)):
        line = lines[i].strip()
        
        # Skip empty lines
        if not line:
            if inList:
                html.append('</ul>')
                inList = False
            continue
        
        # Check if it's a section header
        if line.upper() == line and len(line) > 3:
            if inList:
                html.append('</ul>')
                inList = False
            
            # Section header
            html.append(f"<h2>{line}</h2>")
            
            # Check if we're entering the skills section
            inSkillsSection = 'SKILLS' in line
            continue
        
        # If we're in the skills section, format as bullet points
        if inSkillsSection:
            # Format skills with bullets
            skills = line.split('•')
            skills = [s.strip() for s in skills if s.strip()]
            
            if skills:
                if not inList:
                    html.append('<ul class="skills-list">')
                    inList = True
                
                for skill in skills:
                    html.append(f"<li>{skill}</li>")
        # If line starts with a bullet point or asterisk
        elif line.startswith('•') or line.startswith('*') or line.startswith('-'):
            if not inList:
                html.append('<ul>')
                inList = True
            
            # Remove the bullet point character and trim
            content = line[1:].strip()
            html.append(f"<li>{content}</li>")
        # Regular paragraph
        else:
            if inList:
                html.append('</ul>')
                inList = False
            
            html.append(f"<p>{line}</p>")
    
    # Close any open list
    if inList:
        html.append('</ul>')
    
    # Close HTML document
    html.append('</body></html>')
    
    return '\n'.join(html)