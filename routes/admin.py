from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import Complaint, Admin, Supervisor, Appeal, db

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/dashboard")
@login_required
def dashboard():
    total_complaints = Complaint.query.count()
    resolved_complaints = Complaint.query.filter_by(comp_status="Resolved").count()
    pending_complaints = Complaint.query.filter_by(comp_status="Pending").count()

    return render_template(
        "admin/admin_dashboard.html",
        total_complaints=total_complaints,
        resolved_complaints=resolved_complaints,
        pending_complaints=pending_complaints,
    )


@admin_bp.route("/manage_complaints")
@login_required
def manage_complaints():
    if current_user.role != "admin":
        flash("Unauthorized access.", "danger")
        return redirect(url_for("shared.home"))

    # Ensure the current user has an associated admin record
    admin = Admin.query.filter_by(user_id=current_user.user_id).first()
    if not admin:
        flash("Admin record not found.", "danger")
        return redirect(url_for("shared.home"))

    # Get filter values from the request
    status_filter = request.args.get("status", default="All", type=str)
    search_query = request.args.get("search", default="", type=str)

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
        "admin/manage_complaints.html",
        complaints=complaints,
        selected_status=status_filter,
        search_query=search_query,
        supervisors=supervisors,
    )


@admin_bp.route("/complaint/update/<int:comp_id>", methods=["POST"])
@login_required
def update_complaint(comp_id):
    # ...existing code for updating complaints...
    if current_user.role != "admin":
        return jsonify({"success": False, "message": "Unauthorized access"}), 403

    complaint = Complaint.query.get_or_404(comp_id)

    # Prevent status update if the complaint is transferred to a supervisor
    if complaint.superv_id:
        return (
            jsonify(
                {
                    "success": False,
                    "message": "You cannot update the status of a complaint that has been transferred to a supervisor.",
                }
            ),
            403,
        )

    if request.is_json:  # Handle AJAX Request
        data = request.get_json()
        if "status" in data:
            complaint.comp_status = data["status"]
            db.session.commit()
            return jsonify({"success": True, "new_status": complaint.comp_status})

        return jsonify({"success": False, "message": "Invalid request"}), 400

    else:  # Handle Traditional Form Submission
        complaint.comp_status = request.form["status"]
        db.session.commit()
        flash("Complaint updated successfully.", "success")
    return jsonify({"success": True, "new_status": complaint.comp_status})


# Where's the html for this route
@admin_bp.route("/complaint/transfer/<int:comp_id>", methods=["GET", "POST"])
@login_required
def transfer_complaint(comp_id):
    if current_user.role != "admin":
        flash("Unauthorized access.", "danger")
        return redirect(url_for("shared.home"))

    complaint = Complaint.query.get_or_404(comp_id)

    # Check if the complaint has already been transferred to a supervisor
    if complaint.superv_id:
        flash("This complaint has already been transferred to a supervisor.", "warning")
        return redirect(url_for("admin.manage_complaints"))

    # Fetch the supervisors from the same department as the complaint's department
    supervisors = Supervisor.query.filter_by(dept_id=complaint.comp_dept).all()

    if request.method == "POST":
        supervisor_id = request.form.get("supervisor_id")

        if not supervisor_id:
            flash("Please select a supervisor.", "warning")
            return redirect(url_for("transfer_complaint", comp_id=comp_id))

        # Fetch supervisor
        supervisor = Supervisor.query.get(
            int(supervisor_id)
        )  # Make sure it's an integer

        if not supervisor:
            flash("Invalid supervisor selection.", "danger")
            return redirect(url_for("transfer_complaint", comp_id=comp_id))

        # Update complaint with the supervisor's ID and change status to "Transferred"
        complaint.superv_id = supervisor.superv_id
        complaint.comp_status = "Transferred"

        try:
            db.session.commit()
            flash("Complaint transferred successfully.", "success")
            return redirect(url_for("admin.manage_complaints"))
        except Exception as e:
            db.session.rollback()
            flash(f"An error occurred: {e}", "danger")

    return render_template(
        "transfer_complaint.html", complaint=complaint, supervisors=supervisors
    )


@admin_bp.route("/profile", methods=["GET", "POST"])
@login_required
def admin_profile():
    if current_user.role != "admin":
        flash("Unauthorized access.", "danger")
        return redirect(url_for("shared.home"))

    admin = Admin.query.filter_by(user_id=current_user.user_id).first()

    if request.method == "POST":
        current_user.fname = request.form["fname"]
        current_user.lname = request.form["lname"]
        current_user.phone = request.form["phone"]
        db.session.commit()
        flash("Profile updated successfully.", "success")
        return redirect(url_for("admin.admin_profile"))

    return render_template("admin/admin_profile.html", admin=admin)


# We're not doing appeals
@admin_bp.route("/manage_appeals")
@login_required
def manage_appeals():
    if current_user.role != "admin":
        flash("Unauthorized access.", "danger")
        return redirect(url_for("shared.home"))

    appeals = Appeal.query.all()
    return render_template("admin/manage_appeals.html", appeals=appeals)
