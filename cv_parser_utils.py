import json
from cv_parser import CVProfile
from langgraph_workflow import llm  # ✅ importing your LLM directly

def parse_and_enhance_cv(cv_text):
    # 1. Parse using your custom parser
    cv_profile = CVProfile(cv_text)
    parsed_data = cv_profile.parsed_data
    raw_skills = cv_profile.skills

    # 2. Enhance skills using LLM (semantic synonyms, related terms)
    try:
        prompt = f"""
        Given the following CV skills:

        {raw_skills}

        Return a list of semantically related or synonymous skills that should be included for better job matching.

        Format:
        {{
            "enhanced_skills": ["skill1", "skill2", ...]
        }}
        """
        response = llm.invoke(prompt)
        result = json.loads(response.content)
        enhanced_skills = list(set(raw_skills + result.get("enhanced_skills", [])))
    except Exception as e:
        print(f"[LLM Enhancement Error] {e}")
        enhanced_skills = raw_skills

    return {
        "parsed_data": parsed_data,
        "enhanced_skills": enhanced_skills
    }
