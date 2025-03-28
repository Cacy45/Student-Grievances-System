import sys

from models import (
    db,
    User,
    Department,
    Student,
    Admin,
    Supervisor,
    Complaint,
    Appeal,
    Feedback,
)
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta


def seed_data():
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
    db.session.add_all(
        [dept1, dept2, dept3, dept4, dept5, dept6, dept7, dept8, dept9, dept10]
    )

    # Create users
    user1 = User(
        fname="John",
        lname="Doe",
        email="john.doe@dut4life.ac.za",
        phone="1234567890",
        password=generate_password_hash("password123"),
        role="student",
    )
    user2 = User(
        fname="Jane",
        lname="Smith",
        email="jane.smith@dut4life.ac.za",
        phone="0987654321",
        password=generate_password_hash("password123"),
        role="admin",
    )
    user3 = User(
        fname="Alice",
        lname="Brown",
        email="alice.brown@dut4life.ac.za",
        phone="1122334455",
        password=generate_password_hash("password123"),
        role="supervisor",
    )
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
    complaint1 = Complaint(
        comp_id=1,
        comp_title="Issue with course material",
        comp_doc=None,
        comp_descr="Issue with course material",
        comp_dept=dept1.dept_name,
        stud_id=1,
        comp_anonymous=False,
    )
    db.session.add(complaint1)

    # Example resolved complaint for feedback
    resolved_complaint = Complaint(
        comp_id=2,
        comp_title="Wi-Fi Issues in Library",
        comp_descr="The Wi-Fi connection in the library is very slow and keeps disconnecting.",
        comp_dept=dept1.dept_name,
        comp_status="Resolved",
        comp_datefiled=datetime.now() - timedelta(days=7),
        comp_dateresolved=datetime.now() - timedelta(days=1),
        stud_id=1,
        admin_id=1
    )
    db.session.add(resolved_complaint)
    db.session.commit()
    
    resolved_complaint_no_feedback = Complaint(
        comp_id=3,
        comp_title="Complaint about library hours",
        comp_descr="The library should be open longer hours during exam periods.",
        comp_dept=dept3.dept_name,
        comp_status="Resolved",
        comp_datefiled=datetime.now() - timedelta(days=3),
        stud_id=1,
        admin_id=1
    )
    db.session.add(resolved_complaint_no_feedback)
    db.session.commit()

    # Create appeals
    appeal1 = Appeal(appeal_reason="Unresolved complaint", comp_id=1, stud_id=1)
    db.session.add(appeal1)

    # Create feedback
    example_feedback = Feedback(
        service_quality="Excellent",
        staff_behaviour="Good",
        overall_experience="Very Satisfied",
        comments="The IT team resolved my Wi-Fi issue quickly and professionally.",
        comp_id=2,
        stud_id=1
    )
    db.session.add(example_feedback)
    db.session.commit()

    # Commit all changes
    db.session.commit()
    print("Database wiped and seeded successfully!")


if __name__ == "__main__":
    from app import app

    with app.app_context():
        # Wipe the database
        db.drop_all()
        db.create_all()
        if not sys.argv[1:] or sys.argv[1] != "--no-seed":
            # Seed the database
            seed_data()
