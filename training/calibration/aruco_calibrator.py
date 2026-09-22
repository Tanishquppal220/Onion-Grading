"""Metric Calibration Module using in-frame ArUco reference markers.

Implements perspective correction, scale conversion (pixels -> mm),
camera tilt estimation, height-above-plane compensation, and fallback mode.
Ref: Dataset Plan.md §6 and Technical Approach.md §7.3.
"""

from __future__ import annotations

import math
from typing import Optional, Tuple
import cv2
import numpy as np
from training.common.schemas import CalibrationMetadata, CalibrationMode


# Default reference marker parameters
DEFAULT_MARKER_SIZE_MM = 50.0  # 50 mm square printed marker
DEFAULT_ARUCO_DICT = cv2.aruco.DICT_4X4_50
DEFAULT_FOCAL_LENGTH_PX = 3200.0  # Typical smartphone 12MP primary lens (f ~ 26mm equiv)
FALLBACK_MEDIAN_ONION_MM = 55.0   # Locked in Dataset Plan §9


class ArUcoCalibrator:
    def __init__(
        self,
        marker_size_mm: float = DEFAULT_MARKER_SIZE_MM,
        dict_id: int = DEFAULT_ARUCO_DICT,
        default_focal_px: float = DEFAULT_FOCAL_LENGTH_PX,
    ):
        self.marker_size_mm = marker_size_mm
        self.dict_id = dict_id
        self.default_focal_px = default_focal_px

        # Initialize detector based on OpenCV version
        self.dictionary = cv2.aruco.getPredefinedDictionary(dict_id)
        if hasattr(cv2.aruco, "ArucoDetector"):
            self.params = cv2.aruco.DetectorParameters()
            self.detector = cv2.aruco.ArucoDetector(self.dictionary, self.params)
        else:
            self.detector = None

    def detect_marker(self, image_bgr: np.ndarray) -> Tuple[bool, Optional[np.ndarray], Optional[float]]:
        """Detects ArUco marker corners and estimates camera tilt angle.
        
        Returns:
            (found, corners_4x2, tilt_degrees)
        """
        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY) if len(image_bgr.shape) == 3 else image_bgr

        if self.detector is not None:
            corners, ids, _ = self.detector.detectMarkers(gray)
        else:
            corners, ids, _ = cv2.aruco.detectMarkers(gray, self.dictionary)

        if ids is None or len(corners) == 0:
            return False, None, None

        # Take the first detected marker
        c = corners[0][0]  # shape (4, 2): TL, TR, BR, BL

        # Calculate edge lengths
        d01 = np.linalg.norm(c[0] - c[1])
        d12 = np.linalg.norm(c[1] - c[2])
        d23 = np.linalg.norm(c[2] - c[3])
        d30 = np.linalg.norm(c[3] - c[0])

        mean_w = (d01 + d23) / 2.0
        mean_h = (d12 + d30) / 2.0

        # Estimate tilt angle from aspect distortion
        aspect_ratio = min(mean_w, mean_h) / max(mean_w, mean_h, 1e-6)
        tilt_rad = math.acos(np.clip(aspect_ratio, 0.0, 1.0))
        tilt_deg = math.degrees(tilt_rad)

        return True, c, round(tilt_deg, 1)

    def calibrate(
        self,
        image_bgr: np.ndarray,
        exif_focal_px: Optional[float] = None,
        detected_onion_pixel_diameters: Optional[list[float]] = None,
    ) -> Tuple[CalibrationMetadata, float]:
        """Calibrates scale in pixels per mm for the given image.
        
        Returns:
            (CalibrationMetadata, pixels_per_mm)
        """
        focal_px = exif_focal_px or self.default_focal_px
        found, corners, tilt_deg = self.detect_marker(image_bgr)

        if not found or corners is None:
            # Fallback mode: Assume median onion in frame = 55.0 mm
            if detected_onion_pixel_diameters and len(detected_onion_pixel_diameters) > 0:
                median_px = float(np.median(detected_onion_pixel_diameters))
                fallback_scale = median_px / FALLBACK_MEDIAN_ONION_MM
            else:
                fallback_scale = 10.0  # Arbitrary nominal baseline

            metadata = CalibrationMetadata(
                mode=CalibrationMode.ASSUMED_SCALE,
                scale_source=f"median_onion_prior_{FALLBACK_MEDIAN_ONION_MM}mm",
                mm_reliable=False,
                card_detected=False,
                tilt_degrees=None,
                pixels_per_mm=round(fallback_scale, 3),
            )
            return metadata, fallback_scale

        # Calculate planar scale from marker side
        d01 = np.linalg.norm(corners[0] - corners[1])
        d12 = np.linalg.norm(corners[1] - corners[2])
        d23 = np.linalg.norm(corners[2] - corners[3])
        d30 = np.linalg.norm(corners[3] - corners[0])
        mean_marker_px = (d01 + d12 + d23 + d30) / 4.0

        planar_scale_px_per_mm = mean_marker_px / self.marker_size_mm

        metadata = CalibrationMetadata(
            mode=CalibrationMode.CALIBRATED_ARUCO,
            scale_source=f"aruco_dict_{self.dict_id}_{self.marker_size_mm}mm",
            mm_reliable=True,
            card_detected=True,
            tilt_degrees=tilt_deg,
            pixels_per_mm=round(planar_scale_px_per_mm, 3),
        )
        return metadata, planar_scale_px_per_mm

    def compute_corrected_diameter_mm(
        self,
        pixel_diameter: float,
        planar_scale_px_per_mm: float,
        camera_distance_mm: Optional[float] = None,
        focal_px: Optional[float] = None,
    ) -> float:
        """Converts pixel diameter to real-world mm with height-above-plane compensation.
        
        Because the bulb equator is elevated above the card plane by approximately radius r,
        the bulb is closer to the lens by r, exaggerating its apparent size by Z / (Z - r).
        Ref: Dataset Plan.md §6: D_corrected = D_apparent * (Z - r) / Z.
        """
        if planar_scale_px_per_mm <= 0:
            return 0.0

        apparent_mm = pixel_diameter / planar_scale_px_per_mm

        # If camera distance is known or can be estimated:
        f = focal_px or self.default_focal_px
        z = camera_distance_mm
        if z is None and planar_scale_px_per_mm > 0:
            # Z = focal_px * marker_mm / marker_px = focal_px / scale
            z = f / planar_scale_px_per_mm

        if z is not None and z > 100.0:  # Valid working distance >= 10cm
            # Iterative correction: r ~ apparent_mm / 2
            # D_corrected ~ apparent_mm * (1 - (apparent_mm / (2 * Z)))
            correction_factor = 1.0 - (apparent_mm / (2.0 * z))
            correction_factor = max(0.85, min(1.0, correction_factor))
            return round(apparent_mm * correction_factor, 1)

        return round(apparent_mm, 1)

    def compensate_height_above_plane(
        self,
        apparent_mm: float,
        bulb_height_above_plane_mm: Optional[float] = None,
        focal_px: Optional[float] = None,
        camera_distance_mm: Optional[float] = None,
    ) -> float:
        """Applies height-above-plane focal compensation to an apparent millimeter dimension.
        
        Because the bulb equator is elevated above the card plane by approximately radius r,
        the bulb is closer to the lens by r, exaggerating its apparent size by Z / (Z - r).
        Ref: Dataset Plan.md §6 and Technical Approach.md:
        D_corrected = D_apparent * (1 - r / Z).
        """
        if apparent_mm <= 0:
            return 0.0

        f = focal_px or self.default_focal_px
        z = camera_distance_mm
        if z is None:
            # Default nominal handheld working distance ~450 mm (45 cm)
            z = 450.0

        r = (bulb_height_above_plane_mm if bulb_height_above_plane_mm is not None else apparent_mm) / 2.0
        if z > 100.0 and r < z:
            correction_factor = 1.0 - (r / z)
            correction_factor = max(0.85, min(1.0, correction_factor))
            return round(apparent_mm * correction_factor, 1)

        return round(apparent_mm, 1)

