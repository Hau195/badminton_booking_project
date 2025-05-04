from database import db, bcrypt
from database.user import User

class MemberManagement:
    @staticmethod
    def registerMember(user: User) -> bool:
        """Register a new member"""
        try:
            # Check if email already exists
            if User.query.filter_by(email=user.email).first():
                return False
                
            # Hash the password before saving
            user.password_hash = bcrypt.generate_password_hash(user.password_hash).decode('utf-8')
            
            db.session.add(user)
            db.session.commit()
            return True
            
        except Exception:
            db.session.rollback()
            return False

    @staticmethod
    def updateMemberDetails(user: User) -> bool:
        """Update member details including password if changed"""
        try:
            existing_user = User.query.get(user.user_id)
            if not existing_user:
                return False
                
            # Update basic details
            existing_user.name = user.name
            existing_user.email = user.email
            
            # Only update password if it's different
            if user.password_hash != existing_user.password_hash:
                existing_user.password_hash = bcrypt.generate_password_hash(user.password_hash).decode('utf-8')
                
            db.session.commit()
            return True
            
        except Exception:
            db.session.rollback()
            return False

    @staticmethod
    def removeMember(user: User) -> bool:
        """Remove a member account"""
        try:
            db.session.delete(user)
            db.session.commit()
            return True
        except Exception:
            db.session.rollback()
            return False

    @staticmethod
    def getMemberByEmail(email: str) -> User:
        """Retrieve member by email"""
        return User.query.filter_by(email=email).first()