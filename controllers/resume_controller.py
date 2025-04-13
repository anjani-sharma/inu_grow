import os
import json
from flask import render_template, request, redirect, url_for, flash, current_app, jsonify, send_file
from flask_login import current_user, login_required
from services.cv_service import CVService
from services.document_service import DocumentService
from services.llm_service import LLMService

# CV Templates for ATS-friendly resume formats
CV_TEMPLATES = {
    'executive': {
        'name': 'Executive',
        'description': 'Leadership-oriented format highlighting summary, skills, and achievements'
    },
    'professional': {
        'name': 'Professional',
        'description': 'A traditional format focusing on experience and skills'
    },
    'technical': {
        'name': 'Technical Focus',
        'description': 'Emphasizes technical skills and projects'
     },    
    'modern': {
        'name': 'Modern Clean',
        'description': 'A clean, minimalist template with good ATS compatibility'
    }
}

def resume_builder():
    """Show the resume builder page"""
    # Get user's CVs
    cvs = CVService.get_user_cvs(current_user.id) if current_user.is_authenticated else []
    
    return render_template('resume_builder.html', 
                          templates=CV_TEMPLATES,
                          cvs=cvs)

def get_cv_data(cv_id):
    """Get parsed CV data for the resume builder"""
    cv = CVService.get_cv_by_id(cv_id, current_user.id)
    
    if not cv:
        return jsonify({'error': 'CV not found'}), 404
    
    # Get parsed data using existing CV service
    parsed_data = CVService.get_parsed_data_for_resume(cv)
    
    return jsonify({
        'success': True,
        'parsedData': parsed_data
    })

def generate_resume():
    """Generate a formatted resume based on template and customizations"""
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
    
    data = request.json
    cv_id = data.get('cv_id')
    
    if not cv_id:
        return jsonify({"error": "No CV ID provided"}), 400
    
    cv = CVService.get_cv_by_id(cv_id, current_user.id)
    if not cv:
        return jsonify({"error": "CV not found"}), 404
    
    template_id = data.get('template', 'modern')
    customizations = {
        'custom_summary': data.get('customSummary', ''),
        'highlighted_skills': data.get('highlightedSkills', []),
        'excluded_sections': data.get('excludedSections', [])
    }
    
    # Get the formatted resume
    formatted_resume = CVService.generate_formatted_resume(cv, template_id, customizations)
    
    # Store it temporarily
    temp_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'temp')
    os.makedirs(temp_dir, exist_ok=True)
    
    formatted_text_file = os.path.join(temp_dir, f'resume_{current_user.id}_{cv_id}_{template_id}.txt')
    with open(formatted_text_file, 'w') as f:
        f.write(formatted_resume)
    
    return jsonify({
        'success': True,
        'formattedResume': formatted_resume,
        'downloadUrl': url_for('download_resume', cv_id=cv_id, template_id=template_id)
    })

def download_resume(cv_id, template_id):
    """Download the generated resume as PDF"""
    cv = CVService.get_cv_by_id(cv_id, current_user.id)
    if not cv:
        return jsonify({'error': 'CV not found'}), 404
    
    temp_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'temp')
    text_file = os.path.join(temp_dir, f'resume_{current_user.id}_{cv_id}_{template_id}.txt')
    
    try:
        with open(text_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Format HTML and convert to PDF
        html_content = format_text_as_html(content)
        pdf_path = os.path.join(temp_dir, f'resume_{current_user.id}_{cv_id}_{template_id}.pdf')
        
        DocumentService.html_to_pdf(html_content, pdf_path)
        
        return send_file(
            pdf_path,
            as_attachment=True,
            download_name=f'resume_{template_id}.pdf',
            mimetype='application/pdf'
        )
    except Exception as e:
        return jsonify({'error': f'PDF generation failed: {str(e)}'}), 500

def ai_edit_section():
    """Use AI to improve a resume section"""
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
    
    data = request.json
    section = data.get('section')
    content = data.get('content')
    goal = data.get('goal', 'Make it more professional and impactful')
    
    # Use existing LLM service
    prompt = f"""
    You are a resume assistant. Improve the following {section} content.
    Make it concise, impactful, and ATS-optimized.
    
    Content:
    {content}
    
    Goal: {goal}
    """
    
    response = LLMService.invoke(prompt)
    result = response.content
    
    return jsonify({'updated': result})

# HTML formatter for resume text
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
    <title>Resume</title>
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