from flask import Flask, render_template, redirect, url_for, flash, request, abort, session, make_response
from flask_bootstrap import Bootstrap
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from functools import wraps
from sqlalchemy import Table, Column, Integer, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from statistics import mean
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField
from wtforms.validators import DataRequired, Email
from question_list import list_of_questions
from datetime import datetime, timedelta
import pandas as pd




app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
Bootstrap(app)

##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///assessment.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Initialize Flask-Login
login_manager = LoginManager(app)
login_manager.login_view = 'startpage'  # Set the login view route

## Form for identifying users
class RegisterForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired()])
    name = StringField("Name", validators=[DataRequired()])
    submit = SubmitField("Let's start!")

##CONFIGURE TABLES
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


with app.app_context():
    db.create_all()

@app.route('/', methods = ['POST', 'GET'])
def startpage():
    form = RegisterForm()
    if form.validate_on_submit():
        new_user = User(
            name = form.name.data,
            email = form.email.data
        )
        db.session.add(new_user)
        db.session.commit()

        login_user(new_user)

        return redirect(url_for('form_page'))
    return render_template("index.html", form=form)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/form', methods = ['POST', 'GET'])
@login_required
def form_page():
    questions = list_of_questions # Get the list of all question from another file
    current_question_index = int(request.form.get('current_index', 0)) # Get the current question index
    current_question = questions[current_question_index] # Get the current question from list of questions
    
    gender_answer = ''

    if request.method == 'POST':

        if current_question_index == len(questions) - 1:
            return redirect(url_for('summary', user_id = current_user.id))
    
        ## Handle cases where the user does not answer the question
        answer = request.form.get(current_question['identifier'])
        if not answer:
            flash("Please provide an answer!")
        else:

            category = current_question['category'] # Get question categroy for the subtitle      
            score = request.form.get(current_question['identifier']) # Get the score (value) from each answer
            weight = current_question['weight'] # Get the weight from each answer

            ## Add comment the user comment or 'N/A' for no comment to the database
            if 'comment' in current_question:
                comment = request.form.get(current_question['comment'])
            else:
                comment = 'N/A'

            
            # Map the selected value to its corresponding text based on the question type
            answer_text = None
            if current_question['type'] == 'radio' or current_question['type'] == 'select_choice': 
                for option in current_question['options']:
                    if option['value'] == score:
                        answer_text = option['label']
                        break
                    
            elif current_question['type'] == 'time':
                answer_text = score
                score = 'N/A'

            elif current_question['type'] == 'text':
                answer_text = score
                score = 'N/A'

            # Collect answer in a database
            answers = UserAnswers(
                user_id = current_user.id,
                category = category,
                question_id = current_question_index + 1,
                answer = answer_text,
                score = score,
                weight = weight,
                comment = comment
            )
            db.session.add(answers)
            db.session.commit()


    ###################################  SLEEP  ########################################
            #Question 1 skip to Question 7
            if answer_text == "No" and current_question_index == 0:
                for i in range(2, 7):
                    answers = UserAnswers(
                        user_id = current_user.id,
                        category = 'sleep',
                        question_id = i,
                        answer = 'N/A',
                        score = 0,
                        weight = 0,
                        comment = 'N/A'
                    )
                    db.session.add(answers)
                    db.session.commit()
                current_question_index = 6

            #Question 4 skip to Question 7
            if answer_text == "No" and current_question_index == 3:
                for i in range(5, 7):
                    answers = UserAnswers(
                        user_id = current_user.id,
                        category = 'sleep',
                        question_id = i,
                        answer = UserAnswers.query.filter_by(question_id=i-3).first().answer,
                        score = 'N/A',
                        weight = 0.5,
                        comment = 'N/A'
                    )
                    db.session.add(answers)
                    db.session.commit()

                current_question_index = 6

            ## No effect on score if "Don't know" the answer to Question 8
            if answer_text == "Don't know" and current_question_index == 7:
                UserAnswers.query.filter_by(question_id=8).first().weight = '0'
                db.session.commit()


            # Calculate the score based on hours slept on weekdays
            if current_question_index == 9 and UserAnswers.query.filter_by(question_id=2).first().answer != 'N/A':
                
                weekday_bedtime = datetime.strptime(UserAnswers.query.filter_by(question_id=2).first().answer, "%H:%M")
                weekday_wakeup = datetime.strptime(UserAnswers.query.filter_by(question_id=3).first().answer, "%H:%M")
                weekday_difference = (weekday_wakeup - weekday_bedtime).total_seconds() / 3600
                
                if weekday_difference < 0:
                    weekday_difference = 24 + weekday_difference

                if weekday_difference >= 8:
                    UserAnswers.query.filter_by(question_id=2).first().score = '5'
                elif 7 <= weekday_difference < 8:
                    UserAnswers.query.filter_by(question_id=2).first().score = '3'
                else:
                    UserAnswers.query.filter_by(question_id=2).first().score = '1'

                db.session.commit()

                #Calculate the score based on hours slept on weekends
                weekend_bedtime = datetime.strptime(UserAnswers.query.filter_by(question_id=5).first().answer, "%H:%M")
                weekend_wakeup = datetime.strptime(UserAnswers.query.filter_by(question_id=6).first().answer, "%H:%M")
                weekend_difference = (weekend_bedtime-weekend_wakeup).total_seconds() / 3600

                if weekend_difference < 0:
                    weekend_difference = 24 + weekend_difference

                if weekend_difference >= 8:
                    UserAnswers.query.filter_by(question_id=3).first().score = '5'
                elif 7 <= weekend_difference < 8:
                    UserAnswers.query.filter_by(question_id=3).first().score = '3'
                else:
                    UserAnswers.query.filter_by(question_id=3).first().score = '1'

                db.session.commit()

                #Calculate the score based on wakeup difference
                wakeup_difference = (weekend_wakeup-weekday_wakeup).total_seconds() / 3600

                if wakeup_difference < 0:
                    wakeup_difference = 24 + wakeup_difference

                if wakeup_difference <= 0.5:
                    UserAnswers.query.filter_by(question_id=5).first().score = '5'
                elif 0.5 < wakeup_difference <= 2:
                    UserAnswers.query.filter_by(question_id=5).first().score = '3'
                else:
                    UserAnswers.query.filter_by(question_id=5).first().score = '1'

                db.session.commit()

                #Calculate the score based on bedtime difference
                bedtime_difference = (weekend_bedtime-weekday_bedtime).total_seconds() / 3600
                
                if bedtime_difference < 0:
                    bedtime_difference = 24 + bedtime_difference

                if bedtime_difference <= 0.5:
                    UserAnswers.query.filter_by(question_id=6).first().score = '5'
                elif 0.5 < bedtime_difference <= 2:
                    UserAnswers.query.filter_by(question_id=6).first().score = '3'
                else:
                    UserAnswers.query.filter_by(question_id=6).first().score = '1'

                db.session.commit()

    ###################################  MEAL SCHEDULE  ########################################

            #Question 12 skip to Question 18
            if answer_text == "No" and current_question_index == 11:
                for i in range(13, 18):
                    answers = UserAnswers(
                        user_id = current_user.id,
                        category = 'meal scedule',
                        question_id = i,
                        answer = 'N/A',
                        score = 0,
                        weight = 0,
                        comment = comment
                    )
                    db.session.add(answers)
                    db.session.commit()
                current_question_index = 17

            #Question 15 skip to Question 18
            if answer_text == "No" and current_question_index == 14:
                for i in range(16, 18):
                    answers = UserAnswers(
                        user_id = current_user.id,
                        category = 'meal scedule',
                        question_id = i,
                        answer = UserAnswers.query.filter_by(question_id=i-3).first().answer,
                        score = '5',
                        weight = 0.3,
                        comment = comment
                    )
                    db.session.add(answers)
                    db.session.commit()
                current_question_index = 17

            # Calculate the score based on hours of the last meals before bedtime on week-days.
            if current_question_index == 17:
                
                if UserAnswers.query.filter_by(question_id=2).first().answer != 'N/A' and UserAnswers.query.filter_by(question_id=13).first().answer != 'N/A': 
                    weekday_last_meal = datetime.strptime(UserAnswers.query.filter_by(question_id=13).first().answer, "%H:%M")
                    weekday_bedtime = datetime.strptime(UserAnswers.query.filter_by(question_id=2).first().answer, "%H:%M")
                    weekday_meal_difference = (weekday_bedtime - weekday_last_meal).total_seconds() / 3600
                    
                    if weekday_meal_difference < 0:
                        weekday_meal_difference = 24 + weekday_meal_difference

                    if weekday_meal_difference >= 3:
                        UserAnswers.query.filter_by(question_id=13).first().score = '5'
                    elif 2 <= weekday_meal_difference < 3:
                        UserAnswers.query.filter_by(question_id=13).first().score = '3'
                    else:
                        UserAnswers.query.filter_by(question_id=13).first().score = '1'
                
                else:
                    UserAnswers.query.filter_by(question_id=13).first().score = '0'
                    UserAnswers.query.filter_by(question_id=13).first().weight = '0'

                db.session.commit()


                # Calculate the score based on hours spent fasting on week-days.
                if UserAnswers.query.filter_by(question_id=2).first().answer != 'N/A' and UserAnswers.query.filter_by(question_id=13).first().answer != 'N/A': 
                    weekday_last_meal = datetime.strptime(UserAnswers.query.filter_by(question_id=13).first().answer, "%H:%M")
                    weekday_wakeup = datetime.strptime(UserAnswers.query.filter_by(question_id=3).first().answer, "%H:%M")
                    weekday_fasting = (weekday_last_meal - weekday_wakeup).total_seconds() / 3600
                    
                    if weekday_fasting < 0:
                        weekday_fasting = 24 + weekday_fasting

                    if weekday_fasting >= 12:
                        UserAnswers.query.filter_by(question_id=14).first().score = '5'
                    elif 10 <= weekday_fasting < 12:
                        UserAnswers.query.filter_by(question_id=14).first().score = '3'
                    else:
                        UserAnswers.query.filter_by(question_id=14).first().score = '1'
                
                else:
                    UserAnswers.query.filter_by(question_id=14).first().score = '0'
                    UserAnswers.query.filter_by(question_id=14).first().weight = '0'

                db.session.commit()

                # Calculate the score based on difference between the first meal on week-ends compared to week-days.
                if UserAnswers.query.filter_by(question_id=2).first().answer != 'N/A' and UserAnswers.query.filter_by(question_id=14).first().answer != 'N/A': 
                    weekday_first_meal = datetime.strptime(UserAnswers.query.filter_by(question_id=14).first().answer, "%H:%M")
                    weekend_first_meal = datetime.strptime(UserAnswers.query.filter_by(question_id=16).first().answer, "%H:%M")
                    first_meal_diff = (weekend_first_meal - weekday_first_meal).total_seconds() / 3600
                    
                    if first_meal_diff < 0:
                        first_meal_diff = 24 + first_meal_diff

                    if first_meal_diff >= 2:
                        UserAnswers.query.filter_by(question_id=16).first().score = '5'
                    elif 1 <= first_meal_diff < 2:
                        UserAnswers.query.filter_by(question_id=16).first().score = '3'
                    else:
                        UserAnswers.query.filter_by(question_id=16).first().score = '1'
                
                else:
                    UserAnswers.query.filter_by(question_id=16).first().score = '0'
                    UserAnswers.query.filter_by(question_id=16).first().weight = '0'

                db.session.commit()

                # Calculate the score based on difference between the last meal on week-ends compared to week-days.
                if UserAnswers.query.filter_by(question_id=2).first().answer != 'N/A' and UserAnswers.query.filter_by(question_id=13).first().answer != 'N/A': 
                    weekday_last_meal = datetime.strptime(UserAnswers.query.filter_by(question_id=13).first().answer, "%H:%M")
                    weekend_last_meal = datetime.strptime(UserAnswers.query.filter_by(question_id=17).first().answer, "%H:%M")
                    last_meal_diff = (weekend_last_meal - weekday_last_meal).total_seconds() / 3600
                    
                    if last_meal_diff < 0:
                        last_meal_diff = 24 + last_meal_diff

                    if last_meal_diff >= 2:
                        UserAnswers.query.filter_by(question_id=17).first().score = '5'
                    elif 1 <= last_meal_diff < 2:
                        UserAnswers.query.filter_by(question_id=17).first().score = '3'
                    else:
                        UserAnswers.query.filter_by(question_id=17).first().score = '1'
                
                else:
                    UserAnswers.query.filter_by(question_id=17).first().score = '0'
                    UserAnswers.query.filter_by(question_id=17).first().weight = '0'

                db.session.commit()

    ###################################  NEUROMODULATION  ########################################
            #Question 19 about drinking coffee answer 'Yes' should not affect score (weight should be 0)
            if answer_text == "Yes" and current_question_index == 18:
                UserAnswers.query.filter_by(question_id=19).first().weight = '0'
                db.session.commit()


            #Question 19 skip to Question 23
            if answer_text == "No" and current_question_index == 18:
                for i in range(20, 23):
                    answers = UserAnswers(
                        user_id = current_user.id,
                        category = 'neuromodulation',
                        question_id = i,
                        answer = 'N/A',
                        score = 0,
                        weight = 0,
                        comment = comment
                    )
                    db.session.add(answers)
                    db.session.commit()
                current_question_index = 22

    ###################################  ALCOHOL CONSUMPTION  ########################################
            #Question 27 skip to Question 30
            if answer_text == "No" and current_question_index == 26:
                for i in range(28, 30):
                    answers = UserAnswers(
                        user_id = current_user.id,
                        category = 'alcohol consumption',
                        question_id = i,
                        answer = 'N/A',
                        score = 0,
                        weight = 0,
                        comment = comment
                    )
                    db.session.add(answers)
                    db.session.commit()
                current_question_index = 29

    ###################################  PHYSICAL ACTIVITY  ########################################
            #Question 41 skip to Question 48
            if answer_text == "No" and current_question_index == 40:
                for i in range(42, 48):
                    answers = UserAnswers(
                        user_id = current_user.id,
                        category = 'physical activity',
                        question_id = i,
                        answer = 'N/A',
                        score = 0,
                        weight = 0,
                        comment = comment
                    )
                    db.session.add(answers)
                    db.session.commit()
                current_question_index = 47

            #Question 43 skip to Question 45
            if answer_text == "No" and current_question_index == 42:
                for i in range(44, 45):
                    answers = UserAnswers(
                        user_id = current_user.id,
                        category = 'physical activity',
                        question_id = i,
                        answer = 'N/A',
                        score = 0,
                        weight = 0,
                        comment = comment
                    )
                    db.session.add(answers)
                    db.session.commit()
                current_question_index = 44

            #Question 45 skip to Question 48
            if answer_text == "No" and current_question_index == 44:
                for i in range(46, 48):
                    answers = UserAnswers(
                        user_id = current_user.id,
                        category = 'physical activity',
                        question_id = i,
                        answer = 'N/A',
                        score = 0,
                        weight = 0,
                        comment = comment
                    )
                    db.session.add(answers)
                    db.session.commit()
                current_question_index = 47


            ## Cardio frequency score
            if current_question_index == 45:
                cardio_frequency = float(UserAnswers.query.filter_by(question_id=46).first().answer)

                if cardio_frequency >= 3:
                    UserAnswers.query.filter_by(question_id=46).first().score = "5"
                else:
                    UserAnswers.query.filter_by(question_id=46).first().score = "3" 

                db.session.commit() 

            ## Cardio length weekly score
            if current_question_index == 46 and UserAnswers.query.filter_by(question_id=45).first().answer == "Yes":
                cardio_frequency = float(UserAnswers.query.filter_by(question_id=46).first().answer)
                cardio_length = float(UserAnswers.query.filter_by(question_id=47).first().answer)
                cardio_time_week = cardio_frequency * cardio_length

                if cardio_time_week >= 150:
                    UserAnswers.query.filter_by(question_id=47).first().score = "5"
                elif 60 <= cardio_time_week < 150:
                    UserAnswers.query.filter_by(question_id=47).first().score = "3"
                else:
                    UserAnswers.query.filter_by(question_id=47).first().score = "1"

                db.session.commit()            


    ###################################  BODY COMPOSITION  ########################################

            ##Gender answer 
            gender_answer_entry = UserAnswers.query.filter_by(question_id=52).first()
            gender_answer = gender_answer_entry.answer if gender_answer_entry else "Not answered"


            #Calculating BMI and FFMI
            if current_question_index == 58:
                weight_kg = float(UserAnswers.query.filter_by(question_id=54).first().answer)
                height_m = float(UserAnswers.query.filter_by(question_id=55).first().answer)/100
                bmi = weight_kg / (height_m**2)
                print('bmi = ', bmi)
                if 25 > bmi >= 18.5:
                    UserAnswers.query.filter_by(question_id=54).first().score = '5'
                else:
                    UserAnswers.query.filter_by(question_id=54).first().score = '1'

                db.session.commit()
                

                if UserAnswers.query.filter_by(question_id=52).first().answer == "Female":
                    add_fat = 5
                else:
                    add_fat = 0
                    
                body_fat = float(UserAnswers.query.filter_by(question_id=58).first().answer)*5 + add_fat
                lean_mass = weight_kg * (1 - body_fat / 100)
                height_feet = height_m * 3.28
                ffmi = (lean_mass / 2.2) / (((height_feet * 12) *0.0254) ** 2)
                print('ffmi = ', ffmi)
                if ffmi >= 22.5:
                    UserAnswers.query.filter_by(question_id=55).first().score = '5'
                elif 22.5 > ffmi >= 20:
                    UserAnswers.query.filter_by(question_id=55).first().score = '4'
                elif 20 > ffmi >= 19:
                    UserAnswers.query.filter_by(question_id=55).first().score = '3'
                elif 19 > ffmi >= 17:
                    UserAnswers.query.filter_by(question_id=55).first().score = '2'
                else:
                    UserAnswers.query.filter_by(question_id=55).first().score = '1'

                db.session.commit()

            #Calculating score for waist / hip ratio

                waist_circ = UserAnswers.query.filter_by(question_id=56).first().answer
                hip_circ = UserAnswers.query.filter_by(question_id=57).first().answer

                whr = float(waist_circ)/float(hip_circ)

                #whr female
                if UserAnswers.query.filter_by(question_id=52).first().answer == "Female":
                    if whr < 0.8:
                        UserAnswers.query.filter_by(question_id=56).first().score = '5'
                    else:
                        UserAnswers.query.filter_by(question_id=56).first().score = '1'

                db.session.commit()

                #whr male
                if UserAnswers.query.filter_by(question_id=52).first().answer == "Male":
                    if whr < 0.9:
                        UserAnswers.query.filter_by(question_id=56).first().score = '5'
                    else:
                        UserAnswers.query.filter_by(question_id=56).first().score = '1'
                
                db.session.commit()

                UserAnswers.query.filter_by(question_id=52).first().score = '0' ## no score for gender
                db.session.commit()
                UserAnswers.query.filter_by(question_id=53).first().score = '0' ## no score for age
                db.session.commit()
                UserAnswers.query.filter_by(question_id=57).first().score = '0' ## whr is a single score
                db.session.commit()


    ###################################  NUTRITION  ########################################

            ## Counting healthy foods
            if current_question_index == 68:
                selected_options = request.form.getlist('q68')
                num_selected = len(selected_options)

                if num_selected < 10:
                    UserAnswers.query.filter_by(question_id=68).first().score = '1'
                elif 10 <= num_selected <= 15:
                    UserAnswers.query.filter_by(question_id=68).first().score = '2'
                elif 15 < num_selected < 20:
                    UserAnswers.query.filter_by(question_id=68).first().score = '3'
                elif 20 <= num_selected <= 25:
                    UserAnswers.query.filter_by(question_id=68).first().score = '4'
                else:
                    UserAnswers.query.filter_by(question_id=68).first().score = '5'

                db.session.commit()
            
            #Counting unhealthy foods
            if current_question_index == 70:
                selected_options = request.form.getlist('q70')
                num_selected = len(selected_options)

                if num_selected >= 5:
                    UserAnswers.query.filter_by(question_id=70).first().score = '1'
                elif 3 <= num_selected < 5:
                    UserAnswers.query.filter_by(question_id=70).first().score = '3'
                else:
                    UserAnswers.query.filter_by(question_id=70).first().score = '5'

                db.session.commit()

            #Counting sources of protein
            if current_question_index == 71:
                selected_options = request.form.getlist('q71')
                num_selected = len(selected_options)

                if num_selected > 5:
                    UserAnswers.query.filter_by(question_id=71).first().score = '5'
                elif 4 <= num_selected <= 5:
                    UserAnswers.query.filter_by(question_id=71).first().score = '4'
                elif num_selected == 3:
                    UserAnswers.query.filter_by(question_id=71).first().score = '3'            
                else:
                    UserAnswers.query.filter_by(question_id=71).first().score = '1'

                db.session.commit()

            #Counting liters of water needed per day based on mass
            if current_question_index == 72:
                water_needed = float(UserAnswers.query.filter_by(question_id=54).first().answer) * 0.03
                water_consumed_str = UserAnswers.query.filter_by(question_id=73).first().answer.replace(',', '.')  # Replace comma with period
                water_consumed = float(water_consumed_str)

                if water_consumed >= water_needed:
                    UserAnswers.query.filter_by(question_id=73).first().score = "5"
                else:
                    UserAnswers.query.filter_by(question_id=73).first().score = "1"

                db.session.commit()

    ###################################  MEDICAL HISTORY  ########################################


    ###################################  UPDATE TO NEXT QUESTION  ########################################
            #Question continuation
            if current_question_index < len(questions) - 1:
                current_question_index += 1
                current_question = questions[current_question_index]

            

    return render_template('form_template.html', 
                           questions=questions, 
                           question=current_question, 
                           index=current_question_index,
                           gender = gender_answer)

