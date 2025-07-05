from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin,
    login_user, logout_user,
    login_required, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SECRET_KEY'] = 'your_secret_key_here'
db = SQLAlchemy(app)

# Flask-Login setup
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Association table for user–interests
author_interest = db.Table(
    'user_interest',
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
    interests = db.relationship('Interest', secondary=author_interest, backref='users')
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

with app.app_context():
    db.create_all()

# Helper functions
def calculate_match_percentage(mentee, mentor):
    mentee_ids = {i.id for i in mentee.interests}
    mentor_ids = {i.id for i in mentor.interests}
    common = mentee_ids & mentor_ids
    return (len(common) / len(mentee_ids) * 100) if mentee_ids else 0

# Routes
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = request.form['username']
        p = request.form['password']
        user = User.query.filter_by(username=u).first()
        if user and check_password_hash(user.password, p):
            user.last_login = datetime.utcnow()
            db.session.commit()
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Invalid credentials', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        u = request.form['username']
        pw = generate_password_hash(request.form['password'])
        role = request.form['role']
        new = User(username=u, password=pw, role=role)
        db.session.add(new)
        db.session.commit()
        login_user(new)
        flash('Account created!', 'success')
        return redirect(url_for('profile'))
    return render_template('register.html')

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    # …
    return render_template('profile.html', all_interests=Interest.query.all())

@app.route('/matches')
@login_required
def matches():
    # …
    return render_template('matches.html', matches=[])

@app.route('/dashboard')
@login_required
def dashboard():
    # …
    return render_template('dashboard.html')

@app.route('/resources')
@login_required
def resources():
    return render_template('resources.html', resources=Resource.query.all())

@app.route('/chatbot', methods=['POST'])
@login_required
def chatbot():
    # …
    return "Bot reply"

if __name__ == '__main__':
    app.run(debug=True)