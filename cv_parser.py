import re
from datetime import datetime

class CVParser:
    def __init__(self, cv_text):
        self.cv_text = cv_text
        self.lines = [line.strip() for line in cv_text.split('\n') if line.strip()]
        self.result = {
            'name': '',
            'position': '',
            'email': '',
            'phone': '',
            'linkedin': '',
            'website': '',
            'location': '',
            'summary': '',
            'work_experience': [],
            'education': [],
            'skills': [],
            'certifications': [],
            'languages': [],
            'projects': [],
            'parsed_at': datetime.now()
        }
        
        # Section keywords for identification
        self.section_keywords = {
            'summary': ['summary', 'profile', 'about', 'objective', 'professional summary'],
            'experience': ['experience', 'employment', 'work history', 'professional experience', 'work experience', 'career'],
            'education': ['education', 'academic', 'qualifications', 'degree', 'university', 'college'],
            'skills': ['skills', 'competencies', 'expertise', 'technical skills', 'core competencies', 'key skills'],
            'certifications': ['certifications', 'certificates', 'credentials', 'qualifications', 'license'],
            'languages': ['languages', 'language skills', 'fluency'],
            'projects': ['projects', 'portfolio', 'work samples', 'key projects', 'achievements']
        }

    def parse(self):
        """Parse the CV text into structured sections"""
        # Extract basic personal information first
        self._extract_personal_info()
        
        # Identify sections in the CV
        sections = self._identify_sections()
        
        # Process each identified section
        for section_name, section_content in sections.items():
            if section_name in ['summary']:
                self.result['summary'] = section_content
            elif section_name in ['experience']:
                self.result['work_experience'] = self._parse_experience(section_content)
            elif section_name in ['education']:
                self.result['education'] = self._parse_education(section_content)
            elif section_name in ['skills']:
                self.result['skills'] = self._parse_skills(section_content)
            elif section_name in ['certifications']:
                self.result['certifications'] = self._parse_certifications(section_content)
            elif section_name in ['languages']:
                self.result['languages'] = self._parse_languages(section_content)
            elif section_name in ['projects']:
                self.result['projects'] = self._parse_projects(section_content)
        
        return self.result
    
    def _extract_personal_info(self):
        """Extract personal information like name, email, phone, etc."""
        # Try to extract name from one of the first few lines
        for i, line in enumerate(self.lines[:10]):
            # Look for a name format (usually 2-3 words without special chars)
            words = line.split()
            if (2 <= len(words) <= 4 and 
                all(word.isalpha() or word.replace('.', '').isalpha() for word in words) and
                any(word[0].isupper() for word in words) and
                not any(keyword in line.lower() for keyword in ['university', 'college', 'resume', 'cv'])):
                self.result['name'] = line
                break
        
        # Look for email
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        email_match = re.search(email_pattern, self.cv_text)
        if email_match:
            self.result['email'] = email_match.group()
        
        # Look for phone number
        phone_patterns = [
            r'\b(?:\+\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b',  # (123) 456-7890 or +1 123-456-7890
            r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b',  # 123-456-7890
            r'\b\+\d{10,15}\b'  # +1234567890
        ]
        
        for pattern in phone_patterns:
            phone_match = re.search(pattern, self.cv_text)
            if phone_match:
                self.result['phone'] = phone_match.group()
                break
        
        # Look for LinkedIn
        linkedin_pattern = r'linkedin\.com/in/[\w-]+'
        linkedin_match = re.search(linkedin_pattern, self.cv_text.lower())
        if linkedin_match:
            self.result['linkedin'] = linkedin_match.group()
        
        # Look for website
        website_pattern = r'(https?://)?(www\.)?[\w-]+\.(com|org|net|io|dev)(/[\w-]+)*'
        website_matches = re.findall(website_pattern, self.cv_text.lower())
        for match in website_matches:
            full_match = ''.join(match)
            if 'linkedin' not in full_match and len(full_match) > 5:
                self.result['website'] = full_match
                break
        
        # Try to extract a job title/position
        position_keywords = [
            'data scientist', 'software engineer', 'developer', 'analyst', 
            'manager', 'director', 'consultant', 'specialist', 'lead',
            'architect', 'administrator', 'coordinator', 'designer',
            'researcher', 'professor', 'teacher', 'instructor',
            'executive', 'assistant', 'associate', 'chief', 'head',
            'officer', 'president', 'vice president', 'ceo', 'cto', 'cfo',
            'intern', 'trainee', 'apprentice', 'junior', 'senior'
        ]
        
        for i, line in enumerate(self.lines[:15]):
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in position_keywords) and len(line.split()) <= 6:
                if not (i > 0 and line == self.result['name']):
                    self.result['position'] = line
                    break
        
        # Try to find location information
        location_patterns = [
            r'\b[A-Z][a-z]+,\s*[A-Z]{2}\b',  # City, State
            r'\b[A-Z][a-z]+,\s*[A-Z][a-z]+\b',  # City, Country
            r'\b[A-Z][a-z]+(,\s*[A-Z][a-z]+)?,\s*[A-Z][a-z]+\b'  # City, Region, Country
        ]
        
        for pattern in location_patterns:
            location_match = re.search(pattern, self.cv_text)
            if location_match:
                self.result['location'] = location_match.group()
                break
    
    def _identify_sections(self):
        """Identify different sections in the CV based on section headers"""
        sections = {}
        current_section = None
        current_content = []
        
        for i, line in enumerate(self.lines):
            line_lower = line.lower()
            
            # Check if this is a section header
            detected_section = None
            
            # Check for common section headers
            for section, keywords in self.section_keywords.items():
                # Look for exact match (e.g., "Work Experience", "Skills")
                if line_lower in [kw.lower() for kw in keywords]:
                    detected_section = section
                    break
                
                # Look for partial matches (e.g., "Professional Experience" contains "experience")
                if any(kw.lower() in line_lower for kw in keywords) and len(line.split()) <= 5:
                    # Make sure it's likely a header (short, possibly uppercase)
                    if line.isupper() or any(word[0].isupper() for word in line.split()):
                        detected_section = section
                        break
            
            # If we found a new section
            if detected_section:
                # Save the previous section if it exists
                if current_section and current_content:
                    sections[current_section] = '\n'.join(current_content)
                
                # Start a new section
                current_section = detected_section
                current_content = []
            elif current_section:
                # Add line to current section content
                current_content.append(line)
        
        # Add the last section
        if current_section and current_content:
            sections[current_section] = '\n'.join(current_content)
        
        return sections
    
    def _parse_experience(self, content):
        """Parse work experience section into structured format"""
        if not content:
            return []

        experiences = []
        job_entries = self._split_into_entries(content) or []
        
        for entry in job_entries:
            job = {
                'title': '',
                'company': '',
                'location': '',
                'start_date': '',
                'end_date': '',
                'description': [],
                'achievements': []
            }
            
            lines = entry.split('\n')
            
            # First line often contains job title and company
            if lines:
                first_line = lines[0]
                
                # Try to extract job title and company
                if ' at ' in first_line.lower():
                    parts = first_line.split(' at ', 1)
                    job['title'] = parts[0].strip()
                    job['company'] = parts[1].strip()
                elif ' - ' in first_line:
                    parts = first_line.split(' - ', 1)
                    job['title'] = parts[0].strip()
                    job['company'] = parts[1].strip()
                elif '|' in first_line:
                    parts = first_line.split('|', 1)
                    job['title'] = parts[0].strip()
                    job['company'] = parts[1].strip()
                else:
                    # If no clear separator, assume it's the job title
                    job['title'] = first_line
            
            # Look for dates in the entry
            date_pattern = r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December)\.?\s+\d{4}\s*(?:-|to|–|until)\s*((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December)\.?\s+\d{4}|Present|Current)'
            date_match = re.search(date_pattern, entry, re.IGNORECASE)
            
            if date_match:
                date_str = date_match.group()
                if 'to' in date_str.lower():
                    parts = date_str.lower().split('to')
                elif '-' in date_str:
                    parts = date_str.split('-')
                elif '–' in date_str:  # en dash
                    parts = date_str.split('–')
                elif 'until' in date_str.lower():
                    parts = date_str.lower().split('until')
                else:
                    parts = [date_str]
                
                if len(parts) >= 2:
                    job['start_date'] = parts[0].strip()
                    job['end_date'] = parts[1].strip()
                elif len(parts) == 1:
                    # If only one part (rare), assume it's the end date
                    job['end_date'] = parts[0].strip()
            
            # If no date found with the above pattern, try a different approach
            if not job['start_date'] and not job['end_date']:
                # Look for just years, like "2019 - 2021" or "2019 - Present"
                year_pattern = r'(20\d{2}|19\d{2})\s*(?:-|to|–|until)\s*(20\d{2}|19\d{2}|Present|Current)'
                year_match = re.search(year_pattern, entry, re.IGNORECASE)
                
                if year_match:
                    year_str = year_match.group()
                    if 'to' in year_str.lower():
                        parts = year_str.lower().split('to')
                    elif '-' in year_str:
                        parts = year_str.split('-')
                    elif '–' in year_str:  # en dash
                        parts = year_str.split('–')
                    elif 'until' in year_str.lower():
                        parts = year_str.lower().split('until')
                    else:
                        parts = [year_str]
                    
                    if len(parts) >= 2:
                        job['start_date'] = parts[0].strip()
                        job['end_date'] = parts[1].strip()
            
            # Look for bullet points or numbered lists for achievements
            for i, line in enumerate(lines[1:], 1):
                line = line.strip()
                
                # Skip if it's a date line we already processed
                if date_match and date_match.group() in line:
                    continue
                
                # Look for bullet points or numbered items
                if line.startswith('•') or line.startswith('-') or line.startswith('*') or re.match(r'^\d+\.', line):
                    # Clean up the bullet point or number
                    achievement = re.sub(r'^[•\-*\d\.]+\s*', '', line).strip()
                    if achievement:
                        job['achievements'].append(achievement)
                elif i > 1 and len(line) > 20:  # Longer lines after the first two lines are likely descriptions
                    job['description'].append(line)
            
            # Add the job to experiences list
            if job['title'] or job['company']:
                experiences.append(job)
        
        return experiences
    
    def _parse_education(self, content):
        """Parse education section into structured format"""
        education_entries = []
        
        # Split content into separate education entries
        entries = self._split_into_entries(content) or []   
        
        for entry in entries:
            education = {
                'degree': '',
                'field': '',
                'institution': '',
                'location': '',
                'start_date': '',
                'end_date': '',
                'gpa': '',
                'achievements': []
            }
            
            lines = entry.split('\n')
            
            # First line often contains degree and institution
            if lines:
                first_line = lines[0]
                
                # Look for degree patterns
                degree_match = re.search(r'(Bachelor|Master|PhD|Doctorate|B\.S\.|M\.S\.|B\.A\.|M\.A\.|MBA|Ph\.D\.|BSc|MSc|BA|MA|MD|JD)(?:\s+(?:of|in)\s+(\w+(?:\s+\w+)*))?', first_line, re.IGNORECASE)
                
                if degree_match:
                    education['degree'] = degree_match.group(1)
                    if degree_match.group(2):
                        education['field'] = degree_match.group(2)
                    
                    # Look for institution after the degree
                    if "," in first_line:
                        institution_part = first_line.split(",", 1)[1].strip()
                        education['institution'] = institution_part
                    elif "at" in first_line.lower():
                        institution_part = first_line.lower().split("at", 1)[1].strip()
                        education['institution'] = institution_part
                    elif "-" in first_line:
                        institution_part = first_line.split("-", 1)[1].strip()
                        education['institution'] = institution_part
                else:
                    # If no clear degree format, check if it contains university/college keywords
                    university_pattern = r'(University|College|Institute|School) of ([A-Za-z\s]+)'
                    uni_match = re.search(university_pattern, first_line, re.IGNORECASE)
                    
                    if uni_match:
                        education['institution'] = uni_match.group()
                    else:
                        # As a fallback, take the first line as degree or institution
                        if any(term in first_line.lower() for term in ['university', 'college', 'institute', 'school']):
                            education['institution'] = first_line
                        else:
                            education['degree'] = first_line
            
            # Look for dates in the entry
            year_pattern = r'(19|20)\d{2}\s*(?:-|to|–|until)\s*((?:19|20)\d{2}|Present|Current)'
            year_match = re.search(year_pattern, entry)
            
            if year_match:
                date_str = year_match.group()
                if 'to' in date_str.lower():
                    parts = date_str.lower().split('to')
                elif '-' in date_str:
                    parts = date_str.split('-')
                elif '–' in date_str:  # en dash
                    parts = date_str.split('–')
                elif 'until' in date_str.lower():
                    parts = date_str.lower().split('until')
                else:
                    parts = [date_str]
                
                if len(parts) >= 2:
                    education['start_date'] = parts[0].strip()
                    education['end_date'] = parts[1].strip()
                elif len(parts) == 1:
                    # If only one date, assume it's graduation date
                    education['end_date'] = parts[0].strip()
            
            # Look for GPA
            gpa_pattern = r'GPA:?\s*([\d\.]+)(?:/[\d\.]+)?|[\d\.]+\s+GPA'
            gpa_match = re.search(gpa_pattern, entry, re.IGNORECASE)
            if gpa_match:
                gpa_parts = gpa_match.group().split()
                for part in gpa_parts:
                    if part.replace('.', '').isdigit():
                        education['gpa'] = part
                        break
            
            # Look for achievements
            for i, line in enumerate(lines[1:], 1):
                line = line.strip()
                
                # Skip if it's a date/GPA line we already processed
                if (year_match and year_match.group() in line) or (gpa_match and gpa_match.group() in line):
                    continue
                
                # Look for bullet points or honors
                if line.startswith('•') or line.startswith('-') or line.startswith('*') or re.match(r'^\d+\.', line):
                    # Clean up the bullet point or number
                    achievement = re.sub(r'^[•\-*\d\.]+\s*', '', line).strip()
                    if achievement:
                        education['achievements'].append(achievement)
                elif 'honor' in line.lower() or 'award' in line.lower() or 'scholar' in line.lower():
                    education['achievements'].append(line)
            
            # Add the education entry
            if education['degree'] or education['institution']:
                education_entries.append(education)
        
        return education_entries
    
    def _parse_skills(self, content):
        """Parse skills section into structured format"""
        skill_list = []
        
        # Try to identify skill categories and individual skills
        lines = content.split('\n')
        current_category = 'General'
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if this is a category header
            if line.endswith(':') or line.endswith('Skills') or line.endswith('skills'):
                current_category = line.rstrip(':')
                continue
            
            # Handle skills with proficiency indicators
            proficiency_match = re.search(r'(.*?)\s*\((Advanced|Intermediate|Beginner|Expert|Proficient)\)', line)
            if proficiency_match:
                skill_name = proficiency_match.group(1).strip()
                proficiency = proficiency_match.group(2)
                skill_list.append({
                    'name': skill_name,
                    'category': current_category,
                    'proficiency': proficiency
                })
                continue
            
            # Handle lists of skills separated by commas or bullet points
            if ',' in line:
                # Split by commas
                for skill in line.split(','):
                    skill = skill.strip()
                    if skill:
                        # Clean up bullet points
                        skill = re.sub(r'^[•\-*]', '', skill).strip()
                        skill_list.append({
                            'name': skill,
                            'category': current_category,
                            'proficiency': ''
                        })
            elif line.startswith('•') or line.startswith('-') or line.startswith('*'):
                # Clean up bullet point
                skill = re.sub(r'^[•\-*]', '', line).strip()
                skill_list.append({
                    'name': skill,
                    'category': current_category,
                    'proficiency': ''
                })
            else:
                # Individual skill on its own line
                skill_list.append({
                    'name': line,
                    'category': current_category,
                    'proficiency': ''
                })
        
        return skill_list
    
    def _parse_certifications(self, content):
        """Parse certifications section into structured format"""
        certifications = []
        
        # Split content into separate certification entries
        entries = self._split_into_entries(content) or []
        
        for entry in entries:
            certification = {
                'name': '',
                'issuer': '',
                'date': '',
                'expiration': '',
                'description': ''
            }
            
            lines = entry.split('\n')
            
            # First line is typically the certification name
            if lines:
                certification['name'] = lines[0]
            
            # Look for issuer and dates
            for i, line in enumerate(lines[1:], 1):
                line = line.strip()
                
                # Skip empty lines
                if not line:
                    continue
                
                # Look for patterns indicating the issuer
                if any(term in line.lower() for term in ['issued by', 'from', 'provider', 'issuer']):
                    # Extract issuer name
                    issuer_parts = re.split(r'issued by|from|provider|issuer', line.lower(), maxsplit=1, flags=re.IGNORECASE)
                    if len(issuer_parts) > 1:
                        certification['issuer'] = issuer_parts[1].strip()
                    else:
                        certification['issuer'] = line
                    continue
                
                # Look for date patterns
                date_match = re.search(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December)\.?\s+\d{4}|(?:19|20)\d{2}', line)
                
                if date_match:
                    if not certification['date']:
                        certification['date'] = date_match.group()
                    elif 'expir' in line.lower() or 'valid until' in line.lower():
                        certification['expiration'] = date_match.group()
                    continue
                
                # If not identified as issuer or date, treat as description
                if i > 1 and not certification['description']:
                    certification['description'] = line
            
            # Add the certification if we have at least a name
            if certification['name']:
                certifications.append(certification)
        
        return certifications
    
    def _parse_languages(self, content):
        """Parse languages section into structured format"""
        languages = []
        
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            language = {
                'name': '',
                'proficiency': ''
            }
            
            # Check for proficiency indication
            proficiency_patterns = [
                r'(.*?)\s*\((Native|Fluent|Professional|Intermediate|Beginner|Advanced|Basic)\)',
                r'(.*?)\s*(?:-|:)\s*(Native|Fluent|Professional|Intermediate|Beginner|Advanced|Basic)',
                r'(.*?)\s*:\s*(C1|C2|B1|B2|A1|A2)'
            ]
            
            matched = False
            for pattern in proficiency_patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    language['name'] = match.group(1).strip()
                    language['proficiency'] = match.group(2)
                    matched = True
                    break
            
            if not matched:
                # Clean up bullet points
                language_name = re.sub(r'^[•\-*]', '', line).strip()
                language['name'] = language_name
            
            if language['name']:
                languages.append(language)
        
        return languages
    
    def _parse_projects(self, content):
        """Parse projects section into structured format"""
        projects = []
        
        # Split content into separate project entries
        entries = self._split_into_entries(content) or []
         
        for entry in entries:
            project = {
                'name': '',
                'role': '',
                'date': '',
                'description': '',
                'technologies': [],
                'achievements': []
            }
            
            lines = entry.split('\n')
            
            # First line is typically the project name
            if lines:
                project['name'] = lines[0]
            
            # Parse other project details
            for i, line in enumerate(lines[1:], 1):
                line = line.strip()
                
                # Skip empty lines
                if not line:
                    continue
                
                # Look for dates
                date_match = re.search(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December)\.?\s+\d{4}|(?:19|20)\d{2}', line)
                
                if date_match and not project['date']:
                    project['date'] = line
                    continue
                
                # Look for technology list
                if any(term in line.lower() for term in ['technologies', 'tools', 'tech stack', 'implemented using', 'built with']):
                    tech_parts = re.split(r'technologies|tools|tech stack|implemented using|built with', line.lower(), maxsplit=1, flags=re.IGNORECASE)
                    if len(tech_parts) > 1:
                        techs = tech_parts[1].strip(':, ').split(',')
                        project['technologies'] = [tech.strip() for tech in techs if tech.strip()]
                    continue
                
                # Look for role
                if any(term in line.lower() for term in ['role', 'position', 'responsible for']):
                    role_parts = re.split(r'role|position|responsible for', line.lower(), maxsplit=1, flags=re.IGNORECASE)
                    if len(role_parts) > 1:
                        project['role'] = role_parts[1].strip(':, ')
                    continue
                
                # Look for achievements/bullet points
                if line.startswith('•') or line.startswith('-') or line.startswith('*') or re.match(r'^\d+\.', line):
                    # Clean up the bullet point or number
                    achievement = re.sub(r'^[•\-*\d\.]+\s*', '', line).strip()
                    if achievement:
                        project['achievements'].append(achievement)
                elif not project['description'] and i == 1:
                    # First non-header line is likely a description
                    project['description'] = line
            
            # Add the project if we have at least a name
            if project['name']:
                projects.append(project)
        
        return projects
    
    def _split_into_entries(self, content):
        """Split section content into separate entries based on spacing and formatting"""
        # First try to split by double newlines
        entries = []
        current_entry = []
        
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if not line.strip():
                if current_entry:
                    entries.append('\n'.join(current_entry))
                    current_entry = []
                continue
            
            # Check if this might be the start of a new entry
            # (e.g., job title, degree, or company name)
            if not current_entry:
                current_entry.append(line)
            else:
                # Check for patterns that would indicate a new entry
                is_new_entry = False
                
                # Date patterns suggesting a new entry
                date_pattern = r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December)\.?\s+\d{4}'
                if re.search(date_pattern, line) and i > 0 and not re.search(date_pattern, lines[i-1]):
                    is_new_entry = True
                
                # Year patterns (2018-2020)
                year_pattern = r'(19|20)\d{2}\s*(?:-|to|–|until)'
                if re.search(year_pattern, line) and i > 0 and not re.search(year_pattern, lines[i-1]):
                    is_new_entry = True
                
                # Job title or company patterns
                elif (any(separator in line for separator in [' at ', ' - ', ' | ']) and
                      not any(separator in current_entry[-1] for separator in [' at ', ' - ', ' | '])):
                    is_new_entry = True
                
                # Look for capitalized lines that might be headers
                elif (line[0].isupper() and 
                      len(line.split()) <= 5 and 
                      not line.startswith('•') and 
                      not line.startswith('-') and
                      i > 0 and
                      (lines[i-1].startswith('•') or lines[i-1].startswith('-'))):
                    is_new_entry = True
                
                if is_new_entry and current_entry:
                    entries.append('\n'.join(current_entry))
                    current_entry = [line]
                else:
                    current_entry.append(line)
        
        # Add the last entry
        if current_entry:
            entries.append('\n'.join(current_entry))
        
        # If no clear entries were found, treat the whole content as one entry
        if not entries:
            entries = [content]

