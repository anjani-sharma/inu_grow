from utils.workflow import matching_workflow
from models import CV, JobDescription, db
from services.job_service import JobService
from services.rag_service import RAGService

class AnalysisService:
    @staticmethod
    def analyze_cv_job_match(cv_text, job_desc, user_id, cv_filename=None, cv_skills=None, save_cv=False):
        """
        Analyze the match between a CV and job description
        
        Args:
            cv_text: The text content of the CV
            job_desc: The job description text
            user_id: The ID of the current user
            cv_filename: The filename of the CV (if need to save)
            cv_skills: Any pre-extracted CV skills
            save_cv: Whether to save the CV to the database
            
        Returns:
            A dictionary with the analysis results
        """
        # Initialize RAG
        rag_service = RAGService.get_instance()
        rag_service.add_document(cv_text)
        
        # Run analysis workflow
        state = {"cv_text": cv_text, "job_desc": job_desc}
        
        # Add pre-parsed CV skills to state if available
        if cv_skills:
            print(f"Using pre-parsed skills from database: {cv_skills}")
            state["pre_parsed_skills"] = cv_skills
            
        result = matching_workflow.invoke(state)
        
        # Save job description
        try:
            new_job_desc = JobDescription(user_id=user_id, content=job_desc)
            db.session.add(new_job_desc)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"Error saving job description: {e}")
        
        # Track CV ID to return in results
        cv_id = None
        
        # Save CV if needed (for new uploads)
        if save_cv and cv_filename:
            try:
                cv_skills = result['cv_skills'] if not cv_skills else cv_skills
                new_cv = CV(
                    user_id=user_id, 
                    filename=cv_filename, 
                    content=cv_text, 
                    skills=','.join(cv_skills)
                )
                db.session.add(new_cv)
                db.session.commit()
                cv_id = new_cv.id
            except Exception as e:
                db.session.rollback()
                print(f"Error saving CV: {e}")
        
        # Process results for view
        analysis_results = result['analysis_results']
        response = {
            "matches": result['matches'],
            "match_percentage": result['match_percentage'],
            "optimized_cv": result['optimized_cv'],
            "cover_letter": result['cover_letter'],
            "analysis_results": analysis_results,
            "weighted_match_percentage": result['weighted_match_percentage'],
            "tech_match_percentage": result['tech_match_percentage'],
            "soft_match_percentage": result['soft_match_percentage'],
            "job_technical_skills": result['job_technical_skills'],
            "job_soft_skills": result['job_soft_skills'],
            "cv_skills": result['cv_skills'],
            "cv_text": cv_text,
            "missing_technical_keywords": [kw for kw in analysis_results['keyword_analysis']['missing_keywords'] 
                                        if kw in result['job_technical_skills']],
            "missing_soft_keywords": [kw for kw in analysis_results['keyword_analysis']['missing_keywords'] 
                                    if kw in result['job_soft_skills']],
            "cv_skill_freq": analysis_results['keyword_analysis']['cv_skill_freq'],
            "job_skill_freq": analysis_results['keyword_analysis']['job_skill_freq'],
        }
        
        # Add CV ID if available
        if cv_id:
            response["cv_id"] = cv_id
            
        return response