from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from models import User, Department, Student, Admin, Supervisor, db

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['GET', 'POST'])
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
            return redirect(url_for('auth.register'))

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email is already registered.', 'danger')
            return redirect(url_for('auth.register'))

        # Convert dept_id to integer and validate
        if role in ["admin", "supervisor"]:
            if not dept_id:
                flash(f"{role.capitalize()} must select a department.", "danger")
                return redirect(url_for('auth.register'))
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
        return redirect(url_for('auth.login'))  

    return render_template('register.html', departments=departments)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()

        if not user:
            flash('Invalid email or password.', 'danger')
            return redirect(url_for('auth.login'))

        if not user.check_password(password):
            flash('Invalid email or password.', 'danger')
            return redirect(url_for('auth.login'))

        login_user(user)
        print(f"User {user.email} logged in as {user.role}")  # Debugging
        flash('Login successful!', 'success')

        # Role-based redirection
        if user.role == 'student' and Student.query.filter_by(user_id=user.user_id).first():
            return redirect(url_for('student_dashboard'))
        elif user.role == 'admin' and Admin.query.filter_by(user_id=user.user_id).first():
            return redirect(url_for('admin.dashboard'))
        elif user.role == 'supervisor' and Supervisor.query.filter_by(user_id=user.user_id).first():
            return redirect(url_for('supervisor.dashboard'))

        flash('Profile missing. Contact admin.', 'danger')
        return redirect(url_for('auth.home'))

    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for('auth.login'))