import base64
import io
import logging
import os
import pickle

import cv2
import numpy as np
from mtcnn import MTCNN
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

_detector = None


def get_detector():
    global _detector
    if _detector is None:
        _detector = MTCNN()
        logger.info("MTCNN detector initialised.")
    return _detector


def detect_faces(image_path):
    img_bgr = cv2.imread(image_path)
    if img_bgr is None:
        raise ValueError(f"Could not read image: {image_path}")

    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    h, w = img_rgb.shape[:2]
    if w > 1200:
        scale = 1200 / w
        img_rgb = cv2.resize(img_rgb, (1200, int(h * scale)))

    raw = get_detector().detect_faces(img_rgb)
    faces = []

    for r in raw:
        if r["confidence"] < 0.90:
            continue
        x, y, bw, bh = r["box"]
        x, y = max(0, x), max(0, y)
        crop = img_rgb[y: y + bh, x: x + bw]
        if crop.size == 0:
            continue
        pil_crop = Image.fromarray(crop).resize((160, 160))
        faces.append({
            "crop": pil_crop,
            "box": [x, y, bw, bh],
            "confidence": r["confidence"],
        })

    return faces


def get_embedding(face_pil):
    """Get 128-d face embedding using DeepFace + FaceNet."""
    from deepface import DeepFace

    # Convert PIL to numpy BGR for DeepFace
    face_array = np.array(face_pil)
    face_bgr   = cv2.cvtColor(face_array, cv2.COLOR_RGB2BGR)

    # Save temp file — DeepFace works best with file path
    tmp = os.path.join(BASE_DIR, "_tmp_face.jpg")
    cv2.imwrite(tmp, face_bgr)

    try:
        result = DeepFace.represent(
            img_path     = tmp,
            model_name   = "Facenet",
            enforce_detection = False   # face already cropped
        )
        emb = np.array(result[0]["embedding"])
        emb = emb / np.linalg.norm(emb)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)

    return emb


def identify_face(embedding, known_encodings, threshold=0.6):
    if not known_encodings:
        return "Unknown", 0.0

    best_id   = "Unknown"
    best_dist = float("inf")

    for sid, stored in known_encodings.items():
        dist = np.linalg.norm(embedding - stored)
        if dist < best_dist:
            best_dist = dist
            best_id   = sid

    if best_dist < threshold:
        confidence = round(max(0.0, 1 - (best_dist / threshold)) * 100, 1)
        return best_id, confidence

    return "Unknown", 0.0


def process_attendance_photo(image_path, known_encodings, threshold=0.6):
    faces   = detect_faces(image_path)
    results = []

    for face in faces:
        emb       = get_embedding(face["crop"])
        sid, conf = identify_face(emb, known_encodings, threshold)
        results.append({
            "student_id": sid,
            "confidence": conf,
            "box":        face["box"],
            "recognized": sid != "Unknown",
        })

    recognized = [r for r in results if r["recognized"]]
    unknown    = [r for r in results if not r["recognized"]]

    return {
        "results":          results,
        "face_count":       len(faces),
        "recognized_count": len(recognized),
        "unknown_count":    len(unknown),
        "annotated_image":  annotate_image(image_path, results),
    }


_COLOUR_OK  = (34, 197, 94)
_COLOUR_UNK = (239, 68, 68)
_BOX_WIDTH  = 3


def annotate_image(image_path, results):
    img    = Image.open(image_path).convert("RGB")
    orig_w = img.width
    scale  = orig_w / min(orig_w, 1200)
    draw   = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18
        )
    except Exception:
        font = ImageFont.load_default()

    for r in results:
        x, y, bw, bh = [int(v * scale) for v in r["box"]]
        colour = _COLOUR_OK if r["recognized"] else _COLOUR_UNK
        draw.rectangle([x, y, x + bw, y + bh], outline=colour, width=_BOX_WIDTH)

        label = (
            f"{r['student_id']}  {r['confidence']}%"
            if r["recognized"] else "Unknown"
        )

        try:
            bbox = draw.textbbox((x, y), label, font=font)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        except AttributeError:
            tw, th = draw.textsize(label, font=font)

        pad     = 4
        label_y = max(0, y - th - pad * 2)
        draw.rectangle(
            [x, label_y, x + tw + pad * 2, label_y + th + pad * 2],
            fill=colour,
        )
        draw.text((x + pad, label_y + pad), label, fill="white", font=font)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


def load_encodings():
    path = os.path.join(BASE_DIR, "models", "encodings.pkl")
    if not os.path.exists(path):
        return {}
    with open(path, "rb") as f:
        return pickle.load(f)


def save_encodings(encodings):
    models_dir = os.path.join(BASE_DIR, "models")
    os.makedirs(models_dir, exist_ok=True)
    path = os.path.join(models_dir, "encodings.pkl")
    with open(path, "wb") as f:
        pickle.dump(encodings, f)
    logger.info("Encodings saved (%d students).", len(encodings))