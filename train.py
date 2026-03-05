"""
TRAINING SCRIPT - Run this after adding new students
Command: python train.py
This teaches the system to recognise each student's face
Based on the paper: MTCNN detection + FaceNet embeddings
"""
import os
import pickle
import numpy as np
from face_utils import detect_faces, get_embedding

STUDENT_IMAGES_FOLDER = 'student_images'
MODELS_FOLDER = 'models'


def train():
    print("=" * 50)
    print("  FRAS - Face Recognition Training")
    print("=" * 50)
    print()

    # Check student images folder exists
    if not os.path.exists(STUDENT_IMAGES_FOLDER):
        print("ERROR: student_images folder not found!")
        return

    # Get all student folders
    student_folders = [
        f for f in os.listdir(STUDENT_IMAGES_FOLDER)
        if os.path.isdir(os.path.join(STUDENT_IMAGES_FOLDER, f))
    ]

    if not student_folders:
        print("No student folders found!")
        print("Add photos to student_images/STUDENT_ID/ folders first")
        return

    print(f"Found {len(student_folders)} students to process...")
    print()

    encodings = {}
    success_count = 0
    error_count = 0

    for student_id in student_folders:
        folder = os.path.join(STUDENT_IMAGES_FOLDER, student_id)

        # Get all images in this student's folder
        images = [
            f for f in os.listdir(folder)
            if f.lower().endswith(('.jpg', '.jpeg', '.png'))
        ]

        if not images:
            print(f"  WARNING: No images found for {student_id}")
            error_count += 1
            continue

        print(f"  Processing {student_id} ({len(images)} images)...")

        embeddings = []

        for img_file in images:
            img_path = os.path.join(folder, img_file)

            try:
                # Step 1: Detect faces using MTCNN
                faces = detect_faces(img_path)

                if not faces:
                    continue

                # Use the most confident face detected
                best_face = max(faces, key=lambda x: x['confidence'])

                # Step 2: Get FaceNet embedding
                emb = get_embedding(best_face['crop'])
                embeddings.append(emb)

            except Exception as e:
                print(f"    Error processing {img_file}: {e}")
                continue

        if embeddings:
            # Calculate MEAN embedding for this student
            # Using mean of multiple photos improves accuracy
            # As recommended in the paper
            encodings[student_id] = np.mean(embeddings, axis=0)
            print(f"  OK: {student_id} - {len(embeddings)} faces encoded")
            success_count += 1
        else:
            print(f"  FAILED: No faces detected for {student_id}")
            error_count += 1

    # Save encodings to disk
    os.makedirs(MODELS_FOLDER, exist_ok=True)
    encodings_path = os.path.join(MODELS_FOLDER, 'encodings.pkl')

    with open(encodings_path, 'wb') as f:
        pickle.dump(encodings, f)

    print()
    print("=" * 50)
    print(f"  Training Complete!")
    print(f"  Students encoded: {success_count}")
    print(f"  Errors: {error_count}")
    print(f"  Model saved to: {encodings_path}")
    print("=" * 50)


if __name__ == '__main__':
    train()