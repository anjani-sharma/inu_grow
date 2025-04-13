import json
from services.llm_service import LLMService

class LLMCVParser:
    def __init__(self, cv_text, extra_links=None):
        self.cv_text = cv_text
        self.extra_links = extra_links or []

    def parse(self):
        prompt = f"""
Extract structured CV information from the following content.

Return a JSON object with this format:

{{
  "name": "",
  "email": "",
  "phone": "",
  "linkedin": "",
  "github": "",
  "website": "",
  "location": "",
  "summary": "",
  "skills": ["", "", ...],
  "technologies": ["", "", ...],
  "work_experience": [
    {{"title": "", "company": "", "start_date": "", "end_date": "", "achievements": []}},
    ...
  ],
  "education": [
    {{"degree": "", "institution": "", "start_date": "", "end_date": ""}},
    ...
  ],
  "projects": [
    {{"name": "", "description": "", "technologies": [], "url": ""}},
    ...
  ],
  "certifications": [],
  "languages": []
}}

If a field is missing, return it as an empty string or empty list.

CV Text:
{self.cv_text}

Additional hyperlinks found in the CV (match these to LinkedIn, GitHub, website, or personal portfolios):
{', '.join(self.extra_links)}
"""
        try:
            response = LLMService.invoke(prompt)
            parsed_data = json.loads(response.content)

            # ✅ Extract actual links from hyperlinks and override LLM guess
            linkedin_link = next((l for l in self.extra_links if "linkedin.com/in/" in l.lower()), "")
            github_link = next((l for l in self.extra_links if "github.com/" in l.lower() and len(l.strip('/').split('/')) > 3), "")
            website_link = next((l for l in self.extra_links if any(kw in l.lower() for kw in ["portfolio", "about", "mywebsite", "dev"])), "")

            if linkedin_link:
                parsed_data["linkedin"] = linkedin_link
            if github_link:
                parsed_data["github"] = github_link
            if website_link:
                parsed_data["website"] = website_link

            # ✅ Add debug logging to confirm it's working
            print("[DEBUG] Overridden parsed data links:")
            print(f"LinkedIn: {parsed_data.get('linkedin')}")
            print(f"GitHub: {parsed_data.get('github')}")
            print(f"Website: {parsed_data.get('website')}")

            return parsed_data
        except Exception as e:
            print(f"[LLMCVParser Error] {e}")
            return {}
