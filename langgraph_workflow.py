from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Dict, Any, Optional
from langchain_openai import ChatOpenAI
import os
import re
import json
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Retrieve the OpenAI API key from the environment
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY not found in .env file. Please set it and try again.")

# Initialize the LLM with the API key from the environment
llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.7, api_key=api_key)

class MatchingState(TypedDict):
    cv_text: str
    job_desc: str
    industry: Optional[str]
    domain_keywords: List[str]
    cv_technical_skills: List[str]
    cv_soft_skills: List[str]
    cv_skills: List[str]
    job_technical_skills: List[str]
    job_soft_skills: List[str]
    job_experience_reqs: List[str]
    job_education_reqs: List[str]
    job_industry_knowledge: List[str]
    job_skills: List[str]
    direct_matches: List[str]
    semantic_matches: List[str]
    matches: List[str]
    match_percentage: float
    tech_match_percentage: float
    soft_match_percentage: float
    weighted_match_percentage: float
    optimized_cv: str
    cover_letter: str
    analysis_results: Dict[str, Any]

def identify_industry(state: MatchingState) -> MatchingState:
    job_desc = state["job_desc"]
    prompt = f"""
    Analyze the following job description and identify the industry/sector it belongs to.
    Also identify any specialized domain knowledge that might be required.
    
    Job Description: {job_desc}
    
    Return your answer as a JSON with two fields:
    - "industry": The primary industry (e.g., "Technology", "Healthcare")
    - "domain_keywords": List of 5-10 specialized domain-specific keywords
    """
    response = llm.invoke(prompt)
    try:
        result = json.loads(response.content)
        state["industry"] = result.get("industry", "General")
        state["domain_keywords"] = result.get("domain_keywords", [])
    except Exception as e:
        print(f"Error parsing industry: {e}")
        state["industry"] = "General"
        state["domain_keywords"] = []
    return state

def extract_cv_skills(state: MatchingState) -> MatchingState:
    cv_text = state["cv_text"]
    industry = state.get("industry", "General")
    prompt = f"""
    Extract skills from the CV for a position in the {industry} industry.
    Include technical skills (e.g., Python, SQL) and soft skills (e.g., leadership).
    
    CV Text: {cv_text}
    
    Return as JSON:
    {{
        "technical_skills": ["skill1", "skill2"],
        "soft_skills": ["skill1", "skill2"]
    }}
    """
    response = llm.invoke(prompt)
    try:
        skills_dict = json.loads(response.content)
        technical_skills = [skill.strip().lower() for skill in skills_dict.get("technical_skills", [])]
        soft_skills = [skill.strip().lower() for skill in skills_dict.get("soft_skills", [])]
        state["cv_technical_skills"] = technical_skills
        state["cv_soft_skills"] = soft_skills
        state["cv_skills"] = technical_skills + soft_skills
    except Exception as e:
        print(f"Error parsing CV skills: {e}")
        state["cv_skills"] = []
        state["cv_technical_skills"] = []
        state["cv_soft_skills"] = []
    return state

