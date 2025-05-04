from datetime import datetime
from database import db, bcrypt

class User(db.Model):
    __tablename__ = 'users'
    
    user_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_admin = db.Column(db.Boolean, default=False)
    type = db.Column(db.String(50))  # polymorphic field
    
    # Relationships
    reservations = db.relationship('Reservation', back_populates='user', cascade='all, delete-orphan')
    
    __mapper_args__ = {
        'polymorphic_identity': 'user',
        'polymorphic_on': type,
        'with_polymorphic': '*'
    }    

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        # Generate a new bcrypt hash for the password
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def verify_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

    def create_account(self):
        try:
            db.session.add(self)
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            print(f"Error creating account: {e}")
            return False


    def login(self, password):
        return self.verify_password(password)

    def view_reservations(self):
        return self.reservations

    def __repr__(self):
        return f'<User {self.email}>'