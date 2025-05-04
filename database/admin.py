from database import db, bcrypt
from .user import User


class Admin(User):
    __tablename__ = 'admins'
    
    admin_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), primary_key=True)
    access_level = db.Column(db.String(50), default='basic')
    
    __mapper_args__ = {
        'polymorphic_identity': 'admin',
        'inherit_condition': (admin_id == User.user_id),
        'concrete': True  # Add this for concrete table inheritance
    }

    def __init__(self, **kwargs):
        # First create the User part
        user_kwargs = {
            'name': kwargs.pop('name'),
            'email': kwargs.pop('email'),
            'password_hash': kwargs.pop('password_hash'),
            'is_admin': True  # Always True for Admin instances
        }
        super().__init__(**user_kwargs)
        
        # Then set Admin-specific fields
        self.access_level = kwargs.get('access_level', 'basic')

    def add_court(self, court):
        print("check2!")
        from .court import Court
        if isinstance(court, Court):
            db.session.add(court)
            db.session.commit()
            return True
        return False

    def remove_court(self, court):
        from .court import Court
        if isinstance(court, Court):
            db.session.delete(court)
            db.session.commit()
            return True
        return False
    
    def view_court(self, court):
        from .court import Court
        return Court.query.all()

    def view_all_reservations(self):
        from .reservation import Reservation
        return Reservation.query.all()

    def __repr__(self):
        return f'<Admin {self.email}>'