from flask import render_template, request, redirect, url_for, flash
from app import app
from models import User, UserAnswers
from forms import LoginForm, RegistrationForm
from app import app, db 
from models import UserAnswers
from forms import RegisterForm
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from question_list import list_of_questions
from helpers import update_score, skip_questions, process_answer, process_time_high, process_time_low, cardio_calculation, calculate_bmi, calculate_ffmi, calculate_whr, tick_counter_extended, tick_counter, water_consumed
import pandas as pd

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

@app.route('/form', methods = ['POST', 'GET'])
@login_required
def form_page():
    questions = list_of_questions  # Get the list of all questions from another file
    current_question_index = int(request.form.get('current_index', 0))  # Get the current question index
    current_question = questions[current_question_index]  # Get the current question from the list of questions
    gender_answer = ''

    if request.method == 'POST':
        answer_text = request.form.get(current_question['identifier'])

        if not answer_text:
            flash("Please provide an answer!")
        else:
            ## Get the required values from the user answer
            answer_text, score, comment = process_answer(current_question=current_question)

            #Get add the user answer inputs to the database
            update_score(current_question = current_question, 
                         current_question_index = current_question_index,
                         answer_text = answer_text,
                         score = score)
            
            ## Handle question specific cases
    ###################################  SLEEP  ########################################
            #Question 1 skip to Question 7
            if answer_text == "No" and current_question_index == 0:
                current_question_index = skip_questions(q_from = 1, 
                                                        q_to = 7, 
                                                        current_question = current_question,
                                                        current_question_index = current_question_index)

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
                process_time_high(q_id_1=2,
                             q_id_2=3,
                             answ_id=2,
                             high_treshold=8,
                             low_treshold=7)

                #Calculate the score based on hours slept on weekends
                process_time_high(q_id_1=5,
                             q_id_2=6,
                             answ_id=3,
                             high_treshold=8,
                             low_treshold=7)

                #Calculate the score based on wakeup difference
                process_time_low(q_id_1=6,
                             q_id_2=3,
                             answ_id=5,
                             high_treshold=2,
                             low_treshold=0.5)

                #Calculate the score based on bedtime difference
                process_time_low(q_id_1=5,
                             q_id_2=2,
                             answ_id=6,
                             high_treshold=2,
                             low_treshold=0.5)

    ###################################  MEAL SCHEDULE  ########################################

            #Question 12 skip to Question 18
            if answer_text == "No" and current_question_index == 11:
                current_question_index = skip_questions(q_from = 12, 
                                                        q_to = 18, 
                                                        current_question = current_question,
                                                        current_question_index = current_question_index)            

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
                    process_time_high(q_id_1=13,
                                q_id_2=2,
                                answ_id=13,
                                high_treshold=3,
                                low_treshold=2) 

                # Calculate the score based on hours spent fasting on week-days.
                if UserAnswers.query.filter_by(question_id=2).first().answer != 'N/A' and UserAnswers.query.filter_by(question_id=13).first().answer != 'N/A':
                    process_time_high(q_id_1=13,
                                q_id_2=3,
                                answ_id=14,
                                high_treshold=12,
                                low_treshold=10)                 
                else:
                    UserAnswers.query.filter_by(question_id=14).first().score = '0'
                    UserAnswers.query.filter_by(question_id=14).first().weight = '0'

                db.session.commit()

                # Calculate the score based on difference between the first meal on week-ends compared to week-days.
                if UserAnswers.query.filter_by(question_id=2).first().answer != 'N/A' and UserAnswers.query.filter_by(question_id=14).first().answer != 'N/A': 
                    process_time_high(q_id_1=14,
                                q_id_2=16,
                                answ_id=16,
                                high_treshold=2,
                                low_treshold=1)                     
                else:
                    UserAnswers.query.filter_by(question_id=16).first().score = '0'
                    UserAnswers.query.filter_by(question_id=16).first().weight = '0'

                db.session.commit()

                # Calculate the score based on difference between the last meal on week-ends compared to week-days.
                if UserAnswers.query.filter_by(question_id=2).first().answer != 'N/A' and UserAnswers.query.filter_by(question_id=13).first().answer != 'N/A':
                    process_time_high(q_id_1=13,
                                q_id_2=17,
                                answ_id=17,
                                high_treshold=2,
                                low_treshold=1)                    
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
                current_question_index = skip_questions(q_from = 19, 
                                                        q_to = 23, 
                                                        current_question = current_question,
                                                        current_question_index = current_question_index)
                
    ###################################  ALCOHOL CONSUMPTION  ########################################
            #Question 27 skip to Question 30
            if answer_text == "No" and current_question_index == 26:
                current_question_index = skip_questions(q_from = 27, 
                                                        q_to = 30, 
                                                        current_question = current_question,
                                                        current_question_index = current_question_index)
                
    ###################################  PHYSICAL ACTIVITY  ########################################
            #Question 41 skip to Question 48
            if answer_text == "No" and current_question_index == 40:
                current_question_index = skip_questions(q_from = 41, 
                                                        q_to = 48, 
                                                        current_question = current_question,
                                                        current_question_index = current_question_index)

            #Question 43 skip to Question 45
            if answer_text == "No" and current_question_index == 42:
                current_question_index = skip_questions(q_from = 43, 
                                                        q_to = 45, 
                                                        current_question = current_question,
                                                        current_question_index = current_question_index)

            #Question 45 skip to Question 48
            if answer_text == "No" and current_question_index == 44:
                current_question_index = skip_questions(q_from = 45, 
                                                        q_to = 48, 
                                                        current_question = current_question,
                                                        current_question_index = current_question_index)

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
                cardio_calculation()

    ###################################  BODY COMPOSITION  ########################################

            ##Gender answer 
            gender_answer = UserAnswers.query.filter_by(question_id=52).first()

            #Calculating BMI and FFMI
            if current_question_index == 58:
                weight_kg, height_m = calculate_bmi()
                
                calculate_ffmi(weight_kg, height_m)

            #Calculating score for waist / hip ratio
                calculate_whr(gender = gender_answer)

    ###################################  NUTRITION  ########################################

            ## Counting healthy foods
            if current_question_index == 68:
                tick_counter_extended(current_question_index=68,
                                      very_high=25,
                                      high=20,
                                      medium=15,
                                      low=10)            
            #Counting unhealthy foods
            if current_question_index == 70:
                tick_counter(current_question_index=70,
                             high=5,
                             low=4)

            #Counting sources of protein
            if current_question_index == 71:
                tick_counter_extended(current_question_index=71,
                                      very_high=5,
                                      high=4,
                                      medium=2,
                                      low=1)  

            #Counting liters of water needed per day based on mass
            if current_question_index == 72:
                water_consumed()

    ###################################  UPDATE TO NEXT QUESTION  ########################################
            ## Continuation of the questionnaire
            if current_question_index < len(questions) - 1:
                current_question_index += 1
                current_question = questions[current_question_index]

            if current_question_index == len(questions) - 1:
                return redirect(url_for('summary', user_id=current_user.id))

    return render_template('form_template.html',
                           questions=questions,
                           question=current_question,
                           index=current_question_index,
                           gender=gender_answer)

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
