from flask import Flask, render_template, request, redirect, url_for, flash, abort, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf.csrf import CSRFProtect
from models import User, Complaint, Department, Student, Admin, Supervisor, Appeal, db
import os
from werkzeug.utils import secure_filename
from datetime import datetime
from sqlalchemy import func

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
    return db.session.get(User, int(user_id))  

#======================================Shared Routes============================================#
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    departments = Department.query.all()

    if request.method == 'POST':
        fname = request.form['fname']
        lname = request.form['lname']
        email = request.form['email']
        phone = request.form['phone']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        role = request.form['role']
        dept_id = request.form.get('dept_id')

        print(f"Role selected: {role}")  
        print(f"Selected department: {dept_id}")

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('register'))

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email is already registered.', 'danger')
            return redirect(url_for('register'))

        # Convert dept_id to integer and validate
        if role in ["admin", "supervisor"]:
            if not dept_id:
                flash(f"{role.capitalize()} must select a department.", "danger")
                return redirect(url_for('register'))
            dept_id = int(dept_id)  # Convert from string to integer

        # Create User and commit
        user = User(fname=fname, lname=lname, email=email, phone=phone, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        print(f"User {user.user_id} created successfully!")

        # role-specific details
        if role == "student":
            student = Student(user_id=user.user_id)
            db.session.add(student)
            print(f"Student {student.stud_id} created.")
        elif role == "admin":
            admin = Admin(user_id=user.user_id, dept_id=dept_id)
            db.session.add(admin)
            print(f"Admin {admin.admin_id} created with Dept ID {dept_id}.")
        elif role == "supervisor":
            supervisor = Supervisor(user_id=user.user_id, dept_id=dept_id)
            db.session.add(supervisor)
            print(f"Supervisor {supervisor.superv_id} created with Dept ID {dept_id}.")

        db.session.commit()

        flash('Account created successfully! You can now log in.', 'success')
        return redirect(url_for('login'))  

    return render_template('register.html', departments=departments)



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()

        if not user:
            flash('Invalid email or password.', 'danger')
            return redirect(url_for('login'))

        if not user.check_password(password):
            flash('Invalid email or password.', 'danger')
            return redirect(url_for('login'))

        login_user(user)
        print(f"User {user.email} logged in as {user.role}")  # Debugging
        flash('Login successful!', 'success')

        # Role-based redirection
        if user.role == 'student' and Student.query.filter_by(user_id=user.user_id).first():
            return redirect(url_for('student_dashboard'))
        elif user.role == 'admin' and Admin.query.filter_by(user_id=user.user_id).first():
            return redirect(url_for('admin_dashboard'))
        elif user.role == 'supervisor' and Supervisor.query.filter_by(user_id=user.user_id).first():
            return redirect(url_for('supervisor_dashboard'))

        flash('Profile missing. Contact admin.', 'danger')
        return redirect(url_for('home'))

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
    """
    if current_user.role != 'admin':
        flash("Unauthorized access.", "danger")
        return redirect(url_for('home'))
    """
    total_complaints = Complaint.query.count()
    resolved_complaints = Complaint.query.filter_by(comp_status='Resolved').count()
    pending_complaints = Complaint.query.filter_by(comp_status='Pending').count()
    
    return render_template('admin/admin_dashboard.html', 
                           total_complaints=total_complaints,
                           resolved_complaints=resolved_complaints,
                           pending_complaints=pending_complaints)

@app.route('/admin/manage_complaints')
@login_required
def manage_complaints():
    if current_user.role != 'admin':
        flash("Unauthorized access.", "danger")
        return redirect(url_for('home'))
    
    # Ensure the current user has an associated admin record
    admin = Admin.query.filter_by(user_id=current_user.user_id).first()
    if not admin:
        flash("Admin record not found.", "danger")
        return redirect(url_for('home'))

    # Get filter values from the request
    status_filter = request.args.get('status', default="All", type=str)
    search_query = request.args.get('search', default="", type=str)

    # Fetch complaints assigned to the current admin
    complaints = Complaint.query.filter_by(admin_id=admin.admin_id)

    # Apply department filter to only show complaints from the admin's department
    complaints = complaints.filter_by(comp_dept=admin.department.dept_name)

    # Apply status filter if not "All"
    if status_filter and status_filter != "All":
        complaints = complaints.filter(Complaint.comp_status == status_filter)

    # Apply search query filter
    if search_query:
        complaints = complaints.filter(Complaint.comp_descr.ilike(f"%{search_query}%"))

    complaints = complaints.order_by(Complaint.comp_datefiled.desc()).all()

    # Fetch supervisors belonging to the admin's department
    supervisors = Supervisor.query.filter_by(dept_id=admin.dept_id).all()

    return render_template(
        'admin/manage_complaints.html',
        complaints=complaints,
        selected_status=status_filter,
        search_query=search_query,
        supervisors=supervisors  # Pass supervisors to the template
    )



@app.route('/admin/complaint/update/<int:comp_id>', methods=['POST'])
@login_required
def update_complaint(comp_id):
    if current_user.role != 'admin':
        return jsonify({"success": False, "message": "Unauthorized access"}), 403
    
    complaint = Complaint.query.get_or_404(comp_id)

    # Prevent status update if the complaint is transferred to a supervisor
    if complaint.superv_id:
        return jsonify({"success": False, "message": "You cannot update the status of a complaint that has been transferred to a supervisor."}), 403

    if request.is_json:  # Handle AJAX Request
        data = request.get_json()
        if 'status' in data:
            complaint.comp_status = data['status']
            db.session.commit()
            return jsonify({"success": True, "new_status": complaint.comp_status})

        return jsonify({"success": False, "message": "Invalid request"}), 400

    else:  # Handle Traditional Form Submission
        complaint.comp_status = request.form['status']
        db.session.commit()
        flash("Complaint updated successfully.", "success")
        return redirect(url_for('manage_complaints'))

    
#Where's the html for this route
@app.route('/admin/complaint/transfer/<int:comp_id>', methods=['GET', 'POST'])
@login_required
def transfer_complaint(comp_id):
    if current_user.role != 'admin':
        flash("Unauthorized access.", "danger")
        return redirect(url_for('home'))

    complaint = Complaint.query.get_or_404(comp_id)

    # Check if the complaint has already been transferred to a supervisor
    if complaint.superv_id:
        flash("This complaint has already been transferred to a supervisor.", "warning")
        return redirect(url_for('manage_complaints'))

    # Fetch the supervisors from the same department as the complaint's department
    supervisors = Supervisor.query.filter_by(dept_id=complaint.comp_dept).all()

    if request.method == 'POST':
        supervisor_id = request.form.get('supervisor_id')

        if not supervisor_id:
            flash("Please select a supervisor.", "warning")
            return redirect(url_for('transfer_complaint', comp_id=comp_id))

        # Fetch supervisor
        supervisor = Supervisor.query.get(int(supervisor_id))  # Make sure it's an integer

        if not supervisor:
            flash("Invalid supervisor selection.", "danger")
            return redirect(url_for('transfer_complaint', comp_id=comp_id))

        # Update complaint with the supervisor's ID and change status to "Transferred"
        complaint.superv_id = supervisor.superv_id
        complaint.comp_status = 'Transferred'

        try:
            db.session.commit()
            flash("Complaint transferred successfully.", "success")
            return redirect(url_for('manage_complaints'))
        except Exception as e:
            db.session.rollback()
            flash(f"An error occurred: {e}", "danger")

    return render_template('transfer_complaint.html', complaint=complaint, supervisors=supervisors)


@app.route('/admin/manage_appeals')
@login_required
def manage_appeals():
    if current_user.role != 'admin':
        flash("Unauthorized access.", "danger")
        return redirect(url_for('home'))
    
    appeals = Appeal.query.all()
    return render_template('admin/manage_appeals.html', appeals=appeals)


#Is this route being used?
@app.route('/admin/profile', methods=['GET', 'POST'])
@login_required
def admin_profile():
    if current_user.role != 'admin':
        flash("Unauthorized access.", "danger")
        return redirect(url_for('home'))
    
    admin = Admin.query.filter_by(user_id=current_user.user_id).first()
    
    if request.method == 'POST':
        current_user.fname = request.form['fname']
        current_user.lname = request.form['lname']
        current_user.phone = request.form['phone']
        db.session.commit()
        flash("Profile updated successfully.", "success")
        return redirect(url_for('admin_profile'))
    
    return render_template('admin/admin_profile.html', admin=admin)


#================================================Supervisor Routes======================================================
@app.route('/supervisor/dashboard')
@login_required
def supervisor_dashboard():
    if current_user.role != "supervisor":
        flash("Unauthorized access.", "danger")
        return redirect(url_for('login'))

    # Fetch the latest 5 complaints assigned to the supervisor
    recent_complaints = Complaint.query.filter_by(superv_id=current_user.supervisor.superv_id).order_by(Complaint.comp_id.desc()).limit(5).all()

    return render_template('supervisor/supervisor_dashboard.html', recent_complaints=recent_complaints, user=current_user)


@app.route('/supervisor/manage_complaints')
@login_required
def supervisor_manage_complaints():
    if current_user.role != 'supervisor':
        flash("Unauthorized access.", "danger")
        return redirect(url_for('home'))

    # Ensure the current user has an associated supervisor record
    supervisor = Supervisor.query.filter_by(user_id=current_user.user_id).first()
    if not supervisor:
        flash("Supervisor record not found.", "danger")
        return redirect(url_for('home'))

    # Get filter values from the request
    status_filter = request.args.get('status', default="All", type=str)
    search_query = request.args.get('search', default="", type=str)

    # Fetch complaints assigned to this supervisor
    complaints = Complaint.query.filter_by(superv_id=supervisor.superv_id)

    # Apply status filter if not "All"
    if status_filter and status_filter != "All":
        complaints = complaints.filter(Complaint.comp_status == status_filter)

    # Apply search query filter
    if search_query:
        complaints = complaints.filter(Complaint.comp_descr.ilike(f"%{search_query}%"))

    complaints = complaints.order_by(Complaint.comp_datefiled.desc()).all()

    # Preload student data for each complaint to avoid querying in the template
    for complaint in complaints:
        complaint.student = Student.query.get(complaint.stud_id)

    return render_template('supervisor/supervisor_manage_complaints.html', complaints=complaints, selected_status=status_filter, search_query=search_query)


@app.route('/supervisor/student/<int:student_id>/complaint/<int:complaint_id>')
@login_required
def view_complaint_details(student_id, complaint_id):
    if current_user.role != "supervisor":
        flash("Unauthorized access.", "danger")
        return redirect(url_for('login'))

    student = Student.query.filter_by(stud_id=student_id).first_or_404()

    # Fetch the complaint related to the student using stud_id and complaint_id
    complaint = Complaint.query.filter_by(stud_id=student.stud_id, comp_id=complaint_id).first_or_404()

    return render_template('supervisor/complaint_details.html', student=student, complaint=complaint)




@app.route('/supervisor/complaint/update/<int:comp_id>', methods=['POST'])
@login_required
def update_complaint_status(comp_id):
    # Check if the logged-in user is a supervisor
    if current_user.role != 'supervisor':
        flash("Unauthorized access.", "danger")
        return redirect(url_for('home'))

    # Retrieve the complaint by its ID
    complaint = Complaint.query.get_or_404(comp_id)

    # Ensure that the complaint belongs to the supervisor
    if complaint.superv_id != current_user.supervisor.superv_id:
        flash("Unauthorized access to complaint.", "danger")
        return redirect(url_for('supervisor_manage_complaints'))

    # Get the new status from the form
    new_status = request.form.get('comp_status')

    # If a new status is provided
    if new_status:
        # Validate the status against a list of acceptable values
        if new_status not in ['New', 'Pending', 'Resolved', 'Rejected']:  # Include 'New' and 'Rejected' in valid statuses
            flash("Invalid status.", "danger")
            return redirect(url_for('supervisor_manage_complaints'))

        # Update the complaint status
        complaint.comp_status = new_status

        # If the status is 'Resolved', set the resolution date to the current time
        if new_status == 'Resolved':
            complaint.comp_dateresolved = datetime.utcnow()

        # Commit the changes to the database
        db.session.commit()
        flash("Complaint status updated successfully.", "success")
    else:
        flash("Please select a valid status.", "danger")

    # Redirect back to the supervisor's complaint management page
    return redirect(url_for('supervisor_manage_complaints'))


#Is this route being used, I deleted the html for it
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

    return render_template('supervisor/complaint_history.html', complaints=complaints)


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
    total_complaints = Complaint.query.filter_by(superv_id=supervisor.superv_id).count()
    resolved_complaints = Complaint.query.filter_by(superv_id=supervisor.superv_id, comp_status="Resolved").count()
    unresolved_complaints = total_complaints - resolved_complaints

    # Fetch monthly complaints data from the database
    months = []
    complaints_per_month = []

    results = (
        db.session.query(func.strftime("%Y-%m", Complaint.comp_datefiled), func.count())
        .filter(Complaint.superv_id == supervisor.superv_id)
        .group_by(func.strftime("%Y-%m", Complaint.comp_datefiled))
        .all()
    )

    if results:
        for month, count in results:
            months.append(month)
            complaints_per_month.append(count)

    return render_template('supervisor/performance_analytics.html', 
                           total_complaints=total_complaints, 
                           resolved_complaints=resolved_complaints, 
                           unresolved_complaints=unresolved_complaints,
                           months=months or [],  # Ensure it's always defined
                           complaints_per_month=complaints_per_month or [])  # Ensure it's always defined


#============================================Student Routes===================================================#
@app.route('/student_dashboard')
@login_required
def student_dashboard():
    return render_template('student/student_dashboard.html', user=current_user)


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

        # Create the new complaint object (not assigned yet to an admin)
        new_complaint = Complaint(
            comp_descr=description,
            comp_dept=category,
            comp_anonymous=anonymous,
            comp_doc=filename,
            stud_id=int(student_id) if student_id else None,
        )

        # Fetch the department object based on the selected category
        department = Department.query.filter_by(dept_name=category).first()

        if department:
            # Find the least-loaded admin in this department
            admin = get_least_loaded_admin(department)

            if admin:
                # Assign the least-loaded admin to the complaint
                new_complaint.admin_id = admin.admin_id

        # Add the complaint to the session and commit it
        db.session.add(new_complaint)
        db.session.commit()

        flash("Your grievance has been submitted successfully!", "success")
        return redirect(url_for("submit_grievance"))

    departments = Department.query.all()
    return render_template("student/submit_grievance.html", departments=departments)


def get_least_loaded_admin(department):
    """
    This function returns the admin with the least number of complaints assigned in the given department.
    """
    # Get all admins from the selected department
    admins = Admin.query.filter_by(dept_id=department.dept_id).all()

    least_loaded_admin = None
    least_complaints_count = float('inf')  # Start with an infinite number of complaints

    # Loop through each admin to find the one with the least number of complaints
    for admin in admins:
        num_complaints = len(admin.complaints)  # Get the number of complaints assigned to this admin
        if num_complaints < least_complaints_count:
            least_complaints_count = num_complaints
            least_loaded_admin = admin

    return least_loaded_admin


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
    return render_template('student/view_grievances.html', grievances=grievances)

#Is this route being used?
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
