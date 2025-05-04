from database import db
from datetime import datetime, timedelta

class TimeSlot(db.Model):
    __tablename__ = 'timeslots'
    
    time_slot_id = db.Column(db.Integer, primary_key=True)
    court_id = db.Column(db.Integer, db.ForeignKey('courts.court_id'), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    is_available = db.Column(db.Boolean, default=1)
    price = db.Column(db.Float, default=0.0)
    
    # Relationships
    court = db.relationship('Court', back_populates='time_slots')
    reservation = db.relationship(
    'Reservation', 
    back_populates='time_slot',
    uselist=False,
    cascade='save-update, merge'  # Add this
    )

    def is_available_check(self):
        return self.is_available

    def reserve(self):
        if self.is_available:
            self.is_available = False
            db.session.commit()
            return True
        return False

    def release(self):
        self.is_available = True
        db.session.commit()
        return True

    def duration(self):
        return (self.end_time - self.start_time).total_seconds()

    def __repr__(self):
        return f'<TimeSlot {self.start_time} to {self.end_time}>'