import os
from models import CV, db
from services.document_service import DocumentService
from services.llm_service import LLMService
from services.rag_service import RAGService
from utils.llm_cv_parser import LLMCVParser
import json

class CVService:
    @staticmethod
    def process_cv(file, user_id, filepath):
        """Process a CV file and save it to the database"""
        file_type = file.filename.rsplit('.', 1)[1].lower()

        try:
            if file_type == 'pdf':
                cv_text, links = DocumentService.extract_text_and_links_from_pdf(filepath)
            else:
                cv_text = DocumentService.extract_text(filepath, file_type)
                links = []

            cv_data = CVService.parse_cv(cv_text=cv_text, extra_links=links)

            if not cv_text:
                return None, "Failed to extract text from CV"
        except Exception as e:
            print(f"Error directly parsing CV: {e}")
            cv_text = DocumentService.extract_text(filepath, file_type)
            if not cv_text:
                return None, "Failed to extract text from CV"
            cv_data = CVService.parse_cv(cv_text=cv_text)
            links = []

        existing_cv = CV.query.filter_by(user_id=user_id, content=cv_text).first()
        if existing_cv:
            return None, "This CV has already been uploaded"

        existing_cv_by_name = CV.query.filter_by(user_id=user_id, filename=file.filename).first()
        if existing_cv_by_name:
            return None, "You have already uploaded a CV with this filename"

        new_cv = CV(
            user_id=user_id,
            filename=file.filename,
            content=cv_text,
            skills=",".join(cv_data["enhanced_skills"]),
            summary=cv_data["parsed_data"].get("summary", ""),
            hyperlinks=json.dumps(links)  # Store hyperlinks in the database
        )

        db.session.add(new_cv)
        db.session.commit()

        rag_service = RAGService.get_instance()
        rag_service.add_document(cv_text, doc_id=str(new_cv.id))

        return new_cv, "CV uploaded and parsed successfully"

    
    @staticmethod
    def parse_cv(cv_text=None, cv_path=None, extra_links=None):
        """
        Parse a CV text or file to extract structured data
        
        Args:
            cv_text: The text content of the CV (optional)
            cv_path: The path to the CV file (optional)

        Pure LLM-based CV parsing.
        Extracts structured information from CV text or file path using a single LLM call.
            
        Note:
            At least one of cv_text or cv_path must be provided
        """
       
        if not cv_text and not cv_path:
            raise ValueError("cv_text or cv_path must be provided")

        if not cv_text and cv_path:
            from services.document_service import DocumentService
            file_type = cv_path.rsplit('.', 1)[1].lower()
            if file_type == 'pdf':
                cv_text, extracted_links = DocumentService.extract_text_and_links_from_pdf(cv_path)
            else:
                cv_text = DocumentService.extract_text(cv_path, file_type)
                extracted_links = []
        else:
            extracted_links = []

        if extra_links:
            extracted_links += extra_links

        parser = LLMCVParser(cv_text=cv_text, extra_links=extracted_links)
        parsed_data = parser.parse()

        enhanced_skills = parsed_data.get("skills", []) + parsed_data.get("technologies", [])

        return {
            "parsed_data": parsed_data,
            "enhanced_skills": list(set([s.lower() for s in enhanced_skills if isinstance(s, str)]))
        }
    
    @staticmethod
    def get_cv_by_id(cv_id, user_id):
        """Get a CV by ID and validate user ownership"""
        return CV.query.filter_by(id=cv_id, user_id=user_id).first()
    
    @staticmethod
    def delete_cv(cv_id, user_id):
        """Delete a CV by ID if it belongs to the user"""
        cv = CVService.get_cv_by_id(cv_id, user_id)
        if not cv:
            return False, "CV not found"
        
        try:
            # 1. Remove from RAG index if applicable
            try:
                rag_service = RAGService.get_instance()
                rag_service.delete_document(str(cv.id))
            except Exception as e:
                print(f"[RAG Cleanup Warning] Could not delete RAG index for CV {cv.id}: {e}")

            # 2. Remove from DB
            db.session.delete(cv)
            db.session.commit()
            return True, "CV deleted successfully"

        except Exception as e:
            db.session.rollback()
            return False, f"Error deleting CV: {e}"
    
    @staticmethod
    def get_user_cvs(user_id):
        """Get all CVs belonging to a user"""
        return CV.query.filter_by(user_id=user_id).all()

    # Resume builder functionality
    @staticmethod
    def get_parsed_data_for_resume(cv, extra_links=None):
        extra_links = extra_links or []
        parser = LLMCVParser(cv_text=cv.content, extra_links=extra_links)
        parsed_data = parser.parse()

        linkedin_link = next((l for l in extra_links if "linkedin.com/in/" in l.lower()), "")
        github_link = next((l for l in extra_links if "github.com/" in l.lower() and len(l.strip('/').split('/')) > 3), "")
        website_link = next((l for l in extra_links if any(kw in l.lower() for kw in ["portfolio", "mywebsite", "about", "dev"])), "")

        skills_list = parsed_data.get('skills', []) + parsed_data.get('technologies', [])
        skills_list = list(set([s.strip() for s in skills_list if isinstance(s, str)]))

        resume_data = {
            'contact_info': {
                'name': parsed_data.get('name', ''),
                'email': parsed_data.get('email', ''),
                'phone': parsed_data.get('phone', ''),
                'linkedin': linkedin_link or parsed_data.get('linkedin', ''),
                'github': github_link or parsed_data.get('github', ''),
                'website': website_link or parsed_data.get('website', '')
            },
            'summary': cv.summary or parsed_data.get('summary', ''),
            'skills': skills_list,
            'experience': parsed_data.get('work_experience', []),
            'education': parsed_data.get('education', []),
            'projects': parsed_data.get('projects', []),
            'certifications': parsed_data.get('certifications', []),
            'languages': parsed_data.get('languages', []),
            'technologies': parsed_data.get('technologies', [])
        }

        print(f"[DEBUG] Resume data for CV {cv.id}:")
        print(json.dumps(resume_data, indent=2))

        return resume_data


    
    @staticmethod
    def generate_formatted_resume(cv, template_id, customizations):
        """
        Generate a formatted resume based on CV data and template
        """
        # Get the parsed CV data
        extra_links = json.loads(cv.hyperlinks or "[]")
        parsed_data = CVService.get_parsed_data_for_resume(cv, extra_links=extra_links)

        # default to 'executive' if none provided
        template_id = template_id or 'executive'
        
        # Generate formatted resume based on template
        if template_id == 'modern':
            return CVService.generate_modern_template(parsed_data, customizations)
        elif template_id == 'professional':
            return CVService.generate_professional_template(parsed_data, customizations)
        elif template_id == 'technical':
            return CVService.generate_technical_template(parsed_data, customizations)
        else:
            # Default to executive template
            return CVService.generate_executive_template(parsed_data)
        
    
    @staticmethod
    def generate_executive_template(parsed_data):
        contact_info = parsed_data.get('contact_info', {})
        summary = parsed_data.get('summary', '')
        experience = parsed_data.get('experience', [])
        education = parsed_data.get('education', [])
        skills = parsed_data.get('skills', [])
        certifications = parsed_data.get('certifications', [])
        projects = parsed_data.get('projects', [])

        content = []
        content.append(contact_info.get('name', 'YOUR NAME').upper())
        content.append("Senior Data Science & AI Leader | Generative AI, Machine Learning, Python, People leader")
        content.append(f"Ph# {contact_info.get('phone', '')}, email: {contact_info.get('email', '')}, LinkedIn: {contact_info.get('linkedin', '')}   Project Repository: {contact_info.get('github', '')}")
        content.append("")

        content.append("Professional Summary")
        content.append(summary)
        content.append("")

        content.append("Core Competencies")
        for skill in skills:
            content.append(f"• {skill}")
        content.append("")

        content.append("Professional Experience")
        for exp in experience:
            content.append(exp.get('company', ''))
            content.append(f"{exp.get('title', '')}                                                                  {exp.get('start_date', '')} – {exp.get('end_date', '')}")
            for achievement in exp.get('achievements', []):
                content.append(f"• {achievement}")
            content.append("")

        content.append("Projects")
        for proj in projects:
            content.append(f"• {proj.get('name', '')}: {proj.get('description', '')}")
            content.append("")

        content.append("Skills")
        for skill in skills:
            content.append(f"• {skill}")
        content.append("")

        content.append("Education")
        for edu in education:
            content.append(edu.get('degree', ''))
            content.append(edu.get('institution', ''))
            content.append(f"{edu.get('start_date', '')} – {edu.get('end_date', '')}")
            content.append("")

        content.append("Certifications")
        for cert in certifications:
            content.append(f"• {cert}")

        return "\n".join(content)


            
    @staticmethod
    def generate_modern_template(parsed_data, customizations):
        """Generate a resume using the Modern template"""
        contact_info = parsed_data.get('contact_info', {})
        summary = parsed_data.get('summary', '')
        experience = parsed_data.get('experience', [])
        education = parsed_data.get('education', [])
        skills = parsed_data.get('skills', [])
        projects = parsed_data.get('projects', [])
        certifications = parsed_data.get('certifications', [])
        
        # Apply customizations
        excluded_sections = customizations.get('excluded_sections', [])
        custom_summary = customizations.get('custom_summary', '')
        highlighted_skills = customizations.get('highlighted_skills', [])
        
        content = []
        
        # Header with name and contact details
        content.append(f"{contact_info.get('name', 'YOUR NAME')}")
        contact_line = []
        if contact_info.get('email'):
            contact_line.append(contact_info['email'])
        if contact_info.get('phone'):
            contact_line.append(contact_info['phone'])
        if contact_info.get('linkedin'):
            contact_line.append(contact_info['linkedin'])
        
        content.append(" | ".join(contact_line))
        content.append("")
        
        # Professional Summary
        if 'summary' not in excluded_sections:
            content.append("PROFESSIONAL SUMMARY")
            content.append(custom_summary if custom_summary else summary or "Experienced professional with a proven track record of success...")
            content.append("")
        
        # Skills
        if 'skills' not in excluded_sections:
            content.append("SKILLS")
            skills_to_show = list(set(highlighted_skills + skills)) if highlighted_skills else skills
            content.append(" • ".join(skills_to_show))
            content.append("")
        
        # Experience
        if 'experience' not in excluded_sections and experience:
            content.append("PROFESSIONAL EXPERIENCE")
            for exp in experience:
                if isinstance(exp, str):
                    content.append(exp)
                elif isinstance(exp, dict):
                    # Format dictionary experience entries
                    job_title = exp.get('title', '')
                    company = exp.get('company', '')
                    dates = f"{exp.get('start_date', '')} - {exp.get('end_date', '')}"
                    
                    if job_title and company:
                        content.append(f"{job_title} at {company}")
                    elif job_title:
                        content.append(job_title)
                        
                    if dates.strip() != '-':
                        content.append(dates)
                        
                    for achievement in exp.get('achievements', []):
                        content.append(f"• {achievement}")
                        
                content.append("")
        
        # Education
        if 'education' not in excluded_sections and education:
            content.append("EDUCATION")
            for edu in education:
                if isinstance(edu, str):
                    content.append(edu)
                elif isinstance(edu, dict):
                    # Format dictionary education entries
                    degree = edu.get('degree', '')
                    institution = edu.get('institution', '')
                    dates = f"{edu.get('start_date', '')} - {edu.get('end_date', '')}"
                    
                    if degree and institution:
                        content.append(f"{degree}, {institution}")
                    elif degree:
                        content.append(degree)
                    elif institution:
                        content.append(institution)
                        
                    if dates.strip() != '-':
                        content.append(dates)
                        
                content.append("")
        
        # Projects
        if 'projects' not in excluded_sections and projects:
            content.append("PROJECTS")
            for project in projects:
                if isinstance(project, str):
                    content.append(project)
                elif isinstance(project, dict):
                    # Format dictionary project entries
                    name = project.get('name', '')
                    content.append(name)
                    description = project.get('description', '')
                    if description:
                        content.append(description)
                        
                content.append("")
        
        # Certifications
        if 'certifications' not in excluded_sections and certifications:
            content.append("CERTIFICATIONS")
            for cert in certifications:
                if isinstance(cert, str):
                    content.append(cert)
                elif isinstance(cert, dict):
                    # Format dictionary certification entries
                    name = cert.get('name', '')
                    issuer = cert.get('issuer', '')
                    date = cert.get('date', '')
                    
                    if name:
                        content.append(name)
                    if issuer:
                        content.append(f"Issued by: {issuer}")
                    if date:
                        content.append(date)
                        
                content.append("")
        
        return "\n".join(content)
    
    @staticmethod
    def generate_professional_template(parsed_data, customizations):
        """Generate a resume using the Professional template"""
        contact_info = parsed_data.get('contact_info', {})
        summary = parsed_data.get('summary', '')
        experience = parsed_data.get('experience', [])
        education = parsed_data.get('education', [])
        skills = parsed_data.get('skills', [])
        projects = parsed_data.get('projects', [])
        certifications = parsed_data.get('certifications', [])
        
        # Apply customizations
        excluded_sections = customizations.get('excluded_sections', [])
        custom_summary = customizations.get('custom_summary', '')
        highlighted_skills = customizations.get('highlighted_skills', [])
        
        content = []
        
        # Header with name and contact details
        content.append(f"{contact_info.get('name', 'YOUR NAME')}")
        if contact_info.get('email'):
            content.append(f"Email: {contact_info['email']}")
        if contact_info.get('phone'):
            content.append(f"Phone: {contact_info['phone']}")
        if contact_info.get('linkedin'):
            content.append(f"LinkedIn: {contact_info['linkedin']}")
        content.append("")
        
        # Professional Summary
        if 'summary' not in excluded_sections:
            content.append("SUMMARY")
            content.append("-------")
            content.append(custom_summary if custom_summary else summary or "Experienced professional with a proven track record of success...")
            content.append("")
        
        # Experience
        if 'experience' not in excluded_sections and experience:
            content.append("PROFESSIONAL EXPERIENCE")
            content.append("----------------------")
            for exp in experience:
                if isinstance(exp, str):
                    content.append(exp)
                elif isinstance(exp, dict):
                    # Format dictionary experience entries
                    job_title = exp.get('title', '')
                    company = exp.get('company', '')
                    dates = f"{exp.get('start_date', '')} - {exp.get('end_date', '')}"
                    
                    if job_title and company:
                        content.append(f"{job_title} at {company}")
                    elif job_title:
                        content.append(job_title)
                        
                    if dates.strip() != '-':
                        content.append(dates)
                        
                    for achievement in exp.get('achievements', []):
                        content.append(f"• {achievement}")
                        
                content.append("")
        
        # Education
        if 'education' not in excluded_sections and education:
            content.append("EDUCATION")
            content.append("---------")
            for edu in education:
                if isinstance(edu, str):
                    content.append(edu)
                elif isinstance(edu, dict):
                    # Format dictionary education entries
                    degree = edu.get('degree', '')
                    institution = edu.get('institution', '')
                    dates = f"{edu.get('start_date', '')} - {edu.get('end_date', '')}"
                    
                    if degree and institution:
                        content.append(f"{degree}, {institution}")
                    elif degree:
                        content.append(degree)
                    elif institution:
                        content.append(institution)
                        
                    if dates.strip() != '-':
                        content.append(dates)
                        
                content.append("")
        
        # Skills
        if 'skills' not in excluded_sections and skills:
            content.append("SKILLS")
            content.append("------")
            skills_to_show = list(set(highlighted_skills + skills)) if highlighted_skills else skills
            content.append(" • ".join(skills_to_show))
            content.append("")
        
        # Projects
        if 'projects' not in excluded_sections and projects:
            content.append("PROJECTS")
            content.append("--------")
            for project in projects:
                if isinstance(project, str):
                    content.append(project)
                elif isinstance(project, dict):
                    # Format dictionary project entries
                    name = project.get('name', '')
                    content.append(name)
                    description = project.get('description', '')
                    if description:
                        content.append(description)
                        
                content.append("")
        
        # Certifications
        if 'certifications' not in excluded_sections and certifications:
            content.append("CERTIFICATIONS")
            content.append("--------------")
            for cert in certifications:
                if isinstance(cert, str):
                    content.append(cert)
                elif isinstance(cert, dict):
                    # Format dictionary certification entries
                    name = cert.get('name', '')
                    issuer = cert.get('issuer', '')
                    date = cert.get('date', '')
                    
                    if name:
                        content.append(name)
                    if issuer:
                        content.append(f"Issued by: {issuer}")
                    if date:
                        content.append(date)
                        
                content.append("")
        
        return "\n".join(content)
    
    @staticmethod
    def format_optimized_cv(cv, optimized_content, template_id):
        """
        Format an optimized CV using template styles
        Takes the CV object, optimized content, and template ID
        """
        # Parse the optimized content to extract key information
        # We'll need to infer some structure from the optimized content
        lines = optimized_content.split('\n')
        first_line = lines[0] if lines else ""
        
        # Use the CV's parsed data, but replace content with optimized content
        parsed_data = CVService.get_parsed_data_for_resume(cv)
        
        # Override with content from optimized CV
        parsed_data['optimized_content'] = optimized_content
        
        # Simple customizations for the template formatting
        customizations = {
            'custom_summary': '',  # We'll extract this from optimized content
            'highlighted_skills': parsed_data.get('skills', []),
            'excluded_sections': []
        }
        
        # Apply template formatting
        if template_id == 'modern':
            return CVService._format_optimized_cv_modern(parsed_data, customizations)
        elif template_id == 'professional':
            return CVService._format_optimized_cv_professional(parsed_data, customizations)
        elif template_id == 'technical':
            return CVService._format_optimized_cv_technical(parsed_data, customizations)
        else:
            # Default to modern template
            return CVService._format_optimized_cv_modern(parsed_data, customizations)
    
    @staticmethod
    def _format_optimized_cv_modern(parsed_data, customizations):
        """Format optimized CV with Modern template"""
        contact_info = parsed_data.get('contact_info', {})
        skills = parsed_data.get('skills', [])
        optimized_content = parsed_data.get('optimized_content', '')
        
        # Extract sections from optimized content
        sections = CVService._extract_sections_from_optimized(optimized_content)
        
        content = []
        
        # Header with name and contact details
        content.append(f"{contact_info.get('name', 'YOUR NAME')}")
        contact_line = []
        if contact_info.get('email'):
            contact_line.append(contact_info['email'])
        if contact_info.get('phone'):
            contact_line.append(contact_info['phone'])
        if contact_info.get('linkedin'):
            contact_line.append(contact_info['linkedin'])
        
        content.append(" | ".join(contact_line))
        content.append("")
        
        # Process each section with proper formatting
        for section_name, section_content in sections.items():
            # Add section header
            content.append(section_name.upper())
            
            if section_name.upper() == "SKILLS" or "SKILL" in section_name.upper():
                # For skills section, format as bullet points
                if skills:
                    content.append(" • ".join(skills))
                else:
                    # Try to extract skills from the content
                    skill_items = []
                    
                    # Look for list-like items in the content
                    for line in section_content.split('\n'):
                        line = line.strip()
                        if line.startswith('•') or line.startswith('-') or line.startswith('*'):
                            # Remove the bullet and add to skills
                            skill = line[1:].strip()
                            if skill:
                                skill_items.append(skill)
                        elif ',' in line:
                            # Split by commas
                            for skill in line.split(','):
                                skill = skill.strip()
                                if skill:
                                    skill_items.append(skill)
                    
                    # If we found skills, format them with bullets
                    if skill_items:
                        content.append(" • ".join(skill_items))
                    else:
                        # Just use the content as is
                        content.append(section_content)
            else:
                # Process regular content with proper formatting
                formatted_lines = []
                
                # Look for bullet points and format them
                in_bullet_list = False
                for line in section_content.split('\n'):
                    line = line.strip()
                    if not line:
                        continue
                        
                    # Check for bullet points
                    if line.startswith('•') or line.startswith('-') or line.startswith('*'):
                        formatted_lines.append(line)  # Keep the bullet point
                    elif line[0].isdigit() and '.' in line[:3]:
                        # Numbered list item (e.g., "1. Item")
                        formatted_lines.append(line)
                    else:
                        # Regular paragraph
                        formatted_lines.append(line)
                
                # Add the formatted content
                if formatted_lines:
                    content.append('\n'.join(formatted_lines))
                else:
                    content.append(section_content)
            
            # Add spacing between sections
            content.append("")
        
        return "\n".join(content)
    
    @staticmethod
    def _format_optimized_cv_professional(parsed_data, customizations):
        """Format optimized CV with Professional template"""
        contact_info = parsed_data.get('contact_info', {})
        skills = parsed_data.get('skills', [])
        optimized_content = parsed_data.get('optimized_content', '')
        
        # Extract sections from optimized content
        sections = CVService._extract_sections_from_optimized(optimized_content)
        
        content = []
        
        # Header with name and contact details
        content.append(f"{contact_info.get('name', 'YOUR NAME')}")
        if contact_info.get('email'):
            content.append(f"Email: {contact_info['email']}")
        if contact_info.get('phone'):
            content.append(f"Phone: {contact_info['phone']}")
        if contact_info.get('linkedin'):
            content.append(f"LinkedIn: {contact_info['linkedin']}")
        content.append("")
        
        # Process each section with proper formatting
        for section_name, section_content in sections.items():
            # Add section header with underline
            content.append(section_name.upper())
            content.append("-" * len(section_name))
            
            if section_name.upper() == "SKILLS" or "SKILL" in section_name.upper():
                # For skills section, format as bullet points
                if skills:
                    content.append(" • ".join(skills))
                else:
                    # Try to extract skills from the content
                    skill_items = []
                    
                    # Look for list-like items in the content
                    for line in section_content.split('\n'):
                        line = line.strip()
                        if line.startswith('•') or line.startswith('-') or line.startswith('*'):
                            # Remove the bullet and add to skills
                            skill = line[1:].strip()
                            if skill:
                                skill_items.append(skill)
                        elif ',' in line:
                            # Split by commas
                            for skill in line.split(','):
                                skill = skill.strip()
                                if skill:
                                    skill_items.append(skill)
                    
                    # If we found skills, format them with bullets
                    if skill_items:
                        content.append(" • ".join(skill_items))
                    else:
                        # Just use the content as is
                        content.append(section_content)
            else:
                # Process regular content with proper formatting
                formatted_lines = []
                
                # Look for bullet points and format them
                for line in section_content.split('\n'):
                    line = line.strip()
                    if not line:
                        continue
                        
                    # Check for bullet points
                    if line.startswith('•') or line.startswith('-') or line.startswith('*'):
                        formatted_lines.append(line)  # Keep the bullet point
                    elif line[0].isdigit() and '.' in line[:3]:
                        # Numbered list item (e.g., "1. Item")
                        formatted_lines.append(line)
                    else:
                        # Regular paragraph
                        formatted_lines.append(line)
                
                # Add the formatted content
                if formatted_lines:
                    content.append('\n'.join(formatted_lines))
                else:
                    content.append(section_content)
            
            # Add spacing between sections
            content.append("")
        
        return "\n".join(content)
    
    @staticmethod
    def _format_optimized_cv_technical(parsed_data, customizations):
        """Format optimized CV with Technical template"""
        contact_info = parsed_data.get('contact_info', {})
        skills = parsed_data.get('skills', [])
        optimized_content = parsed_data.get('optimized_content', '')
        
        # Extract sections from optimized content
        sections = CVService._extract_sections_from_optimized(optimized_content)
        
        content = []
        
        # Header with name and contact details
        content.append(f"{contact_info.get('name', 'YOUR NAME')}")
        contact_line = []
        if contact_info.get('email'):
            contact_line.append(contact_info['email'])
        if contact_info.get('phone'):
            contact_line.append(contact_info['phone'])
        if contact_info.get('linkedin'):
            contact_line.append(contact_info['linkedin'])
        
        content.append(" | ".join(contact_line))
        content.append("")
        
        # In technical template, skills come first
        if "SKILLS" in [s.upper() for s in sections.keys()]:
            content.append("TECHNICAL SKILLS")
            content.append("===============")
            
            if skills:
                # Group skills by category if possible
                skill_categories = {
                    'Programming Languages': ['Python', 'Java', 'JavaScript', 'C++', 'C#', 'Go', 'Ruby'],
                    'Web Technologies': ['HTML', 'CSS', 'React', 'Angular', 'Vue', 'Node.js', 'Express'],
                    'Databases': ['SQL', 'MongoDB', 'PostgreSQL', 'MySQL', 'Redis', 'Firebase'],
                    'Cloud & DevOps': ['AWS', 'Azure', 'GCP', 'Docker', 'Kubernetes', 'CI/CD', 'Git'],
                    'Data Science': ['Machine Learning', 'TensorFlow', 'PyTorch', 'Data Analysis', 'NLP']
                }
                
                # Try to categorize skills
                has_categorized = False
                for category, category_skills in skill_categories.items():
                    matched_skills = [skill for skill in skills if skill in category_skills]
                    if matched_skills:
                        has_categorized = True
                        content.append(f"{category}: {', '.join(matched_skills)}")
                
                # Add uncategorized skills
                if not has_categorized:
                    content.append(", ".join(skills))
                else:
                    # Add uncategorized skills
                    categorized = [skill for category_skills in skill_categories.values() 
                                  for skill in category_skills]
                    uncategorized = [skill for skill in skills if skill not in categorized]
                    if uncategorized:
                        content.append(f"Other: {', '.join(uncategorized)}")
            else:
                # Use content from optimized CV
                for section_name, section_content in sections.items():
                    if section_name.upper() == "SKILLS":
                        content.append(section_content)
                        break
            
            content.append("")
        
        # Add remaining sections
        for section_name, section_content in sections.items():
            if section_name.upper() != "SKILLS":  # Skip skills as we've handled it
                content.append(section_name.upper())
                content.append("=" * len(section_name))
                content.append(section_content)
                content.append("")
        
        return "\n".join(content)
    
    @staticmethod
    def _extract_sections_from_optimized(optimized_content):
        """Extract sections from the optimized content"""
        lines = optimized_content.split('\n')
        sections = {}
        
        # First pass: Find sections by looking for uppercase headers
        section_markers = []
        for i, line in enumerate(lines):
            # Look for all-caps section headers that aren't too long
            if (line.upper() == line and len(line) > 3 and len(line.split()) <= 4 and 
                not line.strip().startswith('-') and not line.strip().startswith('=')):
                section_markers.append((i, line))
        
        # If we didn't find any sections, try a more lenient approach (looking for common section names)
        if not section_markers:
            common_sections = ["SUMMARY", "EXPERIENCE", "EDUCATION", "SKILLS", "PROJECTS", "CERTIFICATIONS"]
            for i, line in enumerate(lines):
                for section in common_sections:
                    if section in line.upper() and len(line) < 30:  # Not too long
                        section_markers.append((i, section))
                        break
        
        # If we still don't have sections, create some basic ones
        if not section_markers:
            # Extract the first paragraph (after potential header) as summary
            summary_text = ""
            start_index = 2  # Skip potential name and contact info
            for i in range(start_index, min(10, len(lines))):
                if lines[i].strip():
                    summary_text += lines[i] + "\n"
                elif summary_text:  # End of paragraph
                    break
            
            if summary_text:
                sections["SUMMARY"] = summary_text
            
            # Rest of content as experience
            rest_content = "\n".join(lines[start_index + len(summary_text.split('\n')):])
            if rest_content.strip():
                sections["EXPERIENCE"] = rest_content
                
            return sections
        
        # Process sections based on markers
        for i in range(len(section_markers)):
            section_name = section_markers[i][1]
            start_idx = section_markers[i][0] + 1  # Start after header
            
            # End is either next section or end of file
            end_idx = section_markers[i+1][0] if i < len(section_markers) - 1 else len(lines)
            
            # Get section content
            section_content = '\n'.join(lines[start_idx:end_idx]).strip()
            sections[section_name] = section_content
        
        # Check if we have the basic sections, if not try to infer them
        if "SKILLS" not in sections and "SKILL" not in sections:
            # Try to identify skills from the text
            skills_text = ""
            for section_name, content in sections.items():
                if any(keyword in section_name.upper() for keyword in ["TECHNICAL", "COMPETENC", "PROFICIEN"]):
                    skills_text = content
                    sections["SKILLS"] = content
                    break
        
        # Make sure we have a sensible set of sections
        if not sections:
            # Fallback: split the content into chunks and label as sections
            chunk_size = max(5, len(lines) // 4)  # Divide into 4 parts or 5 lines, whichever is larger
            basic_sections = ["SUMMARY", "EXPERIENCE", "EDUCATION", "SKILLS"]
            
            for i, section_name in enumerate(basic_sections):
                start = i * chunk_size
                end = min((i + 1) * chunk_size, len(lines))
                if start < len(lines):
                    content = '\n'.join(lines[start:end]).strip()
                    if content:
                        sections[section_name] = content
        
        return sections
        
    @staticmethod
    def generate_technical_template(parsed_data, customizations):
        """Generate a resume using the Technical template"""
        contact_info = parsed_data.get('contact_info', {})
        summary = parsed_data.get('summary', '')
        experience = parsed_data.get('experience', [])
        education = parsed_data.get('education', [])
        skills = parsed_data.get('skills', [])
        projects = parsed_data.get('projects', [])
        certifications = parsed_data.get('certifications', [])
        
        # Apply customizations
        excluded_sections = customizations.get('excluded_sections', [])
        custom_summary = customizations.get('custom_summary', '')
        highlighted_skills = customizations.get('highlighted_skills', [])
        
        content = []
        
        # Header with name and contact details
        content.append(f"{contact_info.get('name', 'YOUR NAME')}")
        contact_line = []
        if contact_info.get('email'):
            contact_line.append(contact_info['email'])
        if contact_info.get('phone'):
            contact_line.append(contact_info['phone'])
        if contact_info.get('linkedin'):
            contact_line.append(contact_info['linkedin'])
        
        content.append(" | ".join(contact_line))
        content.append("")
        
        # Skills (moved to top for technical focus)
        if 'skills' not in excluded_sections and skills:
            content.append("TECHNICAL SKILLS")
            content.append("===============")
            
            # Group skills by category
            skill_categories = {
                'Programming Languages': ['Python', 'Java', 'JavaScript', 'C++', 'C#', 'Go', 'Ruby'],
                'Web Technologies': ['HTML', 'CSS', 'React', 'Angular', 'Vue', 'Node.js', 'Express'],
                'Databases': ['SQL', 'MongoDB', 'PostgreSQL', 'MySQL', 'Redis', 'Firebase'],
                'Cloud & DevOps': ['AWS', 'Azure', 'GCP', 'Docker', 'Kubernetes', 'CI/CD', 'Git'],
                'Data Science': ['Machine Learning', 'TensorFlow', 'PyTorch', 'Data Analysis', 'NLP']
            }
            
            skills_to_show = list(set(highlighted_skills + skills)) if highlighted_skills else skills
            
            # Categorize skills
            has_categorized = False
            for category, category_skills in skill_categories.items():
                matched_skills = [skill for skill in skills_to_show if skill in category_skills]
                if matched_skills:
                    has_categorized = True
                    content.append(f"{category}: {', '.join(matched_skills)}")
            
            # Add uncategorized skills
            if not has_categorized:
                content.append(", ".join(skills_to_show))
            else:
                # Add uncategorized skills
                categorized = [skill for category_skills in skill_categories.values() 
                              for skill in category_skills]
                uncategorized = [skill for skill in skills_to_show if skill not in categorized]
                if uncategorized:
                    content.append(f"Other: {', '.join(uncategorized)}")
            
            content.append("")
        
        # Summary
        if 'summary' not in excluded_sections:
            content.append("PROFESSIONAL SUMMARY")
            content.append("===================")
            content.append(custom_summary if custom_summary else summary or "Experienced technical professional with a proven track record of success...")
            content.append("")
        
        # Projects (moved up for technical focus)
        if 'projects' not in excluded_sections and projects:
            content.append("TECHNICAL PROJECTS")
            content.append("=================")
            for project in projects:
                if isinstance(project, str):
                    content.append(project)
                elif isinstance(project, dict):
                    # Format dictionary project entries
                    name = project.get('name', '')
                    content.append(name)
                    description = project.get('description', '')
                    if description:
                        content.append(description)
                        
                content.append("")
        
        # Experience
        if 'experience' not in excluded_sections and experience:
            content.append("PROFESSIONAL EXPERIENCE")
            content.append("======================")
            for exp in experience:
                if isinstance(exp, str):
                    content.append(exp)
                elif isinstance(exp, dict):
                    # Format dictionary experience entries
                    job_title = exp.get('title', '')
                    company = exp.get('company', '')
                    dates = f"{exp.get('start_date', '')} - {exp.get('end_date', '')}"
                    
                    if job_title and company:
                        content.append(f"{job_title} at {company}")
                    elif job_title:
                        content.append(job_title)
                        
                    if dates.strip() != '-':
                        content.append(dates)
                        
                    for achievement in exp.get('achievements', []):
                        content.append(f"• {achievement}")
                        
                content.append("")
        
        # Education
        if 'education' not in excluded_sections and education:
            content.append("EDUCATION")
            content.append("=========")
            for edu in education:
                if isinstance(edu, str):
                    content.append(edu)
                elif isinstance(edu, dict):
                    # Format dictionary education entries
                    degree = edu.get('degree', '')
                    institution = edu.get('institution', '')
                    dates = f"{edu.get('start_date', '')} - {edu.get('end_date', '')}"
                    
                    if degree and institution:
                        content.append(f"{degree}, {institution}")
                    elif degree:
                        content.append(degree)
                    elif institution:
                        content.append(institution)
                        
                    if dates.strip() != '-':
                        content.append(dates)
                        
                content.append("")
        
        # Certifications
        if 'certifications' not in excluded_sections and certifications:
            content.append("CERTIFICATIONS")
            content.append("==============")
            for cert in certifications:
                if isinstance(cert, str):
                    content.append(cert)
                elif isinstance(cert, dict):
                    # Format dictionary certification entries
                    name = cert.get('name', '')
                    issuer = cert.get('issuer', '')
                    date = cert.get('date', '')
                    
                    if name:
                        content.append(name)
                    if issuer:
                        content.append(f"Issued by: {issuer}")
                    if date:
                        content.append(date)
                        
                content.append("")
        
        return "\n".join(content)