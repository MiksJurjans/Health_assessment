from flask import Flask, render_template, request, redirect, url_for, flash
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime
from models import User, UserAnswers
from config import Config
from forms import RegisterForm
from models import User, UserAnswers

app = Flask(__name__)
app.config.from_object(Config)
Bootstrap(app)

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

from routes import *



if __name__ == '__main__':
    app.run(debug=True)
