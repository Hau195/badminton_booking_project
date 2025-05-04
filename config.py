import os
from dotenv import load_dotenv
import datetime

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///badminton.db')
    BCRYPT_LOG_ROUNDS = 12
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = 'your-secret-key-here'
    JWT_EXPIRATION_DELTA = datetime.timedelta(minutes=15)