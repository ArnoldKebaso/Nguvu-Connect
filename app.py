from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SECRET_KEY'] = 'your_secret_key_here'
db = SQLAlchemy(app)

# Initialize DialoGPT components
tokenizer = AutoTokenizer.from_pretrained("microsoft/DialoGPT-small")
model = AutoModelForCausalLM.from_pretrained("microsoft/DialoGPT-small")

# Flask-Login setup
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Association table for user-interests
user_interest = db.Table('user_interest',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('interest_id', db.Integer, db.ForeignKey('interest.id'), primary_key=True)
)

class Interest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    category = db.Column(db.String(20))

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20))  # 'mentee' or 'mentor'
    education = db.Column(db.String(200))
    skills = db.Column(db.String(200))
    interests = db.relationship('Interest', secondary=user_interest, backref='users')
    bio = db.Column(db.Text)
    company = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    is_verified = db.Column(db.Boolean, default=False)

class Goal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mentee_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    mentor_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default='Not Started')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    target_date = db.Column(db.DateTime)

class Session(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mentee_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    mentor_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    scheduled_time = db.Column(db.DateTime)
    location = db.Column(db.String(200))
    feedback = db.Column(db.Text)
    notification_sent = db.Column(db.Boolean, default=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def seed_interests():
    default_interests = [
    # Tech/Digital
    'M-Pesa Integration', 
    'Solar Energy Tech',
    'E-Government Services',
    'Digital Content Creation',
    
    # Agriculture & Related
    'Agritech Solutions',
    'Organic Certification',
    'Hydroponics',
    
    # Creative/Cultural
    'Creative Arts',
    'Cultural Heritage Preservation',
    'Eco-Tourism',
    
    # Business/Development
    'Social Entrepreneurship',
    'Community Development',
    'Informal Sector Finance',
    
    # Emerging Sectors
    'Boda Boda Logistics',
    'E-Waste Recycling',
    'Swahili Tech Localization'
    ]
    for interest in default_interests:
        if not Interest.query.filter_by(name=interest).first():
            db.session.add(Interest(name=interest))
    db.session.commit()

# Create tables and seed interests
with app.app_context():
    db.drop_all()
    db.create_all()
    seed_interests()

def calculate_match_percentage(mentee, mentor):
    mentee_interests = {interest.id for interest in mentee.interests}
    mentor_interests = {interest.id for interest in mentor.interests}
    
    common_interests = mentee_interests & mentor_interests
    total_mentee_interests = len(mentee_interests)
    
    if total_mentee_interests == 0:
        return 0
    
    return (len(common_interests) / total_mentee_interests) * 100

def get_recommended_courses():
    skills = current_user.skills.split(',') if current_user.skills else []
    courses = {
        'farming': 'AgriTech Basics on Udemy',
        'tech': 'Python Fundamentals on Coursera',
        'marketing': 'Digital Marketing Certification'
    }
    return "\n".join([courses.get(skill.strip().lower(), "Basic Computer Skills") for skill in skills][:3])

def get_mentor_matches():
    if current_user.role != 'mentee':
        return "Available for mentees only"
    matches = User.query.filter_by(role='mentor').limit(3).all()
    return "\n".join([f"{m.username} ({', '.join([i.name for i in m.interests][:2])})" for m in matches])

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Invalid username or password')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        role = request.form['role']
        
        new_user = User(
            username=username,
            password=password,
            role=role
        )
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for('profile'))
    
    return render_template('register.html')

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    all_interests = Interest.query.all()
    
    if request.method == 'POST':
        current_user.education = request.form.get('education', '')
        current_user.company = request.form.get('company', '')
        current_user.bio = request.form.get('bio', '')
        current_user.skills = request.form.get('skills', '')
        
        selected_interest_ids = request.form.getlist('interests')
        current_user.interests = Interest.query.filter(
            Interest.id.in_(selected_interest_ids)
        ).all()
        
        db.session.commit()
        flash('Profile updated successfully!')
        return redirect(url_for('dashboard'))
    
    return render_template('profile.html', all_interests=all_interests)

@app.route('/matches')
@login_required
def matches():
    if current_user.role != 'mentee':
        return redirect(url_for('dashboard'))
    
    mentors = User.query.filter_by(role='mentor').all()
    matches = []
    for mentor in mentors:
        match_percent = calculate_match_percentage(current_user, mentor)
        if match_percent > 0:
            matches.append({
                'mentor': mentor,
                'match_percent': round(match_percent, 1)
            })
    
    matches.sort(key=lambda x: x['match_percent'], reverse=True)
    return render_template('matches.html', matches=matches)

@app.route('/dashboard')
@login_required
def dashboard():
    guidelines = [
        "Commit to regular meetings (at least bi-weekly)",
        "Set clear expectations and goals",
        "Maintain confidentiality",
        "Provide constructive feedback"
    ]

    goals = Goal.query.filter(
        (Goal.mentee_id == current_user.id) | 
        (Goal.mentor_id == current_user.id)
    ).all()

    sessions = Session.query.filter(
        (Session.mentee_id == current_user.id) | 
        (Session.mentor_id == current_user.id),
        Session.scheduled_time > datetime.utcnow()
    ).order_by(Session.scheduled_time).all()

    return render_template('dashboard.html',
                         guidelines=guidelines,
                         goals=goals,
                         sessions=sessions,
                         chat_history=session.get('chat_history', []))

@app.route('/goal', methods=['POST'])
@login_required
def create_goal():
    new_goal = Goal(
        mentee_id=current_user.id if current_user.role == 'mentee' else None,
        mentor_id=current_user.id if current_user.role == 'mentor' else None,
        description=request.form['description'],
        target_date=datetime.strptime(request.form['target_date'], '%Y-%m-%d')
    )
    db.session.add(new_goal)
    db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/schedule', methods=['POST'])
@login_required
def schedule_session():
    new_session = Session(
        mentee_id=request.form['mentee_id'],
        mentor_id=request.form['mentor_id'],
        scheduled_time=datetime.strptime(request.form['datetime'], '%Y-%m-%dT%H:%M'),
        location=request.form['location']
    )
    db.session.add(new_session)
    db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/chatbot', methods=['POST'])
@login_required
def chatbot():
    user_message = request.form['message']
    chat_history = session.get('chat_history', [])
    
    local_responses = {
        "cv": "**CV Writing Tips**:\n1. Include KCSE/KCGF certificate numbers\n2. Highlight M-Pesa experience\n3. Mention iTax familiarity\n4. Add vocational training",
        "job": "**Job Platforms**:\n- BrighterMonday\n- MyJobMag\n- County Portals\n- Jijiji Kenya",
        "mentor": get_mentor_matches(),
        "skills": f"**Your Skills**: {current_user.skills}\n**Recommended Courses**:\n{get_recommended_courses()}",
        "interview": "**Interview Tips**:\n1. Research companies\n2. Practice questions\n3. Professional attire\n4. Send thank you emails"
    }
    
    response = None
    for key in local_responses:
        if key in user_message.lower():
            response = local_responses[key]
            break

    if not response:
        try:
            inputs = tokenizer.encode(
                f"{user_message}{tokenizer.eos_token}",
                return_tensors='pt',
                max_length=1000,
                truncation=True
            )
            outputs = model.generate(
                inputs,
                max_length=1000,
                temperature=0.7,
                top_k=40,
                top_p=0.85
            )
            response = tokenizer.decode(outputs[0], skip_special_tokens=True)
        except Exception as e:
            response = "I'm having trouble responding. Please try again later."

    chat_history.append({"user": user_message, "bot": response})
    session['chat_history'] = chat_history[-5:]
    
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.run(debug=True)