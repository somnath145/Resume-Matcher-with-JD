from flask import Blueprint, render_template, request, url_for, flash, session, redirect
from app import db
from app.models import Users
from werkzeug.security import generate_password_hash, check_password_hash

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']
        
        user = Users.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            flash("Login successful!")
        else:
            flash("Invalid username or password.")
        return redirect(url_for('task.upload_resume'))
    
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash("Logged out.",'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/register', methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']
        
        # Check if user already exists
        existing_user = Users.query.filter_by(username=username).first()
        if existing_user:
            flash("Username already exists.")
            return redirect(url_for('auth.register'))

        # Hash password and save
        hashed_password = generate_password_hash(password)
        new_user = Users(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        
        flash("Registration successful. Please login.")
        return redirect(url_for('auth.login'))
    
    return render_template('register.html')