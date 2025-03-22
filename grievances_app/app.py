from flask import Flask,render_template, request, redirect, url_for, flash, abort
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf.csrf import CSRFProtect
from models import User, Complaint, Department, Student, Admin , Supervisor
import os
from werkzeug.utils import secure_filename


app = Flask(__name__)

# Configure Database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///student_grievances.db'  
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_key'

csrf = CSRFProtect(app)

# Import db from models and initialize it properly
from models import db, User  
db.init_app(app)

migrate = Migrate(app, db) 

# ✅ Initialize LoginManager properly
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"  # Redirect unauthorized users to login page

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


"""
db = SQLAlchemy(app)
migrate = Migrate(app, db) "
""" 

# 💡 Move this import **AFTER** initializing `db` and `migrate`
import models as models  

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        fname = request.form['fname']
        lname = request.form['lname']
        email = request.form['email']
        phone = request.form['phone']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        role = request.form['role']

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('register'))

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email is already registered.', 'danger')
            return redirect(url_for('register'))

        # ✅ Create and Hash Password
        user = User(fname=fname, lname=lname, email=email, phone=phone, role=role)
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        # ✅ Create the appropriate profile based on role
        if role == "student":
            new_student = Student(user_id=user.user_id)  
            db.session.add(new_student)
        elif role == "admin":
            new_admin = Admin(user_id=user.user_id)
            db.session.add(new_admin)
        elif role == "supervisor":
            new_supervisor = Supervisor(user_id=user.user_id)
            db.session.add(new_supervisor)

        db.session.commit()

        flash('Account created successfully! You can now log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):  
            login_user(user)
            flash('Login successful!', 'success')

            # ✅ Ensure user has a valid profile & redirect accordingly
            if user.role == 'student':
                student = Student.query.filter_by(user_id=user.user_id).first()
                if student:
                    return redirect(url_for('student_dashboard'))
                else:
                    flash('Student profile missing. Contact admin.', 'danger')
            
            elif user.role == 'admin':
                admin = Admin.query.filter_by(user_id=user.user_id).first()
                if admin:
                    return redirect(url_for('admin_dashboard'))
                else:
                    flash('Admin profile missing. Contact support.', 'danger')

            elif user.role == 'supervisor':
                supervisor = Supervisor.query.filter_by(user_id=user.user_id).first()
                if supervisor:
                    return redirect(url_for('supervisor_dashboard'))
                else:
                    flash('Supervisor profile missing. Contact admin.', 'danger')

            return redirect(url_for('home'))  # Default fallback

        flash('Login failed. Check your email and password.', 'danger')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))

@app.route('/student_dashboard')
@login_required
def student_dashboard():
    return render_template('student_dashboard.html', user=current_user)

@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    return render_template('admin_dashboard.html')

@app.route('/supervisor_dashboard')
@login_required
def supervisor_dashboard():
    return render_template('supervisor_dashboard.html')

UPLOAD_FOLDER = 'static/uploads'  # Folder to store uploaded documents
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf', 'docx'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/submit_grievance", methods=["GET", "POST"])
def submit_grievance():
    if request.method == "POST":
        title = request.form.get("title")
        category = request.form.get("category")
        description = request.form.get("description")
        anonymous = request.form.get("anonymous") == "on"  # Checkbox checked = True
        student_id = request.form.get("stud_id")  # Only used if not anonymous

        # Handle file upload
        attachment = request.files.get("attachment")
        filename = None
        if attachment and allowed_file(attachment.filename):
            filename = secure_filename(attachment.filename)
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            attachment.save(filepath)

        # Determine student ID (if not anonymous)
        if anonymous:
            student_id = None
        else:
            student_id = int(student_id) if student_id else None

        # Create and save the complaint
        new_complaint = Complaint(
            comp_descr=description,
            comp_dept=category,
            comp_anonymous=anonymous,
            comp_doc=filename,
            stud_id=student_id,  # Can be NULL for anonymous complaints
        )

        db.session.add(new_complaint)
        db.session.commit()

        flash("Your grievance has been submitted successfully!", "success")
        return redirect(url_for("submit_grievance"))

    # Fetch departments for dropdown
    departments = Department.query.all()
    return render_template("submit_grievance.html", departments=departments)

@app.route('/view_grievances')
@login_required
def view_grievances():
    # Ensure the logged-in user is a student
    if current_user.role != 'student':
        flash("Access denied. Only students can view grievances.", "danger")
        return redirect(url_for('home'))

    # Fetch the student record linked to the current user
    student = Student.query.filter_by(user_id=current_user.user_id).first()

    # If no student record is found, show an error
    """
    if not student:
        flash("No student profile found. Please contact administration.", "warning")
        return redirect(url_for('student_dashboard'))
    """

    # Fetch all grievances for the student
    grievances = Complaint.query.filter_by(stud_id=student.stud_id).all()

    return render_template('view_grievances.html', grievances=grievances)


# ================= Grievance Detail Route ================= #
@app.route('/grievance/<int:comp_id>')
@login_required
def view_grievance_detail(comp_id):
    grievance = db.session.get(Complaint, comp_id)  # ✅ FIXED: SQLAlchemy 2.0 Compatible
    
    # Ensure the user owns the grievance
    if grievance.stud_id != current_user.user_id:
        flash("Unauthorized access!", "danger")
        return redirect(url_for('view_grievances'))

    return render_template('grievance_detail.html', grievance=grievance)



if __name__ == '__main__':
    app.run(debug=True)
