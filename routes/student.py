import os
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from models import Admin, Complaint, Department, Student, Feedback, db
from config import Config

student_bp = Blueprint('student', __name__)

@student_bp.route('/dashboard')
@login_required
def dashboard():
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

        # Create the new complaint object
        new_complaint = Complaint(
            comp_title=title,  # Save the title
            comp_descr=description,
            comp_dept=category,
            comp_anonymous=anonymous,
            comp_doc=filename,
            stud_id=int(student_id) if student_id else None,
        )

        # Fetch the department object based on the selected category
        department = Department.query.filter_by(dept_name=category).first()

        if not department:
            flash("The selected department does not exist.", "danger")
            return redirect(url_for("student.submit_grievance"))

        # Find the least-loaded admin in this department
        admin = get_least_loaded_admin(department)

        if not admin:
            flash("No admin is available in the selected department.", "danger")
            return redirect(url_for("student.submit_grievance"))

        # Assign the least-loaded admin to the complaint
        new_complaint.admin_id = admin.admin_id

        # Add the complaint to the session and commit it
        db.session.add(new_complaint)
        db.session.commit()

        flash("Your grievance has been submitted successfully!", "success")
        return redirect(url_for("student.dashboard"))  # Redirect to dashboard after submission

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
    # ...existing code...
    if current_user.role != 'student':
        flash("Access denied. Only students can view grievances.", "danger")
        return redirect(url_for('auth.home'))

    student = Student.query.filter_by(user_id=current_user.user_id).first()
    if not student:
        flash("No student profile found. Please contact administration.", "warning")
        return redirect(url_for('student.dashboard'))

    # Get the status and search query from the request
    status = request.args.get('status', 'All')
    search_query = request.args.get('search', '')

    # Start with all grievances for the student
    grievances_query = Complaint.query.filter_by(stud_id=student.stud_id)

    # Apply status filter
    if status != 'All':
        grievances_query = grievances_query.filter_by(comp_status=status)

    # Apply search filter
    if search_query:
        grievances_query = grievances_query.filter(Complaint.comp_descr.contains(search_query))

    # Get the filtered grievances
    grievances = grievances_query.all()
    
    return render_template('student/view_grievances.html', grievances=grievances, selected_status=status, search_query=search_query)

@student_bp.route('/grievance_details/<int:comp_id>')
@login_required
def grievance_details(comp_id):
    # Ensure the user is a student
    if current_user.role != 'student':
        flash("Access denied. Only students can view grievance details.", "danger")
        return redirect(url_for('auth.home'))

    # Fetch the grievance by ID
    grievance = Complaint.query.filter_by(comp_id=comp_id).first()

    if not grievance:
        flash("Grievance not found.", "warning")
        return redirect(url_for('student.view_grievances'))

    # Ensure the grievance belongs to the current student
    student = Student.query.filter_by(user_id=current_user.user_id).first()
    if not student or grievance.stud_id != student.stud_id:
        flash("You are not authorized to view this grievance.", "danger")
        return redirect(url_for('student.view_grievances'))

    return render_template('student/grievence_details.html', grievance=grievance, student=student)

@student_bp.route('/submit_feedback/<int:comp_id>', methods=['GET', 'POST'])
@login_required
def submit_feedback(comp_id):
    if current_user.role != 'student':
        flash("Access denied. Only students can submit feedback.", "danger")
        return redirect(url_for('auth.home'))

    complaint = Complaint.query.get_or_404(comp_id)
    student = Student.query.filter_by(user_id=current_user.user_id).first()

    if complaint.stud_id != student.stud_id:
        flash("You can only provide feedback for your own complaints.", "danger")
        return redirect(url_for('student.view_grievances'))

    if complaint.comp_status != 'Resolved':
        flash("Feedback can only be provided for resolved complaints.", "danger")
        return redirect(url_for('student.view_grievances'))

    # Check if feedback already exists
    existing_feedback = Feedback.query.filter_by(comp_id=comp_id).first()
    if existing_feedback:
        flash("Feedback has already been submitted for this complaint.", "warning")
        return redirect(url_for('student.view_grievances'))

    if request.method == 'POST':
        feedback = Feedback(
            service_quality=request.form['service_quality'],
            staff_behaviour=request.form['staff_behaviour'],
            overall_experience=request.form['overall_experience'],
            comments=request.form.get('comments'),
            comp_id=comp_id,
            stud_id=student.stud_id
        )
        
        db.session.add(feedback)
        db.session.commit()
        
        flash("Thank you for your feedback!", "success")
        return redirect(url_for('student.view_grievances'))

    return render_template('student/feedback.html', complaint=complaint)
