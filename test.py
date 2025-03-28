import pytest
from models import db, User, Department, Student, Admin, Supervisor, Complaint, Appeal, Feedback
from datetime import datetime

@pytest.fixture
def app():
    from flask import Flask
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

def test_user_creation(app):
    user = User(
        fname='John',
        lname='Doe',
        email='john@example.com',
        phone='1234567890',
        role='student'
    )
    user.set_password('password123')
    
    db.session.add(user)
    db.session.commit()
    
    assert user.user_id is not None
    assert user.check_password('password123')
    assert not user.check_password('wrongpassword')

def test_department_creation(app):
    dept = Department(dept_name='Computer Science')
    db.session.add(dept)
    db.session.commit()
    
    assert dept.dept_id is not None
    assert dept.dept_name == 'Computer Science'

def test_complaint_creation(app):
    # Create required relationships
    user = User(fname='Jane', lname='Smith', email='jane@example.com', 
                phone='9876543210', role='student')
    user.set_password('password123')
    db.session.add(user)
    
    student = Student(user=user)
    db.session.add(student)
    db.session.commit()
    
    complaint = Complaint(
        comp_title='Test Complaint',
        comp_descr='Test Description',
        comp_dept='Computer Science',
        stud_id=student.stud_id
    )
    db.session.add(complaint)
    db.session.commit()
    
    assert complaint.comp_id is not None
    assert complaint.comp_status == 'New'
    assert complaint.comp_anonymous == False

def test_appeal_creation(app):
    # Create required relationships
    user = User(fname='Bob', lname='Brown', email='bob@example.com', 
                phone='5555555555', role='student')
    user.set_password('password123')
    db.session.add(user)
    
    student = Student(user=user)
    db.session.add(student)
    
    complaint = Complaint(
        comp_title='Test Complaint',
        comp_descr='Test Description',
        comp_dept='Computer Science',
        stud_id=student.stud_id
    )
    db.session.add(complaint)
    db.session.commit()
    
    appeal = Appeal(
        appeal_reason='Test Appeal',
        comp_id=complaint.comp_id,
        stud_id=student.stud_id
    )
    db.session.add(appeal)
    db.session.commit()
    
    assert appeal.appeal_id is not None
    assert appeal.appeal_status == 'Pending'

def test_feedback_creation(app):
    # Create required relationships
    user = User(fname='Alice', lname='White', email='alice@example.com', 
                phone='1112223333', role='student')
    user.set_password('password123')
    db.session.add(user)
    
    student = Student(user=user)
    db.session.add(student)
    
    complaint = Complaint(
        comp_title='Test Complaint',
        comp_descr='Test Description',
        comp_dept='Computer Science',
        stud_id=student.stud_id
    )
    db.session.add(complaint)
    db.session.commit()
    
    feedback = Feedback(
        service_quality='Excellent',
        staff_behaviour='Good',
        overall_experience='Satisfied',
        comments='Test feedback',
        comp_id=complaint.comp_id,
        stud_id=student.stud_id
    )
    db.session.add(feedback)
    db.session.commit()
    
    assert feedback.feedback_id is not None
    assert feedback.service_quality == 'Excellent'
    assert feedback.complaint is not None
    assert feedback.student is not None
