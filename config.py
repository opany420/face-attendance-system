import os

class Config:
    # Secret key protects user sessions
    SECRET_KEY = 'fras-secret-key-2024'

    # Database file - created automatically
    SQLALCHEMY_DATABASE_URI = 'sqlite:///fras.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Folders
    UPLOAD_FOLDER = 'uploads'
    STUDENT_IMAGES_FOLDER = 'student_images'
    MODELS_FOLDER = 'models'

    # Max upload size - 16MB
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024

    # Allowed photo types
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

    # Face recognition sensitivity
    FACE_THRESHOLD = 0.6