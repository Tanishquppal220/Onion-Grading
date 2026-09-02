from pathlib import Path

import cv2
from pydantic import BaseModel
from ultralytics import YOLO


class GradingResult(BaseModel):
    onion: int = 0
    double_split: int = 0
    rotten: int = 0
    sprout: int = 0
    
    # Size categories
    small: int = 0
    medium: int = 0
    large: int = 0
    
    annotated_image_filename: str | None = None

class OnionGrader:
    # Define arbitrary PPI and conversion factor
    # 1 inch = 25.4 mm
    PPI = 40.0  
    MM_PER_PIXEL = 25.4 / PPI 

    def __init__(self, model_path: str | Path):
        """Initializes the YOLO model from the given path."""
        self.model = YOLO(str(model_path))
        self.names = self.model.names  # {0: 'double_split', 1: 'onion', 2: 'rotten', 3: 'sprout'}

    def process_image(self, image_path: Path, output_dir: Path) -> GradingResult:
        """
        Runs YOLO inference on the image, counts instances of each class,
        calculates size based on PPI, and saves an annotated version of the image.
        """
        from typing import Any
        
        # Run inference (cast to Any to bypass Pylance false-positive type stubs)
        results: Any = self.model.predict(source=str(image_path), save=False, verbose=False)
        result = results[0]
        
        # Count classes
        counts = {"onion": 0, "double_split": 0, "rotten": 0, "sprout": 0}
        sizes = {"small": 0, "medium": 0, "large": 0}
        
        for box in result.boxes:
            class_id = int(box.cls[0].item())
            class_name = self.names.get(class_id, "unknown")
            if class_name in counts:
                counts[class_name] += 1
                
            # Calculate size in mm
            # box.xywh[0] contains [x_center, y_center, width, height]
            width = box.xywh[0][2].item()
            height = box.xywh[0][3].item()
            
            # Estimate diameter using the largest dimension
            diameter_px = max(width, height)
            diameter_mm = diameter_px * self.MM_PER_PIXEL
            
            # Categorize size
            if diameter_mm < 40.0:
                sizes["small"] += 1
            elif diameter_mm <= 70.0:
                sizes["medium"] += 1
            else:
                sizes["large"] += 1
                
        # Save annotated image
        annotated_img = result.plot()
        annotated_filename = f"graded_{image_path.name}"
        annotated_path = output_dir / annotated_filename
        cv2.imwrite(str(annotated_path), annotated_img)
        
        return GradingResult(
            **counts,
            **sizes,
            annotated_image_filename=annotated_filename
        )
