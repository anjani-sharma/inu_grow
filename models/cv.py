from . import db

class CV(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    filename = db.Column(db.String(120), nullable=False)
    content = db.Column(db.Text, nullable=False)
    skills = db.Column(db.Text)
    summary = db.Column(db.Text)
    hyperlinks = db.Column(db.Text)
    generated_resume = db.Column(db.Text, nullable=True)
    
    def __repr__(self):
        return f'<CV {self.filename}>'
    
    def skills_list(self):
        """Returns a list of skills from the skills string"""
        if not self.skills:
            return []
        return [skill.strip() for skill in self.skills.split(',') if skill.strip()]