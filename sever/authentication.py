from database import db, bcrypt
from database.user import *

class Authentication:
    @staticmethod
    def validate_user_login(email, password):
        # Basic input validation
        if not email or not password:
            return None

        # Normalize email (if your DB stores them lowercase)
        email = email.lower().strip()

        # Find user (use one query to avoid timing leaks)
        user = User.query.filter_by(email=email).first()
        # students = User.query.all()

        # for student in students:
        #     print(f'ID: {student.user_id}, Name: {student.name}, {student.password_hash}' )
        
        if user and user.verify_password(password):
            # Optional: Check if account is active
            if hasattr(user, 'is_active') and not user.is_active:
                return None
            return user

        # Return None if either user doesn't exist or password is wrong
        return None

    @staticmethod
    def hash_password(password):
        return bcrypt.generate_password_hash(password).decode('utf-8')

    @staticmethod
    def create_user(name, email, password, is_admin=False):
        try:
            user = User(
                name=name,
                email=email,
                password=password, 
                is_admin=is_admin
            )
            db.session.add(user)
            db.session.commit()
            return user
        except Exception as e:
            db.session.rollback()
            print(f"Error creating user: {e}")
            return None