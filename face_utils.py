import numpy as np
import cv2
from PIL import Image
from mtcnn import MTCNN
import os
import pickle

# Load MTCNN detector once when app starts
detector = MTCNN()


def detect_faces(image_path):
    """
    STEP 1 from the paper: Use MTCNN to detect faces in image
    Returns list of detected faces with crops and bounding boxes
    """
    # Read the image
    img = cv2.imread(image_path)
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    # Resize if image is too large
    h, w = img_rgb.shape[:2]
    if w > 1200:
        scale = 1200 / w
        img_rgb = cv2.resize(img_rgb, (1200, int(h * scale)))

    # Run MTCNN detection
    results = detector.detect_faces(img_rgb)
    faces = []

    for r in results:
        # Only accept faces with 90%+ detection confidence
        # As described in the paper
        if r['confidence'] < 0.90:
            continue

        x, y, w, h = r['box']
        x, y = max(0, x), max(0, y)

        # Crop the face from image
        face_crop = img_rgb[y:y+h, x:x+w]

        # Resize to 160x160 for FaceNet
        face_pil = Image.fromarray(face_crop).resize((160, 160))

        faces.append({
            'crop': face_pil,
            'box': [x, y, w, h],
            'confidence': r['confidence']
        })

    return faces


def get_embedding(face_pil):
    """
    STEP 2 from the paper: Use FaceNet to convert face to 128 numbers
    These 128 numbers are the face's unique fingerprint
    """
    import tensorflow as tf

    # Convert PIL image to numpy array
    face_array = np.array(face_pil).astype('float32')

    # Normalize pixel values - required by FaceNet
    face_array = (face_array - 127.5) / 128.0

    # Add batch dimension
    face_tensor = np.expand_dims(face_array, axis=0)

    # Load FaceNet model
    model = load_facenet()

    # Get the 128 number embedding
    embedding = model.predict(face_tensor)[0]

    # L2 normalize as described in the paper
    embedding = embedding / np.linalg.norm(embedding)

    return embedding


def load_facenet():
    """Load the FaceNet keras model"""
    import tensorflow as tf
    model_path = os.path.join('models', 'facenet_keras.h5')

    if not os.path.exists(model_path):
        print("Downloading FaceNet model...")
        download_facenet()

    model = tf.keras.models.load_model(model_path, compile=False)
    return model


def download_facenet():
    """Download pretrained FaceNet model"""
    import urllib.request
    os.makedirs('models', exist_ok=True)
    url = 'https://github.com/nyoki-mtl/keras-facenet/releases/download/v1.0/facenet_keras.h5'
    print("Downloading FaceNet model (this happens once)...")
    urllib.request.urlretrieve(url, os.path.join('models', 'facenet_keras.h5'))
    print("FaceNet model downloaded!")


def identify_face(embedding, known_encodings, threshold=0.6):
    """
    STEP 3 from the paper: Match face against database
    Uses L2 distance - exactly as described in the paper
    Returns student_id and confidence percentage
    """
    best_id = 'Unknown'
    best_dist = float('inf')

    for student_id, stored_enc in known_encodings.items():
        # Calculate L2 distance between two face embeddings
        dist = np.linalg.norm(embedding - stored_enc)
        if dist < best_dist:
            best_dist = dist
            best_id = student_id

    # Convert distance to confidence percentage
    if best_dist < threshold:
        confidence = round(max(0, 1 - (best_dist / threshold)) * 100, 1)
        return best_id, confidence

    return 'Unknown', 0.0


def load_encodings():
    """Load saved face encodings from disk"""
    path = os.path.join('models', 'encodings.pkl')
    if not os.path.exists(path):
        return {}
    with open(path, 'rb') as f:
        return pickle.load(f)


def save_encodings(encodings):
    """Save face encodings to disk"""
    path = os.path.join('models', 'encodings.pkl')
    with open(path, 'wb') as f:
        pickle.dump(encodings, f)