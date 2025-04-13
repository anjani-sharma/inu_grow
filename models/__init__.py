from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

from .user import User
from .cv import CV
from .job import JobDescription