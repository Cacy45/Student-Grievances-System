from flask import Flask,render_template, request, redirect, url_for, flash, abort
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf.csrf import CSRFProtect
from models import User, Complaint
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

        hashed_password = generate_password_hash(password)
        user = User(fname=fname, lname=lname, email=email, phone=phone, password=hashed_password, role=role)
        db.session.add(user)
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

            # Redirect users based on their role
            if user.role == 'student':
                return redirect(url_for('student_dashboard'))
            elif user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif user.role == 'supervisor':
                return redirect(url_for('supervisor_dashboard'))

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

@app.route('/submit_grievance', methods=['GET', 'POST'])
@login_required
def submit_grievance():
    if request.method == 'POST':
        title = request.form['title']
        category = request.form['category']
        description = request.form['description']
        anonymous = 'anonymous' in request.form  # Checkbox for anonymous submission
        file = request.files['attachment']

        # File handling
        filename = None
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

        # Create new complaint
        new_complaint = Complaint(
            comp_descr=description,
            comp_dept=category,
            comp_anonymous=anonymous,
            comp_doc=filename,  # Save filename if uploaded
            stud_id=current_user.user_id  # Assuming User model links to Student
        )

        db.session.add(new_complaint)
        db.session.commit()

        flash('Grievance submitted successfully!', 'success')
        return redirect(url_for('student_dashboard'))

    return render_template('submit_grievance.html')

# ================= View Grievances Route ================= #
@app.route('/view_grievances')
@login_required
def view_grievances():
    grievances = Complaint.query.filter_by(stud_id=current_user.user_id).all()
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