class CVProfile:
    def __init__(self, raw_text: str):
        self.raw_text = raw_text
        self.parser = CVParser(raw_text)
        self.parsed_data = self.parser.parse()

        self.skills = [s['name'].strip().lower() for s in self.parsed_data.get('skills', [])]
        self.experience = self.parsed_data.get('work_experience', [])
        self.education = self.parsed_data.get('education', [])
        self.certifications = self.parsed_data.get('certifications', [])
        self.projects = self.parsed_data.get('projects', [])
        self.summary = self.parsed_data.get('summary', '')

    def has_skill(self, skill: str, threshold: float = 0.8) -> bool:
        """Check if the CV includes a skill approximately."""
        from difflib import SequenceMatcher
        skill = skill.strip().lower()
        return any(SequenceMatcher(None, skill, s).ratio() >= threshold for s in self.skills)

    def skill_match_score(self, skill: str, threshold: float = 0.8) -> float:
        """Return highest similarity score for a skill."""
        from difflib import SequenceMatcher
        skill = skill.strip().lower()
        return max(SequenceMatcher(None, skill, s).ratio() for s in self.skills) if self.skills else 0.0

    def get_achievements(self) -> list:
        return [a for exp in self.experience for a in exp.get('achievements', [])]

class CVProfile:
    def __init__(self, cv_text):
        self.parser = CVParser(cv_text)
        self.parsed_data = self.parser.parse()
        self.skills = [s['name'].strip().lower() for s in self.parsed_data.get('skills', []) if s]
        self.experience = self.parsed_data.get('work_experience', [])
        self.education = self.parsed_data.get('education', [])
        self.summary = self.parsed_data.get('summary', '')
        self.certifications = self.parsed_data.get('certifications', [])
        self.languages = self.parsed_data.get('languages', [])
        self.projects = self.parsed_data.get('projects', [])
        self.tools = self.parsed_data.get('tools', [])
        self.achievements = self.parsed_data.get('achievements', [])