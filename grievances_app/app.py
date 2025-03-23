from flask import Flask, render_template, request, redirect, url_for, flash, abort
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf.csrf import CSRFProtect
from models import User, Complaint, Department, Student, Admin, Supervisor, db
import os
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)

# Configure Database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///student_grievances.db'  
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_key'

csrf = CSRFProtect(app)

db.init_app(app)
migrate = Migrate(app, db)

# Initialize LoginManager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))  # Fixed SQLAlchemy 2.0 `get()`

#======================================Shared Routes============================================#
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    departments = Department.query.all()  # Fetch all departments

    if request.method == 'POST':
        fname = request.form['fname']
        lname = request.form['lname']
        email = request.form['email']
        phone = request.form['phone']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        role = request.form['role']
        dept_id = request.form.get('dept_id')

        print(f"Role selected: {role}")  # ✅ Debugging Role
        print(f"Selected department: {dept_id}")

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('register'))

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email is already registered.', 'danger')
            return redirect(url_for('register'))

        user = User(fname=fname, lname=lname, email=email, phone=phone, role=role)
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        if role == "student":
            db.session.add(Student(user_id=user.user_id))
        elif role == "admin":
            if not dept_id:
                flash("Admin must select a department.", "danger")
                return redirect(url_for('register'))
            db.session.add(Admin(user_id=user.user_id, dept_id=dept_id))

            print(f"Admin added: {new_admin}") #debug
            
        elif role == "supervisor":
            if not dept_id:
                flash("Supervisor must select a department.", "danger")
                return redirect(url_for('register'))
            db.session.add(Supervisor(user_id=user.user_id, dept_id=dept_id))
            

        db.session.commit()

        flash('Account created successfully! You can now log in.', 'success')
        print("Redirecting to login page...")  

        return redirect(url_for('login'))  

    return render_template('register.html', departments=departments)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):  
            login_user(user)
            flash('Login successful!', 'success')

            if user.role == 'student':
                if Student.query.filter_by(user_id=user.user_id).first():
                    return redirect(url_for('student_dashboard'))
            elif user.role == 'admin':
                if Admin.query.filter_by(user_id=user.user_id).first():
                    return redirect(url_for('admin_dashboard'))
            elif user.role == 'supervisor':
                if Supervisor.query.filter_by(user_id=user.user_id).first():
                    return redirect(url_for('supervisor_dashboard'))

            flash('Profile missing. Contact admin.', 'danger')
            return redirect(url_for('home'))

        flash('Login failed. Check your email and password.', 'danger')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))

#====================================================Admin Routes============================================================#
@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    return render_template('admin_dashboard.html', user=current_user)

#================================================Supervisor Routes======================================================
@app.route('/supervisor/dashboard')
@login_required
def supervisor_dashboard():
    if current_user.role != "supervisor":
        flash("Unauthorized access.", "danger")
        return redirect(url_for('login'))

    # Fetch the latest 5 complaints assigned to the supervisor
    recent_complaints = Complaint.query.filter_by(superv_id=current_user.supervisor.superv_id).order_by(Complaint.comp_id.desc()).limit(5).all()

    return render_template('supervisor_dashboard.html', recent_complaints=recent_complaints, user=current_user)


@app.route('/supervisor/complaints/<int:complaint_id>')
@login_required
def supervisor_complaints(comp_id):
    if current_user.role != "supervisor":
        flash("Unauthorized access.", "danger")
        return redirect(url_for('login'))

    complaint = Complaint.query.get_or_404(comp_id)

    # Ensure the supervisor only sees complaints assigned to them
    if complaint.superv_id != current_user.supervisor.superv_id:
        flash("You do not have access to this complaint.", "danger")
        return redirect(url_for('supervisor_dashboard'))

    return render_template('view_complaint.html', complaint=complaint)