def extract_job_requirements(state: MatchingState) -> MatchingState:
    job_desc = state["job_desc"]
    industry = state.get("industry", "General")
    prompt = f"""
    Extract requirements from the job description for the {industry} industry.
    
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
    response = llm.invoke(prompt)
    try:
        req_dict = json.loads(response.content)
        technical_skills = [skill.strip().lower() for skill in req_dict.get("technical_skills", [])]
        soft_skills = [skill.strip().lower() for skill in req_dict.get("soft_skills", [])]
        experience_reqs = [req.strip().lower() for req in req_dict.get("experience", [])]
        education_reqs = [req.strip().lower() for req in req_dict.get("education", [])]
        industry_knowledge = [req.strip().lower() for req in req_dict.get("industry_knowledge", [])]
        state["job_technical_skills"] = technical_skills
        state["job_soft_skills"] = soft_skills
        state["job_experience_reqs"] = experience_reqs
        state["job_education_reqs"] = education_reqs
        state["job_industry_knowledge"] = industry_knowledge
        state["job_skills"] = technical_skills + soft_skills + industry_knowledge
    except Exception as e:
        print(f"Error parsing job requirements: {e}")
        state["job_skills"] = []
        state["job_technical_skills"] = []
        state["job_soft_skills"] = []
        state["job_experience_reqs"] = []
        state["job_education_reqs"] = []
        state["job_industry_knowledge"] = []
    return state

def match_skills(state: MatchingState) -> MatchingState:
    cv_skills = state["cv_skills"]
    job_skills = state["job_skills"]
    direct_matches = [skill for skill in cv_skills if skill in job_skills]
    remaining_cv_skills = [skill for skill in cv_skills if skill not in direct_matches]
    remaining_job_skills = [skill for skill in job_skills if skill not in direct_matches]
    
    semantic_matches = []
    if remaining_cv_skills and remaining_job_skills:
        prompt = f"""
        Identify semantic matches between CV skills: {remaining_cv_skills} and job skills: {remaining_job_skills}.
        Return as JSON: [{{"cv_skill": "skill", "job_skill": "skill"}}]
        """
        response = llm.invoke(prompt)
        try:
            semantic_matches = [match["cv_skill"] for match in json.loads(response.content)]
        except Exception as e:
            print(f"Error parsing semantic matches: {e}")
    
    matches = direct_matches + semantic_matches
    match_percentage = (len(matches) / len(job_skills)) * 100 if job_skills else 0
    
    tech_matches = sum(1 for skill in state["job_technical_skills"] if skill in matches)
    soft_matches = sum(1 for skill in state["job_soft_skills"] if skill in matches)
    tech_percentage = (tech_matches / len(state["job_technical_skills"])) * 100 if state["job_technical_skills"] else 0
    soft_percentage = (soft_matches / len(state["job_soft_skills"])) * 100 if state["job_soft_skills"] else 0
    weighted_match = (tech_percentage * 0.7) + (soft_percentage * 0.3)
    
    state["direct_matches"] = direct_matches
    state["semantic_matches"] = semantic_matches
    state["matches"] = matches
    state["match_percentage"] = match_percentage
    state["tech_match_percentage"] = tech_percentage
    state["soft_match_percentage"] = soft_percentage
    state["weighted_match_percentage"] = weighted_match
    return state

def keyword_analysis(state: MatchingState) -> MatchingState:
    cv_text = state["cv_text"]
    job_desc = state["job_desc"]
    cv_skills = state["cv_skills"]
    job_skills = state["job_skills"]
    present_keywords = [skill for skill in cv_skills if skill in job_skills]
    missing_keywords = [skill for skill in job_skills if skill not in cv_skills]
    cv_skill_freq = {skill: cv_text.lower().count(skill.lower()) for skill in job_skills}
    job_skill_freq = {skill: job_desc.lower().count(skill.lower()) for skill in job_skills}
    return {
        "keyword_analysis": {
            "present_keywords": present_keywords,
            "missing_keywords": missing_keywords,
            "cv_skill_freq": cv_skill_freq,
            "job_skill_freq": job_skill_freq
        }
    }

def section_analysis(state: MatchingState) -> MatchingState:
    cv_text = state["cv_text"]
    expected_sections = ["Personal Information", "Education", "Work Experience", "Skills", "Certifications", "Projects"]
    present_sections = [section for section in expected_sections if section.lower() in cv_text.lower()]
    missing_sections = [section for section in expected_sections if section not in present_sections]
    ats_issues = []
    for item in ["email", "phone", "address", "product manager"]:
        if item not in cv_text.lower():
            ats_issues.append(f"Missing {item}")
    date_pattern = r"\b\d{2}/\d{4}\b|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}\b"
    if not re.findall(date_pattern, cv_text):
        ats_issues.append("Incorrect date format (use MM/YYYY or Month YYYY)")
    return {
        "section_analysis": {
            "present_sections": present_sections,
            "missing_sections": missing_sections,
            "ats_issues": ats_issues
        }
    }

def achievement_analysis(state: MatchingState) -> MatchingState:
    cv_text = state["cv_text"]
    measurable_pattern = r"\b(\d+%|\d+\s*(?:points|users|clients))\b"
    achievements = re.findall(measurable_pattern, cv_text)
    achievement_score = min(len(achievements) * 20, 100)
    years_pattern = r"\b(\d+)\s*(?:years?|yrs?)\b"
    years = re.findall(years_pattern, cv_text)
    experience_warning = "No specific years of experience mentioned" if not years else None
    cliches = ["hard-working", "team player", "self-motivated"]
    tone_issues = [cliche for cliche in cliches if cliche in cv_text.lower()]
    tone_warning = "Avoid clichés like: " + ", ".join(tone_issues) if tone_issues else None
    return {
        "achievement_analysis": {
            "achievement_score": achievement_score,
            "quantifiable_achievements": achievements,
            "experience_warning": experience_warning,
            "tone_warning": tone_warning,
            "achievement_recommendations": ["Add more quantifiable metrics"] if len(achievements) < 3 else []
        }
    }

def analyze_cv_detailed(state: MatchingState) -> MatchingState:
    """Analyze the CV in detail with enhanced ATS and competitive analysis."""
    cv_text = state["cv_text"]
    job_desc = state["job_desc"]
    industry = state.get("industry", "General")
    matches = state["matches"]
    job_skills = state["job_skills"]
    cv_technical_skills = state["cv_technical_skills"]
    cv_soft_skills = state["cv_soft_skills"]
    job_technical_skills = state["job_technical_skills"]
    job_soft_skills = state["job_soft_skills"]
    job_experience_reqs = state["job_experience_reqs"]
    job_education_reqs = state["job_education_reqs"]
    job_industry_knowledge = state["job_industry_knowledge"]

    # Enhanced ATS Analysis Prompt
    ats_prompt = f"""
    Perform a comprehensive ATS (Applicant Tracking System) analysis for this CV targeting a position in the {industry} industry.

    CV Text: {cv_text}
    Job Description: {job_desc}
    Matched Skills: {matches}
    Job Technical Skills: {job_technical_skills}
    Job Soft Skills: {job_soft_skills}

    Analyze the following aspects:
    1. **Structure and Formatting**: Are sections clearly defined with headers? Is the format ATS-friendly?
    2. **Keyword Optimization**: How well do CV keywords align with the job description?
    3. **Completeness**: Are critical elements present (e.g., contact info, dates)?
    4. **Industry-Specific Fit**: Does the CV use {industry}-specific terminology?
    5. **Quantifiable Metrics**: Are achievements specific and measurable?

    Provide a detailed JSON response:
    {{
        "ats_score": number (0-100),
        "structure_analysis": {{"score": 0-100, "issues": ["issue1"], "recommendations": ["rec1"]}},
        "keyword_optimization": {{"score": 0-100, "present_keywords": ["kw1"], "missing_keywords": ["kw2"], "recommendations": ["rec1"]}},
        "completeness": {{"score": 0-100, "missing_elements": ["elem1"], "recommendations": ["rec1"]}},
        "industry_fit": {{"score": 0-100, "strengths": ["strength1"], "weaknesses": ["weakness1"], "recommendations": ["rec1"]}},
        "metrics_analysis": {{"score": 0-100, "examples": ["example1"], "recommendations": ["rec1"]}}
    }}
    """
    ats_response = llm.invoke(ats_prompt)
    try:
        ats_analysis = json.loads(ats_response.content)
        print("Enhanced ATS Analysis Results:", ats_analysis)
    except Exception as e:
        print(f"Error parsing ATS analysis: {e}")
        ats_analysis = {
            "ats_score": 50,
            "structure_analysis": {"score": 50, "issues": ["Unclear formatting"], "recommendations": ["Use clear headers"]},
            "keyword_optimization": {"score": 50, "present_keywords": [], "missing_keywords": [], "recommendations": ["Add job-specific keywords"]},
            "completeness": {"score": 50, "missing_elements": ["email"], "recommendations": ["Add contact info"]},
            "industry_fit": {"score": 50, "strengths": [], "weaknesses": ["Generic terms"], "recommendations": ["Use industry jargon"]},
            "metrics_analysis": {"score": 50, "examples": [], "recommendations": ["Add measurable results"]}
        }

    # Enhanced Competitive Analysis Prompt
    competitive_prompt = f"""
    Analyze how this CV positions the candidate competitively for a role in the {industry} industry.

    CV Text: {cv_text}
    Job Description: {job_desc}
    Industry: {industry}
    CV Technical Skills: {cv_technical_skills}
    CV Soft Skills: {cv_soft_skills}
    Job Technical Skills: {job_technical_skills}
    Job Soft Skills: {job_soft_skills}
    Job Experience Requirements: {job_experience_reqs}
    Job Education Requirements: {job_education_reqs}
    Job Industry Knowledge: {job_industry_knowledge}
    Matched Skills: {matches}

    Evaluate:
    1. **Skill Depth**: Do skills show advanced proficiency?
    2. **Experience Relevance**: How well does experience align with job requirements?
    3. **Certifications/Credentials**: Are industry-standard certifications present?
    4. **Unique Selling Points**: What makes the candidate stand out?
    5. **Competitive Standing**: Rate as "below average", "average", "above average", or "exceptional".

    Provide a detailed JSON response:
    {{
        "competitive_score": number (0-100),
        "skill_depth": {{"score": 0-100, "strengths": ["strength1"], "gaps": ["gap1"], "recommendations": ["rec1"]}},
        "experience_relevance": {{"score": 0-100, "alignment": ["align1"], "misalignments": ["misalign1"], "recommendations": ["rec1"]}},
        "certifications": {{"score": 0-100, "present": ["cert1"], "missing": ["cert2"], "recommendations": ["rec1"]}},
        "unique_selling_points": ["usp1"],
        "standing": "below average" | "average" | "above average" | "exceptional",
        "overall_recommendations": ["rec1"]
    }}
    """
    competitive_response = llm.invoke(competitive_prompt)
    try:
        competitive_analysis = json.loads(competitive_response.content)
        print("Enhanced Competitive Analysis Results:", competitive_analysis)
    except Exception as e:
        print(f"Error parsing competitive analysis: {e}")
        competitive_analysis = {
            "competitive_score": 50,
            "skill_depth": {"score": 50, "strengths": [], "gaps": ["Advanced skills lacking"], "recommendations": ["Detail skill proficiency"]},
            "experience_relevance": {"score": 50, "alignment": [], "misalignments": ["Experience not specific"], "recommendations": ["Tailor experience"]},
            "certifications": {"score": 50, "present": [], "missing": [], "recommendations": ["Add relevant certifications"]},
            "unique_selling_points": [],
            "standing": "average",
            "overall_recommendations": ["Highlight unique achievements"]
        }

    # Combine all analyses
    analysis_results = {
        "ats_analysis": ats_analysis,
        "competitive_analysis": competitive_analysis,
        "ats_score": ats_analysis["ats_score"],
        "competitive_score": competitive_analysis["competitive_score"]
    }
    analysis_results.update(keyword_analysis(state))
    analysis_results.update(section_analysis(state))
    analysis_results.update(achievement_analysis(state))

    state["analysis_results"] = analysis_results
    return state

def optimize_cv(state: MatchingState) -> MatchingState:
    cv_text = state["cv_text"]
    job_desc = state["job_desc"]
    prompt = f"""
    Optimize this CV for the job:
    CV Text: {cv_text}
    Job Description: {job_desc}
    Return as markdown.
    """
    response = llm.invoke(prompt)
    state["optimized_cv"] = response.content
    return state

def generate_cover_letter(state: MatchingState) -> MatchingState:
    cv_text = state["cv_text"]
    job_desc = state["job_desc"]
    prompt = f"""
    Generate a cover letter:
    CV Text: {cv_text}
    Job Description: {job_desc}
    """
    response = llm.invoke(prompt)
    state["cover_letter"] = response.content
    return state

workflow = StateGraph(MatchingState)
workflow.add_node("identify_industry", identify_industry)
workflow.add_node("extract_cv_skills", extract_cv_skills)
workflow.add_node("extract_job_requirements", extract_job_requirements)
workflow.add_node("match_skills", match_skills)
workflow.add_node("analyze_cv_detailed", analyze_cv_detailed)
workflow.add_node("optimize_cv", optimize_cv)
workflow.add_node("generate_cover_letter", generate_cover_letter)
workflow.add_edge("identify_industry", "extract_cv_skills")
workflow.add_edge("extract_cv_skills", "extract_job_requirements")
workflow.add_edge("extract_job_requirements", "match_skills")
workflow.add_edge("match_skills", "analyze_cv_detailed")
workflow.add_edge("analyze_cv_detailed", "optimize_cv")
workflow.add_edge("optimize_cv", "generate_cover_letter")
workflow.add_edge("generate_cover_letter", END)
workflow.set_entry_point("identify_industry")
matching_workflow = workflow.compile()