from app import db
from flask_login import UserMixin

#User
class User(db.Model, UserMixin):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)

#Parent
class UserAnswers(UserMixin, db.Model):
    __tablename__ = "user_scores"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    category = db.Column(db.String(250), unique=False)
    question_id = db.Column(db.Integer, nullable=False)
    answer = db.Column(db.String(250), unique=False)
    score = db.Column(db.String(250), unique=False)
    weight = db.Column(db.Float, unique=False)
    comment = db.Column(db.String(1000), unique=False)

# Add a unique constraint on user_id and question_id together
    db.UniqueConstraint('user_id', 'question_id', name='unique_user_question')
