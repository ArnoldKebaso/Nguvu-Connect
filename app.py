from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SECRET_KEY'] = 'your_secret_key_here'
db = SQLAlchemy(app)

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

class Resource(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(50))
    skill_tag = db.Column(db.String(100))
    link = db.Column(db.String(200))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def seed_interests():
    default_interests = [
        'Data Science', 'AI/ML', 'Web Development',
        'Mobile Development', 'Cloud Computing', 'Cybersecurity',
        'UI/UX Design', 'Project Management', 'Digital Marketing'
    ]
    for interest in default_interests:
        if not Interest.query.filter_by(name=interest).first():
            db.session.add(Interest(name=interest))
    db.session.commit()
    seed_interests()
# Create tables
with app.app_context():
    db.create_all()

@app.route('/')
def home():
    return redirect(url_for('login'))

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
        current_user.education = request.form['education']
        current_user.bio = request.form['bio']
        current_user.company = request.form['company']
        
        # Update interests
        selected_interest_ids = request.form.getlist('interests')
        current_user.interests = Interest.query.filter(Interest.id.in_(selected_interest_ids)).all()
        
        db.session.commit()
        flash('Profile updated successfully!')
        return redirect(url_for('dashboard'))
    
    return render_template('profile.html', all_interests=all_interests)

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
                         sessions=sessions)

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
    responses = {
        "cv": "Check our CV template: <a href='/resources/1'>Download</a>",
        "job": "Try these platforms: LinkedIn, BrighterMonday Kenya",
        "skills": "Recommended courses: Coursera, Udemy, and local tech hubs"
    }
    return responses.get(user_message.lower(), "I'll connect you to a mentor.")

if __name__ == '__main__':
    app.run(debug=True)