from models import db, User, Department, Student, Admin, Supervisor, Complaint, Appeal
from werkzeug.security import generate_password_hash

def seed_data():
    # Wipe the database
    db.drop_all()
    db.create_all()

    # Create departments
    dept1 = Department(dept_name="Department of Finance")
    dept2 = Department(dept_name="Department of Student Housing and Residence Life")
    dept3 = Department(dept_name="Office of Registrar")
    dept4 = Department(dept_name="Department of Student Governance and Development")
    dept5 = Department(dept_name="Department of Facilities Management")
    dept6 = Department(dept_name="Information Technology Support (ITSS)")
    dept7 = Department(dept_name="Library Services")
    dept8 = Department(dept_name="Department of Student Health and Wellness")
    dept9 = Department(dept_name="International Education and Partnerships Office")
    dept10 = Department(dept_name="Department of Protection Services")
    db.session.add_all([dept1, dept2, dept3, dept4, dept5, dept6, dept7, dept8, dept9, dept10])

    # Create users
    user1 = User(fname="John", lname="Doe", email="john.doe@dut4life.ac.za", phone="1234567890",
                 password=generate_password_hash("password123"), role="student")
    user2 = User(fname="Jane", lname="Smith", email="jane.smith@dut4life.ac.za", phone="0987654321",
                 password=generate_password_hash("password123"), role="admin")
    user3 = User(fname="Alice", lname="Brown", email="alice.brown@dut4life.ac.za", phone="1122334455",
                 password=generate_password_hash("password123"), role="supervisor")
    db.session.add_all([user1, user2, user3])

    # Create student
    student1 = Student(user_id=1)
    db.session.add(student1)

    # Create admin
    admin1 = Admin(user_id=2, dept_id=1)
    db.session.add(admin1)

    # Create supervisor
    supervisor1 = Supervisor(user_id=3, dept_id=1)
    db.session.add(supervisor1)

    # Create complaints
    complaint1 = Complaint(comp_descr="Issue with course material", comp_dept="Computer Science",
                            stud_id=1, comp_anonymous=False)
    db.session.add(complaint1)

    # Create appeals
    appeal1 = Appeal(appeal_reason="Unresolved complaint", comp_id=1, stud_id=1)
    db.session.add(appeal1)

    # Commit all changes
    db.session.commit()
    print("Database wiped and seeded successfully!")

if __name__ == "__main__":
    from app import app  # Import the Flask app to initialize the context
    with app.app_context():
        seed_data()
