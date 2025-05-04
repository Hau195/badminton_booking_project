from database import db
from datetime import datetime

class Reservation(db.Model):
    __tablename__ = 'reservations'
    
    reservation_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    court_id = db.Column(db.Integer, db.ForeignKey('courts.court_id'), nullable=False)
    time_slot_id = db.Column(db.Integer, db.ForeignKey('timeslots.time_slot_id'), nullable=False)
    reservation_time = db.Column(db.DateTime, default=datetime.now)
    status = db.Column(db.String(20), default='pending')  # pending, confirmed, cancelled, completed
    notes = db.Column(db.Text)
    
    # Relationships
    user = db.relationship('User', back_populates='reservations')
    court = db.relationship('Court', back_populates='reservations')
    time_slot = db.relationship('TimeSlot', back_populates='reservation', single_parent=True)

    def confirm_reservation(self):
        if self.status == 'pending' and self.time_slot.reserve():
            self.status = 'confirmed'
            db.session.commit()
            return True
        return False

    def cancel_reservation(self):
        if self.status in ['pending', 'confirmed']:
            self.status = 'cancelled'
            self.time_slot.release()
            db.session.commit()
            return True
        return False

    def __repr__(self):
        return f'<Reservation {self.reservation_id} by User {self.user_id}>'