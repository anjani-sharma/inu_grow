# job_search.py
from langgraph_workflow import extract_job_requirements

class JobSearchAgent:
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
        }
    ]

    def search_jobs(self, query, location):
        """
        Search for jobs based on query and location.
        For now, uses mock data; replace with real API later.
        """
        # Simple mock search: filter jobs by query in title/description and location
        results = []
        for job in self.MOCK_JOBS:
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

    def analyze_job_description(self, job_desc):
        """
        Analyze a job description using extract_job_requirements from langgraph_workflow.
        Optional method if you want to integrate this functionality.
        """
        state = {"job_desc": job_desc}
        result = extract_job_requirements(state)
        return result