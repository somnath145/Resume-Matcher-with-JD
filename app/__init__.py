from flask import Flask
from flask_sqlalchemy import SQLAlchemy

#create database object globally
db = SQLAlchemy()

def create_app():
    app = Flask(__name__)

    app.config['SECRET_KEY'] = 'your-secret-key'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///resume.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app) # connect database(db) with app

    from app.routes.auth import auth_bp
    from app.routes.task import task_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(task_bp)
    
    return app