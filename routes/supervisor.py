from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from sqlalchemy import func
from models import Complaint, Supervisor, Student, db

supervisor_bp = Blueprint('supervisor', __name__)

@supervisor_bp.route('/dashboard')
@login_required
def dashboard():
    # ...existing code for supervisor dashboard...
    if current_user.role != "supervisor":
        flash("Unauthorized access.", "danger")
        return redirect(url_for('auth.login'))

    # Fetch the latest 5 complaints assigned to the supervisor
    recent_complaints = Complaint.query.filter_by(superv_id=current_user.supervisor.superv_id).order_by(Complaint.comp_id.desc()).limit(5).all()
    return render_template('supervisor/supervisor_dashboard.html',recent_complaints=recent_complaints, user=current_user)

@supervisor_bp.route('/manage_complaints')
@login_required
def manage_complaints():
    # ...existing code for managing complaints...
    if current_user.role != 'supervisor':
        flash("Unauthorized access.", "danger")
        return redirect(url_for('auth.home'))

    # Ensure the current user has an associated supervisor record
    supervisor = Supervisor.query.filter_by(user_id=current_user.user_id).first()
    if not supervisor:
        flash("Supervisor record not found.", "danger")
        return redirect(url_for('auth.home'))

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

@supervisor_bp.route('/performance_analytics')
@login_required
def performance_analytics():
    # ...existing code for performance analytics...
    if current_user.role != "supervisor":
        flash("Unauthorized access.", "danger")
        return redirect(url_for('auth.login'))
    
    # Ensure supervisor entry exists
    supervisor = current_user.supervisor
    if not supervisor:
        flash("Supervisor record not found.", "danger")
        return redirect(url_for('auth.login'))

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
    return render_template('supervisor/performance_analytics.html', total_complaints=total_complaints, 
                           resolved_complaints=resolved_complaints, 
                           unresolved_complaints=unresolved_complaints,
                           months=months or [],  # Ensure it's always defined
                           complaints_per_month=complaints_per_month or [])

@supervisor_bp.route('/complaint/update/<int:comp_id>', methods=['POST'])
@login_required
def update_complaint_status(comp_id):
    # Check if the logged-in user is a supervisor
    if current_user.role != 'supervisor':
        flash("Unauthorized access.", "danger")
        return redirect(url_for('auth.home'))

    # Retrieve the complaint by its ID
    complaint = Complaint.query.get_or_404(comp_id)

    # Ensure that the complaint belongs to the supervisor
    if complaint.superv_id != current_user.supervisor.superv_id:
        flash("Unauthorized access to complaint.", "danger")
        return redirect(url_for('supervisor.manage_complaints'))

    # Get the new status from the form
    new_status = request.form.get('comp_status')

    # If a new status is provided
    if new_status:
        # Validate the status against a list of acceptable values
        if new_status not in ['New', 'Pending', 'Resolved', 'Rejected']:  # Include 'New' and 'Rejected' in valid statuses
            flash("Invalid status.", "danger")
            return redirect(url_for('supervisor.manage_complaints'))

        # Update the complaint status
        complaint.comp_status = new_status

        # If the status is 'Resolved', set the resolution date to the current time
        if new_status == 'Resolved':
            complaint.comp_dateresolved = datetime.now()

        # Commit the changes to the database
        db.session.commit()
        flash("Complaint status updated successfully.", "success")
    else:
        flash("Please select a valid status.", "danger")

    # Redirect back to the supervisor's complaint management page
    return redirect(url_for('supervisor.manage_complaints'))


@supervisor_bp.route('/supervisor/complaint_history')
@login_required
def complaint_history():
    if current_user.role != "supervisor":
        flash("Unauthorized access.", "danger")
        return redirect(url_for('auth.login'))

    # Fetch all past complaints the supervisor has handled
    complaints = Complaint.query.filter_by(superv_id=current_user.supervisor.superv_id).all()

    return render_template('supervisor/complaint_history.html', complaints=complaints)


@supervisor_bp.route('/supervisor/student/<int:student_id>/complaint/<int:complaint_id>')
@login_required
def view_complaint_details(student_id, complaint_id):
    if current_user.role != "supervisor":
        flash("Unauthorized access.", "danger")
        return redirect(url_for('auth.login'))

    student = Student.query.filter_by(stud_id=student_id).first_or_404()

    # Fetch the complaint related to the student using stud_id and complaint_id
    complaint = Complaint.query.filter_by(stud_id=student.stud_id, comp_id=complaint_id).first_or_404()

    return render_template('supervisor/complaint_details.html', student=student, complaint=complaint)
