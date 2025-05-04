from flask import Flask, render_template, request, jsonify, redirect
from config import Config
from database import db, init_app
from sever.member_management import MemberManagement
from sever.authentication import *
from sever.booking_management import BookingManagement
from database.user import User
from database.admin import *
from database.court import Court
from database.reservation import Reservation
from database.timeslot import TimeSlot
from datetime import datetime, timedelta
from functools import wraps
#from werkzeug.security import generate_password_hash, check_password_hash
import jwt

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Initialize extensions
    init_app(app)
    
    return app

app = create_app()

@app.route('/register')
def register_page():
    return render_template('register.html')

@app.route('/api/register', methods=['POST'])
def register_user():
    try:
        data = request.get_json()
        # Validate required fields
        if not all(key in data for key in ['name', 'email', 'password', 'confirm-password']):
            return jsonify({'success': False, 'message': 'All fields are required'})

        # Check if passwords match
        if data['password'] != data['confirm-password']:
            return jsonify({'success': False, 'message': 'Passwords do not match'})
        
        # Check if user exists
        if User.query.filter_by(email=data['email']).first():
            return jsonify({'success': False, 'message': 'Email exists'})

        new_user = User(
            name=data['name'],
            email=data['email'],
            password_hash=data['password'],
            is_admin=False
        )
        
        MemberManagement.registerMember(new_user)
        
        return jsonify({
            'success': True,
            'message': 'Registration successful!',
            'redirect': '/login'
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        
        # Check for token in cookies
        token = request.cookies.get('auth_token')
        
        if not token:
            return jsonify({
                'success': False,
                'message': 'Token is missing',
                'redirect': '/login'
            })
            
        try:
            # Decode token with expiration check
            data = jwt.decode(token, app.config['JWT_SECRET_KEY'], algorithms=["HS256"])
            current_user = User.query.get(data['user_id'])
            
            if not current_user:
                return jsonify({
                    'success': False,
                    'message': 'User not found',
                    'redirect': '/login'
                })
                
        except jwt.ExpiredSignatureError:
            return jsonify({
                'success': False,
                'message': 'Token has expired',
                'redirect': '/login'
            })
        except jwt.InvalidTokenError:
            return jsonify({
                'success': False,
                'message': 'Invalid token',
                'redirect': '/login'
            })
            
        return f(current_user, *args, **kwargs)
    return decorated

# Add this helper function near your token_required decorator
def admin_required(f):
    @wraps(f)
    def decorated(current_user, *args, **kwargs):
        
        if not current_user.is_admin:
            return jsonify({
                'success': False,
                'message': 'Admin access required',
                'redirect': '/dashboard'
            }), 403
        
        
        admin = db.session.query(Admin).join(User).filter(
        User.user_id == current_user.user_id,
        User.is_admin == True).first()

        if not admin:
            return jsonify({
                'success': False,
                'message': 'Admin profile not found',
                'redirect': '/dashboard'
            }), 403
  
        return f(admin, *args, **kwargs)
    return decorated



@app.route('/login', methods=['GET'])
def login_page():
    return render_template('login.html')

@app.route('/api/login', methods=['POST'])
def login():
    try:
        
        # Handle both JSON and form data
        if request.content_type == 'application/json':
            data = request.get_json()
        else:
            data = request.form.to_dict()
           
        # Validate required fields
        if not data or 'email' not in data or 'password' not in data:
            return jsonify({"success": False, "message": "Email and password are required"})
        
        
        user = Authentication.validate_user_login(data['email'], data['password'])
        # Validate required fields
        if user == None:
            return jsonify({"success": False, "message": "Email or/and password incorrect"})
        
        # Create JWT token
        token = jwt.encode({
            'user_id': user.user_id,
            'exp': datetime.utcnow() + app.config['JWT_EXPIRATION_DELTA']
        }, app.config['JWT_SECRET_KEY'], algorithm="HS256")
        
        # Create response with cookie
        response = jsonify({
            'success': True,
            'token' : token,
            'message': 'Login successful!',
            'redirect': '/dashboard',
            'user': {
                'id': user.user_id,
                'name': user.name,
                'email': user.email,
                'is_admin': user.is_admin
            }
        })
        
        # Set secure HTTP-only cookie
        response.set_cookie(
            'auth_token',
            value=token,
            httponly=True,
            secure=True,  # Enable in production (requires HTTPS)
            samesite='Lax'
            # max_age=3600  # 1 hour expiration (matches JWT expiry)
        )
        
        return response

    except Exception as e:
        app.logger.error(f"Unexpected error: {str(e)}")
        return jsonify({"success": False, "message": "Internal server error"}), 500

@app.route('/dashboard')
@token_required 
def dashboard(current_user):
    try:
        # Get any additional user data needed for the dashboard
        user_data = {
            'id': current_user.user_id,
            'name': current_user.name,
            'email': current_user.email,
            'is_admin': current_user.is_admin,
        }
        
        return render_template('dashboard.html', user=user_data)
        
    except Exception as e:
        app.logger.error(f"Dashboard error: {str(e)}")
        return redirect('/login?error=dashboard_error')
    
@app.route('/api/check-auth', methods=['GET'])
@token_required
def check_auth(current_user):
    if current_user:
        return jsonify(success=True, user={
            'id': current_user.user_id,
            'name': current_user.name,
            'email': current_user.email,
            'is_admin': current_user.is_admin
        })
    else:
        return jsonify(success=False), 401
    
@app.route('/api/logout', methods=['POST'])
def logout():
    response = jsonify({'success': True})
    response.delete_cookie('auth_token')
    return response

# Court Management Routes
@app.route('/admin/manage-court')
@token_required
@admin_required
def manage_courts_page(admin):
    """Render the court management template for admins"""
    return render_template('manage-court.html', 
                         page_title="Court Management",
                         admin=admin)


# API endpoints
@app.route('/api/admin/courts', methods=['GET', 'POST'])
@token_required
@admin_required
def handle_courts(admin):
    if request.method == 'GET':
        courts = Court.query.order_by(Court.court_id).all()
        return jsonify({
            'courts': [{
                'court_id': court.court_id,
                'court_type': court.court_type,
                'location': court.location,
                'availability_status': court.availability_status,
                'opening_time': court.opening_time.strftime('%H:%M'),
                'closing_time': court.closing_time.strftime('%H:%M')
            } for court in courts]
        })
    elif request.method == 'POST':
        data = request.get_json()
        try:
            # Validate required fields
            required_fields = ['court_type', 'location', 'opening_time', 'closing_time']
            if not all(field in data for field in required_fields):
                return jsonify({'success': False, 'error': 'Missing required fields'}), 400

            availability = data.get('availability_status', 'true')
            if isinstance(availability, str):
                data['availability_status'] = availability.lower() == 'true'                                            

            # Create new court
            new_court = Court(
                court_type=data['court_type'],
                location=data['location'],
                availability_status=data.get('availability_status', True),
                opening_time=datetime.strptime(data['opening_time'], '%H:%M').time(),
                closing_time=datetime.strptime(data['closing_time'], '%H:%M').time()
            )
            
            
            if not admin:
                return jsonify({'success': False, 'error': 'Admin not found'}), 500

            if admin.add_court(new_court):
                return jsonify({
                    'success': True,
                    'court': {
                        'id': new_court.court_id,
                        'type': new_court.court_type,
                        'location': new_court.location
                    }
                }), 201
            return jsonify({'success': False, 'error': 'Failed to add court'}), 400
                
        except ValueError as e:
            return jsonify({'success': False, 'error': f'Invalid time format: {str(e)}'}), 400
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Court creation error: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/admin/courts/<int:court_id>', methods=['PUT', 'DELETE'])
@token_required
@admin_required
def handle_single_court(current_user, court_id):
    court = Court.query.get_or_404(court_id)
    if request.method == 'PUT':
        data = request.get_json()

        try:
            court.court_type = data.get('court_type', court.court_type)
            court.location = data.get('location', court.location)
            availability_status = data.get('availability_status')
            if availability_status is not None:
                court.availability_status = availability_status.lower() == 'true' \
                if isinstance(availability_status, str) else bool(availability_status)
            if 'opening_time' in data:
                court.opening_time = datetime.strptime(data['opening_time'], '%H:%M').time()
            # Else keeps existing opening_time (default handled by model)
            
            if 'closing_time' in data:
                court.closing_time = datetime.strptime(data['closing_time'], '%H:%M').time()
            # Else keeps existing closing_time

            db.session.commit()
            return jsonify({"message": "Court updated successfully"}), 200
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 400
    elif request.method == 'DELETE':
        db.session.delete(court)
        db.session.commit()
        return jsonify({'success': True})

@app.route('/admin/reservations')
@token_required
@admin_required
def admin_reservations_page(admin):
    """Render admin reservations management page"""
    return render_template('all-reservation.html')

@app.route('/api/admin/reservations', methods=['GET'])
@token_required
@admin_required
def get_all_reservations(admin):
    """Get all reservations with filtering options"""
    try:
        # Get query parameters
        status = request.args.get('status')
        date = request.args.get('date')
        court_id = request.args.get('court_id')
        user_id = request.args.get('user_id')
        
        # Base query
        query = Reservation.query.join(User).join(Court).join(TimeSlot)
        
        # Apply filters
        if status:
            query = query.filter(Reservation.status == status)
        if date:
            query = query.filter(db.func.date(TimeSlot.start_time) == date)
        if court_id:
            query = query.filter(Reservation.court_id == court_id)
        if user_id:
            query = query.filter(Reservation.user_id == user_id)
        
        # Execute query
        reservations = query.order_by(TimeSlot.start_time.desc()).all()
        
        return jsonify({
            'reservations': [{
                'id': r.reservation_id,
                'user': {
                    'id': r.user.user_id,
                    'name': r.user.name,
                    'email': r.user.email
                },
                'court': {
                    'id': r.court.court_id,
                    'type': r.court.court_type,
                    'location': r.court.location
                },
                'time_slot': {
                    'start': r.time_slot.start_time.isoformat(),
                    'end': r.time_slot.end_time.isoformat()
                },
                'status': r.status,
                'created_at': r.reservation_time.isoformat(),
                'can_modify': r.status in ['pending', 'confirmed', 'cancelled', 'completed']
            } for r in reservations]
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/admin/reservations/<int:reservation_id>', methods=['PUT', 'DELETE'])
@token_required
@admin_required
def manage_reservation(admin, reservation_id):
    """Update or delete a reservation"""
    try:
        reservation = Reservation.query.get_or_404(reservation_id)
        
        if request.method == 'PUT':
            data = request.get_json()
            if 'status' in data:
                if data['status'] == 'cancelled':
                    reservation.cancel_reservation()
                else:
                    reservation.status = data['status']
                    db.session.commit()
            return jsonify({'success': True})
            
        elif request.method == 'DELETE':
            db.session.delete(reservation)
            db.session.commit()
            return jsonify({'success': True})
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


# Route to display the member management page
@app.route('/admin/member-management')
@token_required
@admin_required
def member_management_page(admin):
    """Render the member management HTML page"""
    return render_template('member-management.html')

# API endpoint to get all members
@app.route('/api/members', methods=['GET'])
@token_required
@admin_required
def get_all_members(admin):
    """Get list of all members for the member management page"""
    try:
        members = User.query.order_by(User.name.asc()).all()
        return jsonify({
            'success': True,
            'members': [{
                'id': member.user_id,
                'name': member.name,
                'email': member.email,
                'created_at': member.created_at.strftime('%Y-%m-%d %H:%M:%S') if member.created_at else 'Not available',
                'is_admin': member.is_admin
            } for member in members]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# API endpoint to register new member
@app.route('/api/members/register', methods=['POST'])
@token_required
@admin_required
def register_member(admin):
    """Handle member registration from the form"""
    try:       
        data = request.get_json()

        # Validate required fields
        if not all(key in data for key in ['name', 'email', 'password', 'confirm_password']):
            return jsonify({'success': False, 'message': 'All fields are required'}), 400
        
        # Check if passwords match
        if data['password'] != data['confirm_password']:
            return jsonify({'success': False, 'message': 'Passwords do not match'}), 400
        new_user = User(
            name=data['name'],
            email=data['email'],
            password_hash=data['password'],
            is_admin=False
        )
        
        MemberManagement.registerMember(new_user)
        
        return jsonify({
            'success': True,
            'message': 'Registration successful!',
            'redirect': 'login'
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


# API endpoint to update member
@app.route('/api/members/update', methods=['POST'])
@token_required
@admin_required
def update_member(admin):
    """Handle member updates from the form"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if 'email' not in data:
            return jsonify({'success': False, 'error': 'Email is required to identify member'}), 400
            
        # Find existing user
        existing_user = MemberManagement.getMemberByEmail(data['email'])
        if not existing_user:
            return jsonify({'success': False, 'error': 'Member not found'}), 404
            
        # Create user object with updates
        updated_user = User(
            user_id=existing_user.user_id,
            name=data.get('name', existing_user.name),
            email=data.get('email', existing_user.email),
            password_hash=data.get('password', existing_user.password_hash),
            is_admin=data.get('is_admin', existing_user.is_admin),
            created_at=existing_user.created_at  # Preserve original creation date
        )
        
        # Use your MemberManagement class
        if MemberManagement.updateMemberDetails(updated_user):
            return jsonify({
                'success': True,
                'message': 'Member updated successfully',
                'member': {
                    'id': updated_user.user_id,
                    'name': updated_user.name,
                    'email': updated_user.email,
                    'created_at': updated_user.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    'is_admin': updated_user.is_admin
                }
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to update member'}), 400
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# API endpoint to delete member
@app.route('/api/members/delete', methods=['POST'])
@token_required
@admin_required
def delete_member(admin):
    """Handle member deletion from the form"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if 'email' not in data:
            return jsonify({'success': False, 'error': 'Email is required to identify member'}), 400
            
        # Find existing user
        user_to_delete = MemberManagement.getMemberByEmail(data['email'])
        if not user_to_delete:
            return jsonify({'success': False, 'error': 'Member not found'}), 404
            
        # Use your MemberManagement class
        if MemberManagement.removeMember(user_to_delete):
            return jsonify({
                'success': True,
                'message': 'Member deleted successfully'
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to delete member'}), 400
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/book-court', methods=['GET'])
@token_required
def book_court_page(current_user):
    """Render booking page with court availability based on opening hours"""
    try:
        # Get current time and initialize booking window
        now = datetime.now()
        current_time = now.time()
        today = now.date()
        booking_window_days = 14  # Show availability for 2 weeks
        
        # 1. Get all active courts
        courts = Court.query.filter_by(availability_status=True).all()
        
        # 2. Generate available time slots for each court
        available_slots = {}
        
        for court in courts:
            # Generate slots for each day in booking window
            court_slots = []
            
            for day in range(booking_window_days):
                target_date = today + timedelta(days=day)
                
                # Skip if court is closed on this day (add your logic here)
                # if target_date.weekday() in court.closed_days:
                #     continue
                
                # Calculate effective opening/closing times
                opening = datetime.combine(target_date, court.opening_time)
                closing = datetime.combine(target_date, court.closing_time)
                
                # Generate 1-hour slots
                slot_start = max(opening, datetime.now())  # Don't show past slots
                while slot_start + timedelta(hours=1) <= closing:
                    # Check if slot is already booked
                    existing_booking = Reservation.query.join(TimeSlot).filter(
                        TimeSlot.court_id == court.court_id,
                        TimeSlot.start_time == slot_start
                    ).first()
                    
                    if not existing_booking:
                        court_slots.append({
                            'date': target_date,
                            'start': slot_start.time().strftime('%H:%M'),
                            'end': (slot_start + timedelta(hours=1)).time().strftime('%H:%M'),
                            'datetime': slot_start.isoformat()
                        })
                    
                    slot_start += timedelta(hours=1)
            
            available_slots[court.court_id] = {
                'court_name': f"{court.court_type} - {court.location}",
                'slots': court_slots
            }
        
        return render_template(
            'book-court.html',
            courts=courts,
            available_slots=available_slots,
            min_date=today,
            max_date=today + timedelta(days=booking_window_days),
            current_time=current_time.strftime('%H:%M')
        )
        
    except Exception as e:
        app.logger.error(f"Booking page error: {str(e)}")
        return render_template('error.html', 
                            message="Court booking system is currently unavailable"), 500

@app.route('/api/book-court', methods=['POST'])
@token_required
def dev_book_court(current_user):
    """Development route for testing court booking logic"""
    try:
        # 1. Get and validate input data
        data = request.get_json()
        
        required_fields = ['court_id', 'start_time', 'duration']
        if not all(field in data for field in required_fields):
            return jsonify({"error": f"Missing required fields: {required_fields}"}), 400

        # Try multiple datetime formats
        duration = int(data['duration'])
        start_time_str = data['start_time']
        try:
            start_time = datetime.strptime(start_time_str, "%Y-%m-%dT%H:%M:%S")  # ISO format
        except ValueError:
            try:
                start_time = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M")  # Space separator
            except ValueError:
                start_time = datetime.fromisoformat(start_time_str)  # Python 3.7+

        # 2. Fetch user and court
        user = User.query.get(current_user.user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        court = Court.query.get(data['court_id'])
        if not court:
            return jsonify({"error": "Court not found"}), 404

        # 3. Use your create_reservation function
        reservation = BookingManagement.create_reservation(
            user=user,
            court=court,
            start_time=start_time,
            duration=duration
        )
        
        # 4. Return success response
        return jsonify({
            "message": "Reservation created successfully",
            "reservation_id": reservation.reservation_id,
            "court_id": court.court_id,
            "start_time": start_time.isoformat(),
            "end_time": (start_time + timedelta(minutes=duration)).isoformat(),
            "status": "confirmed"
        }), 201

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Unexpected error", "details": str(e)}), 500

@app.route('/my-reservations')
@token_required
def my_reservations_page(current_user):
    """Render the user's reservations page"""
    try:
        reservations = Reservation.query.filter_by(user_id=current_user.user_id)\
            .join(Court)\
            .join(TimeSlot)\
            .order_by(TimeSlot.start_time.desc())\
            .all()
        
        return render_template(
            'my-reservation.html',
            reservations=reservations,
            current_time=datetime.now()
        )
    except Exception as e:
        app.logger.error(f"Reservations page error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/my-reservations', methods=['GET'])
@token_required
def get_my_reservations(current_user):
    """API endpoint for user reservations"""
    try:
        reservations = Reservation.query.filter_by(user_id=current_user.user_id)\
            .join(Court)\
            .join(TimeSlot)\
            .order_by(TimeSlot.start_time.desc())\
            .all()
        
        return jsonify({
            'reservations': [{
                'id': r.reservation_id,
                'court': r.court.court_type,
                'location': r.court.location,
                'date': r.time_slot.start_time.date().isoformat(),
                'start_time': r.time_slot.start_time.time().strftime('%H:%M'),
                'end_time': r.time_slot.end_time.time().strftime('%H:%M'),
                'status': r.status,
                'can_cancel': r.status == 'confirmed' and 
                             r.time_slot.start_time > datetime.now()
            } for r in reservations]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/reservations/<int:reservation_id>/cancel', methods=['POST'])
@token_required
def cancel_reservation(current_user, reservation_id):
    """Cancel a reservation"""
    try:
        reservation = Reservation.query.filter_by(
            reservation_id=reservation_id,
            user_id=current_user.user_id
        ).first_or_404()
        
        if reservation.cancel_reservation():
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'Cannot cancel this reservation'}), 400
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
