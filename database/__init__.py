from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt



db = SQLAlchemy()
bcrypt = Bcrypt()

def init_app(app):
    db.init_app(app)
    bcrypt.init_app(app)
    with app.app_context():
        from database.court import Court
        from database.user import User
        from database.reservation import Reservation
        from database.timeslot import TimeSlot
        from database.admin import Admin
        
        db.create_all()  # Creates fresh tables
        _create_initial_data()

def _create_initial_data():
    from .user import User  # This relative import is okay here
    from database.admin import Admin

    if not User.query.filter_by(email='admin@badminton.com').first():
        
        admin = Admin(
            name='Admin',
            email='admin@badminton.com',
            password_hash=bcrypt.generate_password_hash('admin123').decode('utf-8'),
            is_admin=True,
            access_level='super'
        )
        db.session.add(admin)
        db.session.commit()
        print(admin.user_id)

        
        