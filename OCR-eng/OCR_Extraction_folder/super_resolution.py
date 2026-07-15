import cv2
import os


BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

MODEL_PATH = os.path.join(
    BASE_DIR,
    "models",
    "EDSR_x2.pb"
)

sr_model = None


# =========================================================
# LOAD MODEL LAZILY
# =========================================================

def load_sr_model():

    global sr_model

    if sr_model is None:

        sr_model = cv2.dnn_superres.DnnSuperResImpl_create()

        sr_model.readModel(MODEL_PATH)

        sr_model.setModel(
            "edsr",
            2
        )

        print("SR Model Loaded")

    return sr_model


# =========================================================
# BLUR DETECTION
# =========================================================

def detect_blur(image):

    gray = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2GRAY
    )

    return cv2.Laplacian(
        gray,
        cv2.CV_64F
    ).var()


# =========================================================
# APPLY SR
# =========================================================

def apply_super_resolution(image_path, output_folder):

    os.makedirs(output_folder, exist_ok=True)

    image = cv2.imread(image_path)

    if image is None:
        raise ValueError(f"Cannot read image: {image_path}")

    h, w = image.shape[:2]

    blur_score = detect_blur(image)

    print(f"Blur Score: {blur_score}")

    result = image

    # =====================================================
    # INDUSTRIAL DECISION LOGIC
    # =====================================================

    # should_apply_sr = (
    #     blur_score < 80
    #     and max(h, w) < 1600
    # )


    should_apply_sr = (
        blur_score < 120
        or (blur_score < 200 and max(h, w) < 1500)
    )

    if should_apply_sr:

        print("Applying Super Resolution")

        try:

            sr = load_sr_model()

            result = sr.upsample(image)

            print("SR Applied Successfully")

        except Exception as e:

            print(f"SR Failed: {e}")

            result = image

    else:

        print("Skipping SR")

    output_path = os.path.join(
        output_folder,
        os.path.basename(image_path)
    )

    cv2.imwrite(output_path, result)

    return output_path