import os
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from models import Admin, Complaint, Department, Student, db
from config import Config

student_bp = Blueprint('student', __name__)

@student_bp.route('/dashboard')
@login_required
def dashboard():
    # ...existing code for student dashboard...
    
    return render_template('student/student_dashboard.html', user=current_user)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

@student_bp.route('/submit_grievance', methods=['GET', 'POST'])
@login_required
def submit_grievance():
    # ...existing code for submitting grievances...
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
            attachment.save(os.path.join(Config.UPLOAD_FOLDER, filename))

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
    return render_template('student/submit_grievance.html', departments=departments)

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

@student_bp.route('/view_grievances')
@login_required
def view_grievances():
    # ...existing code for viewing grievances...
    if current_user.role != 'student':
        flash("Access denied. Only students can view grievances.", "danger")
        return redirect(url_for('auth.home'))

    student = Student.query.filter_by(user_id=current_user.user_id).first()
    if not student:
        flash("No student profile found. Please contact administration.", "warning")
        return redirect(url_for('student_dashboard'))

    grievances = Complaint.query.filter_by(stud_id=student.stud_id).all()
    
    return render_template('student/view_grievances.html', grievances=grievances)
