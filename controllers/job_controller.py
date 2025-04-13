from flask import render_template, request
from services.job_service import JobService

def job_search():
    """Handle job search functionality"""
    if request.method == 'POST':
        query = request.form['query']
        location = request.form['location']
        
        # Search for jobs
        jobs = JobService.search_jobs(query, location)
        
        return render_template('job_search.html', jobs=jobs)
    
    # Display empty search page
    return render_template('job_search.html', jobs=None)

def job_description(job_id):
    """Show job description details"""
    # This is a placeholder. In a real implementation, you would fetch 
    # the job with the given ID from a database or API
    job = {
        "id": job_id,
        "title": "Sample Job",
        "company": "Sample Company",
        "location": "Remote",
        "description": "This is a sample job description."
    }
    
    return render_template('job_desc.html', job=job)