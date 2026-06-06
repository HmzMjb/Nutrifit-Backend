"""
NutriFit – meal_snap.py
=======================
Enhanced food-recognition module with:
  • MobileNetV3-Large feature extraction (PyTorch)
  • Prototype-based food classification w/ similarity threshold
  • Zero-shot weight estimation via pixel-area scaling
  • OpenCV contour-based piece counting
  • ML re-ranking with a lightweight Ridge-Regression confidence layer
  • Multi-tile aggregation to prevent false positives
  • Fully structured output per detected food item

Dependencies
------------
  pip install torch torchvision pillow opencv-python-headless numpy pandas scikit-learn
"""

from __future__ import annotations

import io
import os
import re
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image, UnidentifiedImageError
from sklearn.linear_model import Ridge
from sklearn.preprocessing import LabelEncoder
from torchvision import models, transforms

warnings.filterwarnings("ignore", category=UserWarning)

# ─────────────────────────────────────────────
#  Paths  (edit to match your environment)
# ─────────────────────────────────────────────
BASE_CSV_DIR = os.path.dirname(os.path.abspath(__file__))
FOOD_CSV_PATH = os.path.join(BASE_CSV_DIR, "foods4.csv")
IMAGES_DIR = Path(BASE_CSV_DIR) / "Food Images"

# ─────────────────────────────────────────────
#  Tuneable constants
# ─────────────────────────────────────────────
SIMILARITY_THRESHOLD  = 0.60   # Cosine sim below this → discard
MIN_CONTOUR_AREA      = 500    # px²  – ignore tiny noise regions
CONTOUR_APPROX_FACTOR = 0.02   # polygon approximation precision
TILE_OVERLAP_PX       = 20     # pixel overlap between 2×2 tiles
ML_RIDGE_ALPHA        = 1.0    # regularisation for Ridge re-ranker


# ══════════════════════════════════════════════
#  Data containers
# ══════════════════════════════════════════════
@dataclass
class FoodItem:
    predicted_label: str
    similarity:      float
    piece_count:     int
    estimated_weight_g: float
    nutrition_found: bool
    quantity:    float               = 1.0

    unit:            str                 = "g"
    meal_id:         Optional[int]       = None
    calories:        Optional[float]     = None
    protein_g:       Optional[float]     = None
    carbs_g:         Optional[float]     = None
    fat_g:           Optional[float]     = None
    confidence:      Optional[float]     = None

@dataclass
class PrototypeMeta:
    """Feature vector + reference pixel area for one prototype image."""
    label:     str
    feature:   torch.Tensor               # shape (D,)
    area_px:   float                      # non-zero pixel count in prototype
    ref_weight_g: float = 100.0           # canonical weight (grams per 100 g)


