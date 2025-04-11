from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SECRET_KEY'] = 'your_secret_key_here'
db = SQLAlchemy(app)

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20))  # 'mentee' or 'mentor'
    education = db.Column(db.String(200))
    skills = db.Column(db.String(200))
    interests = db.Column(db.String(200))
    guidelines_accepted = db.Column(db.Boolean, default=False)
class Goal(db.Model):  # New model
    id = db.Column(db.Integer, primary_key=True)
    mentee_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    mentor_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default='Not Started')  # Not Started/In Progress/Completed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    target_date = db.Column(db.DateTime)


class Session(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mentee_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    mentor_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    date = db.Column(db.String(50))
    feedback = db.Column(db.Text)
    scheduled_time = db.Column(db.DateTime)
    location = db.Column(db.String(200))  # e.g., Google Meet link
    notification_sent = db.Column(db.Boolean, default=False)
class Resource(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(50))  # 'course', 'article'
    skill_tag = db.Column(db.String(100))
    link = db.Column(db.String(200))

# Create tables
with app.app_context():
    db.create_all()

# -------------------  Home Route ------------------- 
@app.route('/')
def home():
    return redirect(url_for('register'))

# -------------------  Registration Route ------------------- 
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        role = request.form['role']
        
        new_user = User(username=username, password=password, role=role)
        db.session.add(new_user)
        db.session.commit()
        
        # Redirect to profile page WITH USER ID
        return redirect(url_for('profile', user_id=new_user.id))
    
    return render_template('register.html')

# -------------------  Profile Route ------------------- 
@app.route('/profile/<int:user_id>', methods=['GET', 'POST'])
def profile(user_id):
    user = User.query.get(user_id)
    
    if request.method == 'POST':
        user.education = request.form['education']
        user.skills = request.form['skills']
        user.interests = request.form['interests']
        db.session.commit()
        return redirect(url_for('dashboard', user_id=user.id))
    
    return render_template('profile.html', user=user)

# -------------------  Dashboard Route ------------------- 
@app.route('/dashboard/<int:user_id>')
def dashboard(user_id):
    current_user = User.query.get(user_id)
    
    # Get mentorship guidelines
    guidelines = [
        "Commit to regular meetings (at least bi-weekly)",
        "Set clear expectations and goals",
        "Maintain confidentiality",
        "Provide constructive feedback"
    ]

    # Get goals
    goals = Goal.query.filter(
        (Goal.mentee_id == user_id) | (Goal.mentor_id == user_id)
    ).all()

    # Get upcoming sessions
    sessions = Session.query.filter(
        (Session.mentee_id == user_id) | (Session.mentor_id == user_id),
        Session.scheduled_time > datetime.utcnow()
    ).order_by(Session.scheduled_time).all()

    return render_template('dashboard.html', 
                        user=current_user,
                        guidelines=guidelines,
                        goals=goals,
                        sessions=sessions)
    
    
# ------------------- New Goal Route -------------------
@app.route('/goal/<int:user_id>', methods=['POST'])
def create_goal(user_id):
    current_user = User.query.get(user_id)
    goal = Goal(
        mentee_id=current_user.id if current_user.role == 'mentee' else None,
        mentor_id=current_user.id if current_user.role == 'mentor' else None,
        description=request.form['description'],
        target_date=datetime.strptime(request.form['target_date'], '%Y-%m-%d')
    )
    db.session.add(goal)
    db.session.commit()
    return redirect(url_for('dashboard', user_id=user_id))

# ------------------- New Session Route -------------------
@app.route('/schedule/<int:user_id>', methods=['POST'])
def schedule_session(user_id):
    session = Session(
        mentee_id=request.form['mentee_id'],
        mentor_id=request.form['mentor_id'],
        scheduled_time=datetime.strptime(request.form['datetime'], '%Y-%m-%dT%H:%M'),
        location=request.form['location']
    )
    db.session.add(session)
    db.session.commit()
    return redirect(url_for('dashboard', user_id=user_id))
# ------------------- Chatbot Route ------------------- 
@app.route('/chatbot', methods=['POST'])
def chatbot():
    user_message = request.form['message']
    responses = {
        "cv": "Check our CV template: <a href='/resources/1'>Download</a>",
        "job": "Try these platforms: LinkedIn, BrighterMonday Kenya"
    }
    return responses.get(user_message.lower(), "I’ll connect you to a mentor.")

if __name__ == '__main__':
    app.run(debug=True)