from app import db
from models import User, UserAnswers
from flask_login import current_user
from flask import request
from datetime import datetime

def process_answer(current_question):
    score = request.form.get(current_question['identifier'])
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
    
    if 'comment' in current_question:
        comment = request.form.get(current_question['comment'])
    else:
        comment = 'N/A'

    return answer_text, score, comment

def update_score(current_question, current_question_index, answer_text, score):
    answers = UserAnswers(
        user_id = current_user.id,
        category = current_question['category'],
        question_id = current_question_index + 1,
        answer = answer_text,
        score = score,
        weight = current_question['weight'],
        comment = current_question['comment']
    )
    db.session.add(answers)
    db.session.commit()

def skip_questions(q_from, q_to, current_question, current_question_index, answer = None, weight = 0):
    for i in range(q_from+1, q_to):
        answers = UserAnswers(
            user_id = current_user.id,
            category = current_question['category'],
            question_id = i,
            answer = answer if answer is not None else 'N/A',
            score = 0,
            weight = weight if weight is not 0 else 0,
            comment = 'N/A'
        )
        db.session.add(answers)
        db.session.commit()
    current_question_index = q_to-1
    return current_question_index

def process_time_high(q_id_1, q_id_2, answ_id, high_treshold, low_treshold):        
    time_1 = datetime.strptime(UserAnswers.query.filter_by(question_id=q_id_1).first().answer, "%H:%M")
    time_2 = datetime.strptime(UserAnswers.query.filter_by(question_id=q_id_2).first().answer, "%H:%M")
    time_difference = (time_2 - time_1).total_seconds() / 3600
    
    if time_difference < 0:
        time_difference = 24 + time_difference
    
    if time_difference >= high_treshold:
        UserAnswers.query.filter_by(question_id=answ_id).first().score = '5'
    elif low_treshold <= time_difference < high_treshold:
        UserAnswers.query.filter_by(question_id=answ_id).first().score = '3'
    else:
        UserAnswers.query.filter_by(question_id=answ_id).first().score = '1'

    db.session.commit()

def process_time_low(q_id_1, q_id_2, answ_id, high_treshold, low_treshold):        
    time_1 = datetime.strptime(UserAnswers.query.filter_by(question_id=q_id_1).first().answer, "%H:%M")
    time_2 = datetime.strptime(UserAnswers.query.filter_by(question_id=q_id_2).first().answer, "%H:%M")
    time_difference = (time_2 - time_1).total_seconds() / 3600
    
    if time_difference < 0:
        time_difference = 24 + time_difference
    
    if time_difference <= low_treshold:
        UserAnswers.query.filter_by(question_id=answ_id).first().score = '5'
    elif high_treshold < time_difference <= low_treshold:
        UserAnswers.query.filter_by(question_id=answ_id).first().score = '3'
    else:
        UserAnswers.query.filter_by(question_id=answ_id).first().score = '1'

    db.session.commit()

def cardio_calculation():
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

def calculate_bmi():
    weight_kg = float(UserAnswers.query.filter_by(question_id=54).first().answer)
    height_m = float(UserAnswers.query.filter_by(question_id=55).first().answer)/100
    bmi = weight_kg / (height_m**2)
    print('bmi = ', bmi)
    if 25 > bmi >= 18.5:
        UserAnswers.query.filter_by(question_id=54).first().score = '5'
    else:
        UserAnswers.query.filter_by(question_id=54).first().score = '1'

    db.session.commit()

    return weight_kg, height_m

def calculate_ffmi(weight_kg, height_m):
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

def calculate_whr(gender):
    waist_circ = UserAnswers.query.filter_by(question_id=56).first().answer
    hip_circ = UserAnswers.query.filter_by(question_id=57).first().answer
    whr = float(waist_circ)/float(hip_circ)

    #whr female
    if gender == "Female":
        if whr < 0.8:
            UserAnswers.query.filter_by(question_id=56).first().score = '5'
        else:
            UserAnswers.query.filter_by(question_id=56).first().score = '1'

    db.session.commit()

    #whr male
    if gender == "Male":
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

def tick_counter_extended(current_question_index, very_high, high, medium, low):
    selected_options = request.form.getlist(current_question_index)
    num_selected = len(selected_options)

    if num_selected < low:
        UserAnswers.query.filter_by(question_id=68).first().score = '1'
    elif low <= num_selected <= medium:
        UserAnswers.query.filter_by(question_id=68).first().score = '2'
    elif medium < num_selected < high:
        UserAnswers.query.filter_by(question_id=68).first().score = '3'
    elif high <= num_selected <= very_high:
        UserAnswers.query.filter_by(question_id=68).first().score = '4'
    else:
        UserAnswers.query.filter_by(question_id=68).first().score = '5'

    db.session.commit()

def tick_counter(current_question_index, high, low):
    selected_options = request.form.getlist(current_question_index)
    num_selected = len(selected_options)

    if num_selected >= high:
        UserAnswers.query.filter_by(question_id=70).first().score = '1'
    elif low <= num_selected < high:
        UserAnswers.query.filter_by(question_id=70).first().score = '3'
    else:
        UserAnswers.query.filter_by(question_id=70).first().score = '5'

    db.session.commit()

def water_consumed():
    water_needed = float(UserAnswers.query.filter_by(question_id=54).first().answer) * 0.03
    water_consumed_str = UserAnswers.query.filter_by(question_id=73).first().answer.replace(',', '.')  # Replace comma with period
    water_consumed = float(water_consumed_str)

    if water_consumed >= water_needed:
        UserAnswers.query.filter_by(question_id=73).first().score = "5"
    else:
        UserAnswers.query.filter_by(question_id=73).first().score = "1"

    db.session.commit()