@app.route('/supervisor/complaints/<int:comp_id>/resolve', methods=['GET', 'POST'])
@login_required
def resolve_complaint(comp_id):
    if current_user.role != "supervisor":
        flash("Unauthorized access.", "danger")
        return redirect(url_for('login'))

    complaint = Complaint.query.get_or_404(comp_id)

    # Ensure the supervisor only updates complaints assigned to them
    if complaint.superv_id != current_user.supervisor.superv_id:
        flash("You do not have access to this complaint.", "danger")
        return redirect(url_for('supervisor_dashboard'))

    if request.method == 'POST':
        status = request.form['status']
        resolution = request.form['resolution']

        complaint.comp_status = status
        complaint.comp_dateresolved = datetime.utcnow()
        complaint.comp_descr += f"\n\n[Supervisor Resolution]: {resolution}"  # Appending resolution details

        db.session.commit()

        flash("Complaint resolved successfully!", "success")
        return redirect(url_for('supervisor_dashboard'))

    return render_template('resolve_complaint.html', complaint=complaint)


@app.route('/supervisor/complaint_history')
@login_required
def complaint_history():
    if current_user.role != "supervisor":
        flash("Unauthorized access.", "danger")
        return redirect(url_for('login'))

    # Fetch all past complaints the supervisor has handled
    complaints = Complaint.query.filter_by(superv_id=current_user.supervisor.superv_id).all()

    return render_template('complaint_history.html', complaints=complaints)


@app.route('/supervisor/performance_analytics')
@login_required
def performance_analytics():
    if current_user.role != "supervisor":
        flash("Unauthorized access.", "danger")
        return redirect(url_for('login'))
    
    # Ensure supervisor entry exists
    supervisor = current_user.supervisor
    if not supervisor:
        flash("Supervisor record not found.", "danger")
        return redirect(url_for('login'))

    # Fetch complaint stats
    total_complaints = Complaint.query.filter_by(superv_id=current_user.supervisor.superv_id).count()
    resolved_complaints = Complaint.query.filter_by(superv_id=current_user.supervisor.superv_id, comp_status="Resolved").count()
    unresolved_complaints = total_complaints - resolved_complaints

    # Dummy months data (Replace this with actual data from your database)
    #months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun","Jul","Aug","Sep","Oct","Nov","Dec"]  

    return render_template('performance_analytics.html', 
                           total_complaints=total_complaints, 
                           resolved_complaints=resolved_complaints, 
                           unresolved_complaints=unresolved_complaints)

"""
@app.route('/supervisor_dashboard')
@login_required
def supervisor_dashboard():
    return render_template('supervisor_dashboard.html', user=current_user)
"""
#============================================Student Routes===================================================#
@app.route('/student_dashboard')
@login_required
def student_dashboard():
    return render_template('student_dashboard.html', user=current_user)


UPLOAD_FOLDER = 'static/uploads'
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
        anonymous = request.form.get("anonymous") == "on"
        student_id = None if anonymous else request.form.get("stud_id")

        attachment = request.files.get("attachment")
        filename = None
        if attachment and allowed_file(attachment.filename):
            filename = secure_filename(attachment.filename)
            attachment.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

        new_complaint = Complaint(
            comp_descr=description,
            comp_dept=category,
            comp_anonymous=anonymous,
            comp_doc=filename,
            stud_id=int(student_id) if student_id else None,
        )
        db.session.add(new_complaint)
        db.session.commit()

        flash("Your grievance has been submitted successfully!", "success")
        return redirect(url_for("submit_grievance"))

    departments = Department.query.all()
    return render_template("submit_grievance.html", departments=departments)

@app.route('/view_grievances')
@login_required
def view_grievances():
    if current_user.role != 'student':
        flash("Access denied. Only students can view grievances.", "danger")
        return redirect(url_for('home'))

    student = Student.query.filter_by(user_id=current_user.user_id).first()
    if not student:
        flash("No student profile found. Please contact administration.", "warning")
        return redirect(url_for('student_dashboard'))

    grievances = Complaint.query.filter_by(stud_id=student.stud_id).all()
    return render_template('view_grievances.html', grievances=grievances)

@app.route('/grievance/<int:comp_id>')
@login_required
def view_grievance_detail(comp_id):
    grievance = db.session.get(Complaint, comp_id)
    student = Student.query.filter_by(user_id=current_user.user_id).first()

    if not grievance or not student or grievance.stud_id != student.stud_id:
        flash("Unauthorized access!", "danger")
        return redirect(url_for('view_grievances'))

    return render_template('grievance_detail.html', grievance=grievance)

if __name__ == '__main__':
    app.run(debug=True)