# ══════════════════════════════════════════════
#  Main class
# ══════════════════════════════════════════════
class MealSnap:
    """
    Single-image food detection with weight & piece estimation.

    Usage
    -----
    snap = MealSnap()
    result = snap.estimate(image_bytes, quantity_g=None)   # auto-weight
    """

    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"[MealSnap] Using device: {self.device}")

        self.df_food:    Optional[pd.DataFrame]   = None
        self.prototypes: List[PrototypeMeta]      = []
        self._ml_ranker: Optional[Ridge]          = None
        self._label_enc: Optional[LabelEncoder]   = None

        self._init_model()
        self._load_food_csv()
        self._build_prototypes()
        self._train_ml_ranker()

    # ──────────────────────────────────────────
    #  1.  MobileNetV3 feature extractor
    # ──────────────────────────────────────────
    def _init_model(self) -> None:
        backbone = models.mobilenet_v3_large(weights="IMAGENET1K_V1").to(self.device)
        backbone.eval()

        # Keep features + global pooling; drop classifier
        self.feature_extractor = nn.Sequential(
            backbone.features,
            backbone.avgpool,
            nn.Flatten(),
        ).to(self.device)

        for p in self.feature_extractor.parameters():
            p.requires_grad = False

        self.img_transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                 std =[0.229, 0.224, 0.225]),
        ])
        print("[MealSnap] MobileNetV3-Large loaded (frozen).")

    # ──────────────────────────────────────────
    #  2.  Image → feature helpers
    # ──────────────────────────────────────────
    @torch.no_grad()
    def _extract_feature(self, img: Image.Image) -> torch.Tensor:
        """Return L2-normalised feature vector (D,) for a PIL image."""
        x = self.img_transform(img).unsqueeze(0).to(self.device)
        feat = self.feature_extractor(x)
        return F.normalize(feat, dim=1).squeeze(0)

    def _feature_from_bytes(self, image_bytes: bytes) -> Tuple[torch.Tensor, Image.Image]:
        try:
            img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        except UnidentifiedImageError:
            raise ValueError("Uploaded file is not a valid image.")
        return self._extract_feature(img), img

    def _feature_from_path(self, path: str | Path) -> Tuple[torch.Tensor, Image.Image]:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Image not found: {p}")
        img = Image.open(p).convert("RGB")
        return self._extract_feature(img), img

    # ──────────────────────────────────────────
    #  3.  Prototype gallery
    # ──────────────────────────────────────────
    @staticmethod
    def _food_pixel_area(img: Image.Image) -> float:
        """
        Approximate 'food' pixel area via HSV saturation + value mask.
        Falls back to total pixel count if no food-like region found.
        """
        arr = np.array(img.resize((224, 224)))
        hsv = cv2.cvtColor(arr, cv2.COLOR_RGB2HSV)

        # Broad mask: saturation > 30, value between 30–250
        mask = (hsv[:, :, 1] > 30) & (hsv[:, :, 2] > 30) & (hsv[:, :, 2] < 250)
        area = float(mask.sum())
        return area if area > 500 else float(224 * 224)

    def _build_prototypes(self) -> None:
        if not IMAGES_DIR.exists():
            raise FileNotFoundError(f"Images directory not found: {IMAGES_DIR}")

        for fname in sorted(IMAGES_DIR.iterdir()):
            if fname.suffix.lower() not in {".jpg", ".jpeg", ".png", ".jfif"}:
                continue
            label = fname.stem
            try:
                feat, img = self._feature_from_path(fname)
                area = self._food_pixel_area(img)
                self.prototypes.append(
                    PrototypeMeta(label=label, feature=feat,
                                  area_px=area, ref_weight_g=100.0)
                )
            except Exception as exc:
                print(f"  [warn] Skipping {fname.name}: {exc}")

        print(f"[MealSnap] Built {len(self.prototypes)} prototypes.")

    # ──────────────────────────────────────────
    #  4.  ML re-ranker  (Ridge regression)
    #      Predicts a 'confidence' score from
    #      the raw cosine-similarity vector,
    #      helping suppress false positives.
    # ──────────────────────────────────────────
    def _train_ml_ranker(self) -> None:
        """
        Self-supervised training: each prototype's own similarity against the
        full gallery is used as a training example (label = its own index).
        This gives the re-ranker a sense of inter-class margin.
        """
        if len(self.prototypes) < 2:
            print("[MealSnap] Too few prototypes to train ML re-ranker – skipped.")
            return

        proto_matrix = torch.stack([p.feature for p in self.prototypes])  # (N, D)
        sim_matrix   = torch.matmul(proto_matrix, proto_matrix.T).cpu().numpy()  # (N, N)

        labels = [p.label for p in self.prototypes]
        self._label_enc = LabelEncoder().fit(labels)
        y = self._label_enc.transform(labels)

        self._ml_ranker = Ridge(alpha=ML_RIDGE_ALPHA)
        self._ml_ranker.fit(sim_matrix, y)
        print("[MealSnap] ML re-ranker trained on prototype gallery.")

    def _ml_confidence(self, sim_vector: np.ndarray, predicted_label: str) -> float:
        """
        Return a [0, 1] confidence derived from the re-ranker's prediction.
        The closer the predicted class index is to the true predicted label
        index, the higher the confidence.
        """
        if self._ml_ranker is None or self._label_enc is None:
            return 1.0
        try:
            pred_val   = float(self._ml_ranker.predict(sim_vector.reshape(1, -1))[0])
            true_idx   = float(self._label_enc.transform([predicted_label])[0])
            n_classes  = len(self._label_enc.classes_)
            distance   = abs(pred_val - true_idx) / max(n_classes - 1, 1)
            confidence = float(np.clip(1.0 - distance, 0.0, 1.0))
            return confidence
        except Exception:
            return 1.0

    # ──────────────────────────────────────────
    #  5.  Weight estimation
    # ──────────────────────────────────────────
    def _estimate_weight(
        self,
        query_img:    Image.Image,
        proto:        PrototypeMeta,
        piece_count:  int,
    ) -> float:
        """
        Zero-shot weight via pixel-area ratio scaling.

            estimated_weight = ref_weight × (query_area / proto_area)

        Then multiply by piece count so each piece contributes proportionally.
        """
        query_area = self._food_pixel_area(query_img)
        ratio      = query_area / max(proto.area_px, 1.0)
        base_w     = proto.ref_weight_g * ratio
        # Per-piece weight × pieces  (avoids penalising multi-item plates)
        return round(float(base_w)) * max(piece_count, 1)

    # ──────────────────────────────────────────
    #  6.  Piece counting (OpenCV contours)
    # ──────────────────────────────────────────
    @staticmethod
    def _count_pieces(img: Image.Image) -> int:
        """
        Count discrete food items using:
          HSV → binary mask → morphological clean-up → contour detection.
        Returns at least 1.
        """
        arr  = np.array(img.resize((512, 512)))
        hsv  = cv2.cvtColor(arr, cv2.COLOR_RGB2HSV)

        # Saturation + value thresholds to isolate food regions
        mask = cv2.inRange(hsv,
                           np.array([0,  30,  30]),
                           np.array([180, 255, 240]))

        # Morphological closing fills gaps between pieces
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
        closed = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)

        # Opening removes small noise blobs
        opened = cv2.morphologyEx(closed, cv2.MORPH_OPEN, kernel, iterations=1)

        contours, _ = cv2.findContours(opened, cv2.RETR_EXTERNAL,
                                       cv2.CHAIN_APPROX_SIMPLE)

        valid = [c for c in contours if cv2.contourArea(c) >= MIN_CONTOUR_AREA]
        return max(len(valid), 1)

    # ──────────────────────────────────────────
    #  7.  Multi-tile feature aggregation
    # ──────────────────────────────────────────
    def _tile_features(self, img: Image.Image) -> List[torch.Tensor]:
        """
        Extract features from whole image + 2×2 overlapping tiles.
        Aggregation over tiles improves recall for multi-food plates.
        """
        W, H   = img.size
        feats  = [self._extract_feature(img)]   # whole image

        for r in range(2):
            for c in range(2):
                x1 = int(c / 2 * W)
                y1 = int(r / 2 * H)
                x2 = min(W, int((c + 1) / 2 * W) + TILE_OVERLAP_PX)
                y2 = min(H, int((r + 1) / 2 * H) + TILE_OVERLAP_PX)
                tile = img.crop((x1, y1, x2, y2))
                feats.append(self._extract_feature(tile))

        return feats

    # ──────────────────────────────────────────
    #  8.  CSV handling
    # ──────────────────────────────────────────
    def _load_food_csv(self) -> None:
        df = pd.read_csv(FOOD_CSV_PATH)
        df.columns = df.columns.str.strip()

        required = ["food_name", "calories", "fat_g", "protein_g", "carbs_g"]
        missing  = [c for c in required if c not in df.columns]
        if missing:
            raise KeyError(f"Missing columns in CSV: {missing}")

        df["meal_id"] = range(1, len(df) + 1)
        self.df_food  = df
        print(f"[MealSnap] CSV loaded: {len(df)} food entries.")

    @staticmethod
    def _normalise_name(s: str) -> str:
        s = s.lower().strip()
        s = re.sub(r"[_\-]", " ", s)
        return re.sub(r"\s+", " ", s)

    def _find_food_row(self, name: str) -> Optional[pd.Series]:
        target   = self._normalise_name(name)
        df_norm  = self.df_food["food_name"].astype(str).apply(self._normalise_name)

        exact = df_norm == target
        if exact.any():
            return self.df_food[exact].iloc[0]

        contains = df_norm.str.contains(re.escape(target), na=False)
        if contains.any():
            return self.df_food[contains].iloc[0]

        return None

    # ──────────────────────────────────────────
    #  9.  Core estimation pipeline
    # ──────────────────────────────────────────
    def estimate(
        self,
        image_bytes: bytes,
        quantity_g:  Optional[float] = None,
    ) -> Dict:
        """
        Main entry point.

        Parameters
        ----------
        image_bytes : bytes
            Raw bytes of the uploaded image.
        quantity_g : float, optional
            If provided, override automatic weight estimation.

        Returns
        -------
        dict  with key "items" → list of FoodItem dicts
        """
        # ── Load image ──────────────────────────
        try:
            img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        except UnidentifiedImageError:
            raise ValueError("Uploaded file is not a valid image.")

        if not self.prototypes:
            raise RuntimeError("No prototypes loaded; cannot classify.")

        # ── Build prototype matrix ───────────────
        proto_matrix = torch.stack([p.feature for p in self.prototypes])  # (N, D)

        # ── Tile-based feature extraction ────────
        tile_feats = self._tile_features(img)

        # Accumulate best similarity per label across all tiles
        best: Dict[str, Dict] = {}   # label → {sim, proto_idx}

        for feat in tile_feats:
            sims      = torch.matmul(proto_matrix, feat).cpu().numpy()  # (N,)
            top_idx   = int(np.argmax(sims))
            top_label = self.prototypes[top_idx].label
            top_sim   = float(sims[top_idx])

            if top_sim < SIMILARITY_THRESHOLD:
                continue   # ← false-positive guard

            if top_label not in best or top_sim > best[top_label]["sim"]:
                best[top_label] = {
                    "sim":       top_sim,
                    "proto_idx": top_idx,
                    "sim_vec":   sims,
                }

        if not best:
            return {"items": [], "message": "No food detected above similarity threshold."}

        # ── Piece counting (once on whole image) ─
        piece_count = self._count_pieces(img)

        # ── Build result items ───────────────────
        print(f"\n{'=' * 50}")
        print(f"  Detected {len(best)} food item(s)  |  Pieces: {piece_count}")
        print(f"{'=' * 50}")

        items: List[FoodItem] = []

        for label, meta in best.items():
            proto       = self.prototypes[meta["proto_idx"]]
            similarity  = meta["sim"]
            sim_vec     = meta["sim_vec"]

            # ML confidence
            confidence = self._ml_confidence(sim_vec, label)

            # Weight
            if quantity_g is not None:
                w_g = float(quantity_g)
            else:
                w_g = self._estimate_weight(img, proto, piece_count)

            # Nutrition lookup
            row = self._find_food_row(label)

            if row is None:
                item = FoodItem(
                    predicted_label=label,
                    similarity=round(similarity, 4),
                    piece_count=piece_count,
                    estimated_weight_g=w_g,
                    nutrition_found=False,
                    confidence=round(confidence, 4),
                )
            else:
                factor = w_g / float(row["quantity"]) if str(row["unit"]).strip().lower() == "g" else 1.0

                item = FoodItem(
                    predicted_label=label,
                    similarity=round(similarity, 4),
                    piece_count=piece_count,
                    estimated_weight_g=w_g,
                    nutrition_found=True,
                    quantity=float(row["quantity"]),
                    unit=str(row["unit"]).strip(),
                    meal_id=int(row["meal_id"]),
                    calories=round(row["calories"] * factor, 2),
                    protein_g=round(row["protein_g"] * factor, 2),
                    carbs_g=round(row["carbs_g"] * factor, 2),
                    fat_g=round(row["fat_g"] * factor, 2),
                    confidence=round(confidence, 4),
                )

            items.append(item)

            print(f"  • {label:<25} sim={similarity:.3f}  "
                  f"conf={confidence:.3f}  wt={w_g:.1f}g    pieces = {piece_count}   unit={str(row.get('unit', 'g')) if row is not None else 'g'}")

        print(f"{'=' * 50}\n")

        return {
            "items": [vars(i) for i in items],
            "total_pieces": piece_count,
            "total_estimated_weight_g": round(sum(i.estimated_weight_g for i in items), 1),
        }


