import json
from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv

load_dotenv()

class LLMService:
    _instance = None
    
    @classmethod
    def get_instance(cls):
        """Get or create the LLM instance (singleton pattern)"""
        if cls._instance is None:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not found in .env file")
            cls._instance = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.7, api_key=api_key)
        return cls._instance
    
    @classmethod
    def enhance_skills(cls, skills):
        """Use LLM to enhance the skills list with related skills"""
        llm = cls.get_instance()
        try:
            prompt = f"""
            Given the following CV skills:
            
            {skills}
            
            Return a list of semantically related or synonymous skills that should be included for better job matching.
            
            Format:
            {{
                "enhanced_skills": ["skill1", "skill2", ...]
            }}
            """
            response = llm.invoke(prompt)
            result = json.loads(response.content)
            return list(set(skills + result.get("enhanced_skills", [])))
        except Exception as e:
            print(f"[LLM Enhancement Error] {e}")
            return skills
            
    @classmethod
    def invoke(cls, prompt):
        """Directly invoke the LLM with a prompt"""
        llm = cls.get_instance()
        return llm.invoke(prompt)