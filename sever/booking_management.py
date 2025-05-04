from datetime import datetime, timedelta
from database import db
from database.court import Court
from database.reservation import Reservation
from database.timeslot import TimeSlot
from database.user import User

class BookingManagement:
    @staticmethod
    def create_reservation(user: User, court: Court, start_time: datetime, duration: int) -> Reservation:
        """Create a new reservation"""
        try:
            # Calculate end time
            end_time = start_time + timedelta(minutes=duration)
            
            # Check court availability
            if not court.availability_status:
                raise ValueError("Court is not available")
            
            # Find or create time slot
            time_slot = TimeSlot.query.filter_by(
                court_id=court.court_id,
                start_time=start_time,
                end_time=end_time
            ).first()
            
            if not time_slot:
                time_slot = TimeSlot(
                    court_id=court.court_id,
                    start_time=start_time,
                    end_time=end_time,
                    is_available=True,
                    price=25.00  # Default price
                )
                db.session.add(time_slot)
            
            if not time_slot.is_available:
                raise ValueError("Time slot is already booked")
            
            # Create reservation
            reservation = Reservation(
                user_id=user.user_id,
                court_id=court.court_id,
                time_slot_id=time_slot.time_slot_id,
                status='confirmed'
            )
            
            # Update time slot availability
            time_slot.is_available = False
            time_slot.reservation = reservation
            
            db.session.add(reservation)
            db.session.commit()
            
            return reservation
            
        except Exception as e:
            db.session.rollback()
            raise e

    @staticmethod
    def cancel_reservation_management(reservation_id: int) -> bool:
        # Create a temporary timeslot to satisfy NOT NULL constraint
        try:
            temp_timeslot = TimeSlot(
                court_id=1,  
                start_time=datetime.now(),
                end_time=datetime.now(),
                is_available=True,
                price=0
            )
            db.session.add(temp_timeslot)
            db.session.flush() 

            reservation = db.session.query(Reservation).\
                filter_by(reservation_id=reservation_id).\
                with_for_update().\
                first()
            
            original_timeslot = reservation.time_slot
            
           
            reservation.time_slot_id = temp_timeslot.time_slot_id
            db.session.flush()
            
            
            original_timeslot.is_available = True
            original_timeslot.reservation = None
            
            
            reservation.status = 'cancelled'
            
            db.session.commit()
            return True
            
        except Exception as e:
            db.session.rollback()
            return False

    @staticmethod
    def get_available_time_slots(court_id: int, date: datetime) -> list:
        """Get available time slots for a court on specific date"""
        start_of_day = datetime.combine(date, datetime.min.time())  
        end_of_day = datetime.combine(date, datetime.max.time()) 
        
        return TimeSlot.query.filter(
            TimeSlot.court_id == court_id,
            TimeSlot.start_time >= start_of_day,
            TimeSlot.end_time <= end_of_day,
            TimeSlot.is_available == True
        ).all()

    @staticmethod
    def get_reservations_by_user(user_id: int) -> list:
        """Get all reservations for a specific user"""
        return Reservation.query.filter_by(user_id=user_id).all()