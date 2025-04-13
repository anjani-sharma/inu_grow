from models import JobDescription, db
import json

class JobService:
    # Mock job dataset (replace with real API in production)
    MOCK_JOBS = [
        {
            "title": "Software Engineer",
            "description": "We are looking for a Software Engineer with experience in Python, Java, and SQL. Strong communication skills are required.",
            "location": "Remote"
        },
        {
            "title": "Data Analyst",
            "description": "Seeking a Data Analyst proficient in SQL, Python, and data visualization. Teamwork and problem-solving skills are a must.",
            "location": "New York"
        },
        {
            "title": "Product Manager",
            "description": "Looking for a Product Manager with experience in Agile methodologies. Must have excellent communication and leadership skills.",
            "location": "San Francisco"
        },
        {
            "title": "UX Designer",
            "description": "Seeking a UX Designer with expertise in Figma, Adobe XD, and user research. Strong portfolio required.",
            "location": "Boston"
        }
    ]

    @staticmethod
    def search_jobs(query, location):
        """
        Search for jobs based on query and location.
        For now, uses mock data; replace with real API later.
        """
        # Simple mock search: filter jobs by query in title/description and location
        results = []
        for job in JobService.MOCK_JOBS:
            if (query.lower() in job["title"].lower() or 
                query.lower() in job["description"].lower()) and \
               (location.lower() in job["location"].lower() or not location):
                results.append(job)
        
        if not results:
            # Fallback: return a mock job if no matches
            results.append({
                "title": f"Mock Job - {query}",
                "location": location or "Unknown",
                "description": "No exact matches found; this is a mock result."
            })
        return results

    @staticmethod
    def analyze_job_description(job_desc):
        """
        Analyze a job description to extract requirements and skills.
        Uses the LLM service for extraction.
        """
        from services.llm_service import LLMService
        
        prompt = f"""
        Extract requirements from the job description.
        
        Job Description: {job_desc}
        
        Return as JSON:
        {{
            "technical_skills": ["skill1", "skill2"],
            "soft_skills": ["skill1", "skill2"],
            "experience": ["req1", "req2"],
            "education": ["req1", "req2"],
            "industry_knowledge": ["req1", "req2"]
        }}
        """
        
        try:
            response = LLMService.invoke(prompt)
            req_dict = json.loads(response.content)
            
            technical_skills = [skill.strip().lower() for skill in req_dict.get("technical_skills", [])]
            soft_skills = [skill.strip().lower() for skill in req_dict.get("soft_skills", [])]
            experience_reqs = [req.strip().lower() for req in req_dict.get("experience", [])]
            education_reqs = [req.strip().lower() for req in req_dict.get("education", [])]
            industry_knowledge = [req.strip().lower() for req in req_dict.get("industry_knowledge", [])]
            
            return {
                "job_technical_skills": technical_skills,
                "job_soft_skills": soft_skills,
                "job_experience_reqs": experience_reqs,
                "job_education_reqs": education_reqs,
                "job_industry_knowledge": industry_knowledge,
                "job_skills": technical_skills + soft_skills + industry_knowledge
            }
        except Exception as e:
            print(f"Error analyzing job description: {e}")
            return {
                "job_technical_skills": [],
                "job_soft_skills": [],
                "job_experience_reqs": [],
                "job_education_reqs": [],
                "job_industry_knowledge": [],
                "job_skills": []
            }
    
    @staticmethod
    def save_job_description(job_desc, user_id):
        """Save a job description to the database"""
        try:
            new_job_desc = JobDescription(user_id=user_id, content=job_desc)
            db.session.add(new_job_desc)
            db.session.commit()
            return new_job_desc, "Job description saved successfully"
        except Exception as e:
            db.session.rollback()
            return None, f"Error saving job description: {e}"