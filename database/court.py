from database import db
from datetime import time

class Court(db.Model):
    __tablename__ = 'courts'
    
    
    court_id = db.Column(db.Integer, primary_key=True)
    court_type = db.Column(db.String(50), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    availability_status = db.Column(db.Boolean, default=True)
    opening_time = db.Column(db.Time, default=time(8, 0)) 
    closing_time = db.Column(db.Time, default=time(22, 0))  
    
    # Relationships
    time_slots = db.relationship('TimeSlot', back_populates='court', cascade='all, delete-orphan')
    reservations = db.relationship('Reservation', back_populates='court')


    def get_available_time_slots(self):
        from .timeslot import TimeSlot
        return TimeSlot.query.filter_by(court_id=self.court_id, is_available = True).all()

    def update_availability(self, status):
        self.availability_status = status
        db.session.commit()
        return True

    def __repr__(self):
        return f'<Court {self.court_type} at {self.location}>'