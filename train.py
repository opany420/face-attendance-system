import os
import pickle
import numpy as np
from face_utils import detect_faces, get_embedding

BASE_DIR       = os.path.dirname(os.path.abspath(__file__))
STUDENT_IMAGES = os.path.join(BASE_DIR, "student_images")
MODELS_FOLDER  = os.path.join(BASE_DIR, "models")


def train():
    print("=" * 50)
    print("  FRAS - Face Recognition Training")
    print("=" * 50)

    if not os.path.exists(STUDENT_IMAGES):
        print("ERROR: student_images folder not found!")
        return

    # Walk ALL subfolders and collect images per student_id
    # Handles student IDs with slashes like IN13/00122/24
    # which get stored as nested folders IN13\00122\24
    student_image_map = {}

    for root, dirs, files in os.walk(STUDENT_IMAGES):
        images = [
            f for f in files
            if f.lower().endswith(('.jpg', '.jpeg', '.png'))
        ]
        if not images:
            continue

        # Convert folder path back to student_id
        rel_path   = os.path.relpath(root, STUDENT_IMAGES)
        student_id = rel_path.replace(os.sep, '/')

        if student_id not in student_image_map:
            student_image_map[student_id] = []
        student_image_map[student_id].extend(
            [os.path.join(root, f) for f in images]
        )

    if not student_image_map:
        print("No student images found!")
        print(f"Add photos to: {STUDENT_IMAGES}/<student_id>/")
        return

    print(f"Found {len(student_image_map)} students...\n")

    encodings     = {}
    success_count = 0
    error_count   = 0

    for student_id, image_paths in student_image_map.items():
        print(f"  Processing {student_id} ({len(image_paths)} images)...")
        embeddings = []

        for img_path in image_paths:
            try:
                faces = detect_faces(img_path)
                if not faces:
                    continue
                best_face = max(faces, key=lambda x: x['confidence'])
                emb = get_embedding(best_face['crop'])
                embeddings.append(emb)
            except Exception as e:
                print(f"    Error on {os.path.basename(img_path)}: {e}")

        if embeddings:
            encodings[student_id] = np.mean(embeddings, axis=0)
            print(f"  OK: {student_id} — {len(embeddings)} faces encoded")
            success_count += 1
        else:
            print(f"  FAILED: No faces detected for {student_id}")
            error_count += 1

    os.makedirs(MODELS_FOLDER, exist_ok=True)
    encodings_path = os.path.join(MODELS_FOLDER, "encodings.pkl")
    with open(encodings_path, "wb") as f:
        pickle.dump(encodings, f)

    print(f"\n{'=' * 50}")
    print(f"  Training Complete!")
    print(f"  Students encoded: {success_count}")
    print(f"  Errors:           {error_count}")
    print(f"  Saved to:         {encodings_path}")
    print("=" * 50)


if __name__ == '__main__':
    train()