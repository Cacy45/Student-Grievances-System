from app import app  # Import your Flask app
from models import db, User, Student

# Ensure queries run inside application context
with app.app_context():
    user = User.query.filter_by(email="22324091@dut4life.ac.za").first()
    
    if user:
        new_student = Student(user_id=user.user_id, stud_id=22324091)  # Replace `12345` with a valid `stud_id`
        db.session.add(new_student)
        db.session.commit()
        print("Student record created!")

