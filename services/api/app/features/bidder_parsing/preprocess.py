"""
TenderLens — F-03 OpenCV Preprocessing
Runs before OCR call — in the api container, NOT in the OCR service.

Steps from PRD Section 3.3:
  1. Deskew   — Hough line detection, rotate to within 0.5°
  2. Binarise — Adaptive Gaussian threshold, denoise
  3. Glare    — Highlights suppression for phone-camera photos
  4. Perspective — Four-corner correction for angled photos
"""

import cv2
import numpy as np
from typing import Optional


class ImagePreprocessor:
    """
    OpenCV preprocessing pipeline applied before sending images to OCR.
    Each step is modular and can be toggled independently.
    """

    def full_pipeline(self, image_bytes: bytes) -> bytes:
        """
        Run the full preprocessing pipeline on an image.
        Returns preprocessed image as PNG bytes.
        """
        img = self._bytes_to_cv2(image_bytes)

        if img is None:
            return image_bytes  # Return original if decoding fails

        # Step 1: Deskew
        img = self.deskew(img)

        # Step 2: Binarise
        img = self.binarise(img)

        # Step 3: Glare fix
        img = self.fix_glare(img)

        # Step 4: Perspective correction (only for photos)
        img = self.correct_perspective(img)

        return self._cv2_to_bytes(img)

    def deskew(self, img: np.ndarray) -> np.ndarray:
        """
        Deskew using Hough line detection.
        Rotates to within 0.5 degrees of horizontal.
        """
        try:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
            edges = cv2.Canny(gray, 50, 150, apertureSize=3)

            lines = cv2.HoughLinesP(
                edges, 1, np.pi / 180,
                threshold=100,
                minLineLength=100,
                maxLineGap=10,
            )

            if lines is None or len(lines) == 0:
                return img

            # Calculate median angle
            angles = []
            for line in lines:
                x1, y1, x2, y2 = line[0]
                angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
                if abs(angle) < 45:  # Only consider near-horizontal lines
                    angles.append(angle)

            if not angles:
                return img

            median_angle = np.median(angles)

            if abs(median_angle) < 0.5:
                return img  # Already straight

            # Rotate
            h, w = img.shape[:2]
            center = (w // 2, h // 2)
            rotation_matrix = cv2.getRotationMatrix2D(center, median_angle, 1.0)
            rotated = cv2.warpAffine(
                img, rotation_matrix, (w, h),
                flags=cv2.INTER_CUBIC,
                borderMode=cv2.BORDER_REPLICATE,
            )
            return rotated

        except Exception:
            return img

    def binarise(self, img: np.ndarray) -> np.ndarray:
        """
        Adaptive Gaussian threshold + denoise.
        Converts to clean black-and-white for OCR.
        """
        try:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img

            # Denoise
            denoised = cv2.fastNlMeansDenoising(gray, h=10)

            # Adaptive threshold
            binary = cv2.adaptiveThreshold(
                denoised, 255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                blockSize=11,
                C=2,
            )

            # Convert back to BGR for consistency
            return cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)

        except Exception:
            return img

    def fix_glare(self, img: np.ndarray) -> np.ndarray:
        """
        Suppress highlight glare from phone-camera photos.
        Uses CLAHE (Contrast Limited Adaptive Histogram Equalisation).
        """
        try:
            lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
            l_channel, a, b = cv2.split(lab)

            # CLAHE on lightness channel
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            cl = clahe.apply(l_channel)

            merged = cv2.merge([cl, a, b])
            result = cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)
            return result

        except Exception:
            return img

    def correct_perspective(self, img: np.ndarray) -> np.ndarray:
        """
        Four-corner perspective correction for angled photos.
        Detects the document boundary and warps to a rectangle.
        """
        try:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            edges = cv2.Canny(blurred, 75, 200)

            contours, _ = cv2.findContours(
                edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE
            )

            if not contours:
                return img

            # Find the largest quadrilateral contour
            contours = sorted(contours, key=cv2.contourArea, reverse=True)

            for contour in contours[:5]:
                peri = cv2.arcLength(contour, True)
                approx = cv2.approxPolyDP(contour, 0.02 * peri, True)

                if len(approx) == 4:
                    # Found a quadrilateral — warp perspective
                    pts = approx.reshape(4, 2).astype(np.float32)
                    rect = self._order_points(pts)

                    (tl, tr, br, bl) = rect
                    width_a = np.linalg.norm(br - bl)
                    width_b = np.linalg.norm(tr - tl)
                    max_width = int(max(width_a, width_b))

                    height_a = np.linalg.norm(tr - br)
                    height_b = np.linalg.norm(tl - bl)
                    max_height = int(max(height_a, height_b))

                    dst = np.array([
                        [0, 0],
                        [max_width - 1, 0],
                        [max_width - 1, max_height - 1],
                        [0, max_height - 1],
                    ], dtype=np.float32)

                    matrix = cv2.getPerspectiveTransform(rect, dst)
                    warped = cv2.warpPerspective(img, matrix, (max_width, max_height))
                    return warped

            return img

        except Exception:
            return img

    @staticmethod
    def _order_points(pts: np.ndarray) -> np.ndarray:
        """Order 4 points as: top-left, top-right, bottom-right, bottom-left."""
        rect = np.zeros((4, 2), dtype=np.float32)
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]  # top-left has smallest sum
        rect[2] = pts[np.argmax(s)]  # bottom-right has largest sum
        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]  # top-right
        rect[3] = pts[np.argmax(diff)]  # bottom-left
        return rect

    @staticmethod
    def _bytes_to_cv2(image_bytes: bytes) -> Optional[np.ndarray]:
        """Convert bytes to OpenCV image."""
        nparr = np.frombuffer(image_bytes, np.uint8)
        return cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    @staticmethod
    def _cv2_to_bytes(img: np.ndarray) -> bytes:
        """Convert OpenCV image to PNG bytes."""
        _, encoded = cv2.imencode(".png", img)
        return encoded.tobytes()