@app.route('/summary/<int:user_id>', methods = ['POST', 'GET'])
def summary(user_id):

    results = []

    current_category = 'sleep'
    category_score = 0
    category_weight_sum = 0
    total_questions = 98

    for question_id in range(1, total_questions + 1):
        answer = UserAnswers.query.filter_by(question_id=question_id).first()
        
        if answer:
            # Check if the category has changed
            if answer.category != current_category :
                # Calculate the category's weighted score and print the result
                if category_weight_sum > 0:
                    category_weighted_score = category_score / category_weight_sum
                else:
                    category_weighted_score = 0.0
                print(f"Category {current_category}: Weighted Score = {category_weighted_score}")
                category_result = {
                'category': current_category,
                'score': round(category_weighted_score,2)
                }
                results.append(category_result)
                
                # Reset values for the new category
                current_category = answer.category
                category_score = int(answer.score) * float(answer.weight)
                category_weight_sum = float(answer.weight)
            else:
                # Accumulate score and weight for the current category
                category_score += int(answer.score) * float(answer.weight)
                category_weight_sum += float(answer.weight)

    # Calculate and print the last category's weighted score
    if category_weight_sum > 0:
        category_weighted_score = category_score / category_weight_sum
    else:
        category_weighted_score = 0.0
    print(f"Category {current_category}: Weighted Score = {category_weighted_score}")
    category_result = {
        'category': current_category,
        'score': round(category_weighted_score,2)
        }
    results.append(category_result)

    summary_data = []
    for result in results:
        summary_data.append(result)

    # Create a pandas DataFrame
    df = pd.DataFrame(summary_data)

    # Save DataFrame to a local CSV file
    df.to_csv('summary.csv', index=False)

    # Retrieve all responses for the given user from the database
    user_responses = UserAnswers.query.filter_by(user_id=user_id).all()

    # Prepare data for pandas DataFrame
    summary_data = []
    for response in user_responses:
        summary_data.append({
            'user_id': response.user_id,
            'category': response.category,
            'question_id': response.question_id,
            'answer': response.answer,
            'score': response.score,
            'weight': response.weight,
            'comment': response.comment
        })

    # Create a pandas DataFrame
    df = pd.DataFrame(summary_data)

    # Save DataFrame to a local CSV file
    csv_filename = f'user_{user_id}_responses.csv'
    df.to_csv(csv_filename, index=False)

    def send_csv_to_email(csv_data):
        pass
    # ... code to send email with the CSV data as an attachment ...
    # You can use Python's built-in 'smtplib' library to send emails.
    # Make sure you have email server credentials and details set up.


    return render_template('summary.html', results = results)



if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True, port=5000)