# ══════════════════════════════════════════════
#  Singleton  (loaded once at import time)
# ══════════════════════════════════════════════
_model: Optional[MealSnap] = None


def get_model() -> MealSnap:
    """Return the global singleton, initialising it on first call."""
    global _model
    if _model is None:
        _model = MealSnap()
    return _model


# ──────────────────────────────────────────────
#  Backward-compatible public function
# ──────────────────────────────────────────────
def estimate_from_image_bytes(
    image_bytes: bytes,
    quantity_g:  Optional[float] = None,
) -> Dict:
    """
    Drop-in replacement for the original function.
    quantity_g is now optional; omit it for fully automatic weight estimation.
    """
    if quantity_g is not None:
        try:
            quantity_g = float(quantity_g)
        except (ValueError, TypeError):
            quantity_g = None
    return get_model().estimate(image_bytes, quantity_g)


# ──────────────────────────────────────────────
#  Quick smoke-test
# ──────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python meal_snap.py <image_path> [quantity_g]")
        sys.exit(1)

    img_path   = Path(sys.argv[1])
    quantity   = float(sys.argv[2]) if len(sys.argv) > 2 else None

    with open(img_path, "rb") as fh:
        raw = fh.read()

    snap   = MealSnap()
    result = snap.estimate(raw, quantity)

    print("\n── Result ──────────────────────────────────")
    for item in result["items"]:
        print(f"\n  Food       : {item['predicted_label']}")
        print(f"  Similarity : {item['similarity']}")
        print(f"  Confidence : {item['confidence']}")
        print(f"  Weight (g) : {item['estimated_weight_g']}")
        print(f"  Pieces     : {item['piece_count']}")
        if item["nutrition_found"]:
            print(f"  Calories   : {item['calories']} kcal")
            print(f"  Protein    : {item['protein_g']} g")
            print(f"  Carbs      : {item['carbs_g']} g")
            print(f"  Fat        : {item['fat_g']} g")
        else:
            print("  Nutrition  : not found in CSV")
    print(f"\n  Total weight : {result['total_estimated_weight_g']} g")
    print(f"  Total pieces : {result['total_pieces']}")