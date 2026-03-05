from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from flask_bcrypt import Bcrypt
from datetime import datetime
import json

db = SQLAlchemy()
bcrypt = Bcrypt()


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id         = db.Column(db.Integer, primary_key=True)
    username   = db.Column(db.String(80), unique=True, nullable=False)
    email      = db.Column(db.String(120), unique=True, nullable=False)
    password   = db.Column(db.String(200), nullable=False)
    role       = db.Column(db.String(20), default='lecturer')
    full_name  = db.Column(db.String(100))
    department = db.Column(db.String(100))
    is_active  = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    def set_password(self, password):
        self.password = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password, password)

    def is_admin(self):
        return self.role == 'admin'


class Student(db.Model):
    __tablename__ = 'students'
    id            = db.Column(db.Integer, primary_key=True)
    student_id    = db.Column(db.String(20), unique=True, nullable=False)
    full_name     = db.Column(db.String(100), nullable=False)
    email         = db.Column(db.String(120))
    department    = db.Column(db.String(100))
    year_of_study = db.Column(db.Integer)
    cgpa          = db.Column(db.Float)
    phone         = db.Column(db.String(20))
    advisor       = db.Column(db.String(100))
    photo_path    = db.Column(db.String(200))
    face_encoding = db.Column(db.Text)
    is_active     = db.Column(db.Boolean, default=True)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    def get_encoding(self):
        if self.face_encoding:
            import numpy as np
            return np.array(json.loads(self.face_encoding))
        return None

    def set_encoding(self, encoding_array):
        self.face_encoding = json.dumps(encoding_array.tolist())


class Course(db.Model):
    __tablename__ = 'courses'
    id          = db.Column(db.Integer, primary_key=True)
    code        = db.Column(db.String(20), unique=True, nullable=False)
    name        = db.Column(db.String(150), nullable=False)
    department  = db.Column(db.String(100))
    lecturer_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    lecturer    = db.relationship('User', backref='courses')
    is_active   = db.Column(db.Boolean, default=True)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)


class AttendanceRecord(db.Model):
    __tablename__ = 'attendance'
    id           = db.Column(db.Integer, primary_key=True)
    student_id   = db.Column(db.Integer, db.ForeignKey('students.id'))
    course_id    = db.Column(db.Integer, db.ForeignKey('courses.id'))
    session_date = db.Column(db.Date, nullable=False)
    session_time = db.Column(db.Time)
    status       = db.Column(db.String(10), default='present')
    confidence   = db.Column(db.Float)
    marked_by    = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)

    student = db.relationship('Student', backref='attendance_records')
    course  = db.relationship('Course', backref='attendance_records')
    marker  = db.relationship('User', backref='marked_records',
                               foreign_keys=[marked_by])