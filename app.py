from flask import (Flask, render_template, request, redirect,
                   url_for, flash, jsonify, send_file)
from flask_login import (LoginManager, login_user, logout_user,
                         login_required, current_user)
from functools import wraps
from datetime import datetime, date
import os
import io
import pandas as pd

from config import Config
from models import db, bcrypt, User, Student, Course, AttendanceRecord
from face_utils import detect_faces, get_embedding, identify_face, load_encodings

# ─── Create App ───────────────────────────────────────
app = Flask(__name__)
app.config.from_object(Config)

# Initialise extensions
db.init_app(app)
bcrypt.init_app(app)

# Login manager setup
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

# Global variables for ML model
known_encodings = {}


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ─── Role Decorator ───────────────────────────────────
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            flash('Admin access required.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated


# ─── App Startup ──────────────────────────────────────
def create_tables():
    db.create_all()
    # Create default admin if none exists
    if not User.query.filter_by(role='admin').first():
        admin = User(
            username='admin',
            email='admin@fras.edu',
            role='admin',
            full_name='System Administrator',
            department='IT'
        )
        admin.set_password('Admin@1234')
        db.session.add(admin)
        db.session.commit()
        print('✅ Default admin created: admin / Admin@1234')


# ════════════════════════════════════════════
#   AUTH ROUTES
# ════════════════════════════════════════════
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember', False)

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password) and user.is_active:
            login_user(user, remember=bool(remember))
            user.last_login = datetime.utcnow()
            db.session.commit()
            flash(f'Welcome back, {user.full_name}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'danger')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


# ════════════════════════════════════════════
#   DASHBOARD
# ════════════════════════════════════════════
@app.route('/dashboard')
@login_required
def dashboard():
    total_students = Student.query.filter_by(is_active=True).count()
    total_courses  = Course.query.filter_by(is_active=True).count()
    total_records  = AttendanceRecord.query.count()
    today_records  = AttendanceRecord.query.filter_by(
                        session_date=date.today()).count()

    recent_records = (AttendanceRecord.query
                      .order_by(AttendanceRecord.created_at.desc())
                      .limit(10).all())

    return render_template('dashboard.html',
        total_students=total_students,
        total_courses=total_courses,
        total_records=total_records,
        today_records=today_records,
        recent_records=recent_records)


# ════════════════════════════════════════════
#   STUDENTS
# ════════════════════════════════════════════
@app.route('/students')
@login_required
def students():
    all_students = Student.query.filter_by(is_active=True).all()
    return render_template('students.html', students=all_students)


@app.route('/students/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_student():
    if request.method == 'POST':
        # Check if student ID already exists
        existing = Student.query.filter_by(
            student_id=request.form['student_id']).first()
        if existing:
            flash('Student ID already exists!', 'danger')
            return render_template('add_student.html')

        student = Student(
            student_id    = request.form['student_id'],
            full_name     = request.form['full_name'],
            email         = request.form.get('email'),
            department    = request.form.get('department'),
            year_of_study = request.form.get('year_of_study', type=int),
            cgpa          = request.form.get('cgpa', type=float),
            phone         = request.form.get('phone'),
            advisor       = request.form.get('advisor')
        )
        db.session.add(student)
        db.session.commit()

        # Create image folder for this student
        img_folder = os.path.join('student_images', student.student_id)
        os.makedirs(img_folder, exist_ok=True)

        flash(f'Student {student.full_name} added successfully!', 'success')
        return redirect(url_for('upload_photos', student_id=student.id))

    return render_template('add_student.html')


@app.route('/students/<int:student_id>/upload',
           methods=['GET', 'POST'])
@login_required
@admin_required
def upload_photos(student_id):
    student = Student.query.get_or_404(student_id)

    if request.method == 'POST':
        photos = request.files.getlist('photos')
        folder = os.path.join('student_images', student.student_id)
        os.makedirs(folder, exist_ok=True)
        count = 0

        for photo in photos:
            if photo.filename:
                # Save photo to student folder
                photo.save(os.path.join(folder, photo.filename))
                count += 1

        flash(f'{count} photos uploaded! Run training to update model.',
              'success')
        return redirect(url_for('students'))

    # Count existing photos
    folder = os.path.join('student_images', student.student_id)
    existing_photos = 0
    if os.path.exists(folder):
        existing_photos = len([
            f for f in os.listdir(folder)
            if f.lower().endswith(('.jpg', '.jpeg', '.png'))
        ])

    return render_template('upload_photos.html',
                           student=student,
                           existing_photos=existing_photos)


@app.route('/students/<int:student_id>/deactivate',
           methods=['POST'])
@login_required
@admin_required
def deactivate_student(student_id):
    student = Student.query.get_or_404(student_id)
    student.is_active = False
    db.session.commit()
    flash(f'{student.full_name} has been deactivated.', 'info')
    return redirect(url_for('students'))


# ════════════════════════════════════════════
#   COURSES
# ════════════════════════════════════════════
@app.route('/courses')
@login_required
def courses():
    if current_user.is_admin():
        all_courses = Course.query.filter_by(is_active=True).all()
    else:
        all_courses = Course.query.filter_by(
            lecturer_id=current_user.id,
            is_active=True).all()
    return render_template('courses.html', courses=all_courses)


@app.route('/courses/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_course():
    lecturers = User.query.filter_by(
        role='lecturer', is_active=True).all()

    if request.method == 'POST':
        course = Course(
            code        = request.form['code'],
            name        = request.form['name'],
            department  = request.form.get('department'),
            lecturer_id = request.form.get('lecturer_id', type=int)
        )
        db.session.add(course)
        db.session.commit()
        flash(f'Course {course.name} added!', 'success')
        return redirect(url_for('courses'))

    return render_template('add_course.html', lecturers=lecturers)


# ════════════════════════════════════════════
#   TAKE ATTENDANCE
# ════════════════════════════════════════════
@app.route('/attendance', methods=['GET', 'POST'])
@login_required
def take_attendance():
    # Load face encodings from disk
    global known_encodings
    known_encodings = load_encodings()

    # Get courses based on role
    if current_user.is_admin():
        courses = Course.query.filter_by(is_active=True).all()
    else:
        courses = Course.query.filter_by(
            lecturer_id=current_user.id,
            is_active=True).all()

    if request.method == 'POST':
        photo     = request.files.get('photo')
        course_id = request.form.get('course_id', type=int)

        if not photo or not course_id:
            return jsonify({'error': 'Photo and course required'}), 400

        if not known_encodings:
            return jsonify({
                'error': 'No trained model found. Please train first.'
            }), 400

        # Save uploaded photo temporarily
        tmp_path = os.path.join('uploads', photo.filename)
        photo.save(tmp_path)

        # Run MTCNN + FaceNet pipeline
        faces   = detect_faces(tmp_path)
        results = []

        for face in faces:
            emb             = get_embedding(face['crop'])
            sid, confidence = identify_face(emb, known_encodings)

            results.append({
                'student_id': sid,
                'confidence': confidence,
                'box':        face['box']
            })

        # Clean up temp file
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

        return jsonify({
            'results':    results,
            'face_count': len(faces)
        })

    return render_template('take_attendance.html', courses=courses)


@app.route('/attendance/save', methods=['POST'])
@login_required
def save_attendance():
    data      = request.get_json()
    course_id = data.get('course_id')
    records   = data.get('records', [])
    today     = date.today()
    saved     = 0

    for rec in records:
        student = Student.query.filter_by(
            student_id=rec['student_id']).first()
        if not student:
            continue

        attendance = AttendanceRecord(
            student_id   = student.id,
            course_id    = course_id,
            session_date = today,
            session_time = datetime.now().time(),
            status       = rec.get('status', 'present'),
            confidence   = rec.get('confidence'),
            marked_by    = current_user.id
        )
        db.session.add(attendance)
        saved += 1

    db.session.commit()
    return jsonify({'success': True, 'saved': saved})


# ════════════════════════════════════════════
#   REPORTS
# ════════════════════════════════════════════
@app.route('/reports')
@login_required
def reports():
    if current_user.is_admin():
        records = (AttendanceRecord.query
                   .order_by(AttendanceRecord.session_date.desc())
                   .limit(200).all())
    else:
        records = (AttendanceRecord.query
                   .join(Course)
                   .filter(Course.lecturer_id == current_user.id)
                   .order_by(AttendanceRecord.session_date.desc())
                   .limit(200).all())

    return render_template('reports.html', records=records)


@app.route('/reports/export')
@login_required
def export_report():
    records = AttendanceRecord.query.all()
    rows = []

    for r in records:
        rows.append({
            'Student ID':    r.student.student_id,
            'Full Name':     r.student.full_name,
            'Department':    r.student.department,
            'Course':        r.course.name,
            'Course Code':   r.course.code,
            'Date':          r.session_date,
            'Time':          r.session_time,
            'Status':        r.status,
            'Confidence %':  r.confidence,
            'Marked By':     r.marker.full_name if r.marker else 'System'
        })

    df  = pd.DataFrame(rows)
    buf = io.BytesIO()
    df.to_excel(buf, index=False, sheet_name='Attendance')
    buf.seek(0)

    return send_file(
        buf,
        download_name='attendance_report.xlsx',
        as_attachment=True,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )


# ════════════════════════════════════════════
#   TRAINING
# ════════════════════════════════════════════
@app.route('/train', methods=['GET', 'POST'])
@login_required
@admin_required
def train_model():
    if request.method == 'POST':
        try:
            import subprocess
            result = subprocess.run(
                ['python', 'train.py'],
                capture_output=True,
                text=True,
                cwd=os.getcwd()
            )
            # Reload encodings after training
            global known_encodings
            known_encodings = load_encodings()

            return jsonify({
                'success': True,
                'output':  result.stdout,
                'errors':  result.stderr
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})

    return render_template('train_model.html')


# ════════════════════════════════════════════
#   USER MANAGEMENT
# ════════════════════════════════════════════
@app.route('/users')
@login_required
@admin_required
def manage_users():
    users = User.query.all()
    return render_template('users.html', users=users)


@app.route('/users/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_user():
    if request.method == 'POST':
        user = User(
            username   = request.form['username'],
            email      = request.form['email'],
            role       = request.form.get('role', 'lecturer'),
            full_name  = request.form.get('full_name'),
            department = request.form.get('department')
        )
        user.set_password(request.form['password'])
        db.session.add(user)
        db.session.commit()
        flash(f'User {user.username} created!', 'success')
        return redirect(url_for('manage_users'))

    return render_template('add_user.html')


# ════════════════════════════════════════════
#   RUN APP
# ════════════════════════════════════════════
if __name__ == '__main__':
    with app.app_context():
        create_tables()
    app.run(debug=True)