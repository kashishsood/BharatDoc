"""
BharatDoc-VLM: Near-Duplicate Detection
=========================================

Uses datasketch MinHash LSH for text-based deduplication and imagehash
for perceptual image deduplication. Flags near-duplicates if either
similarity exceeds 0.95 threshold.

Why datasketch over simhash: datasketch is actively maintained, well-documented,
and provides MinHash LSH which scales to large datasets with sub-linear query time.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

SIMILARITY_THRESHOLD = 0.95


@dataclass
class DuplicateResult:
    """Result of duplicate detection for a single document."""
    doc_id: str
    is_duplicate: bool
    duplicate_of: Optional[str] = None
    text_similarity: float = 0.0
    image_similarity: float = 0.0


class DocumentDeduplicator:
    """
    Dual-mode deduplication using text MinHash + perceptual image hashing.
    
    Why two methods:
    - Text similarity catches docs with same content but different scans
    - Image similarity catches identical scans with minor OCR differences
    - A doc is flagged if EITHER similarity > threshold
    """

    def __init__(self, num_perm: int = 128, threshold: float = SIMILARITY_THRESHOLD):
        self.num_perm = num_perm
        self.threshold = threshold
        self._text_index = {}  # doc_id -> MinHash
        self._image_index = {}  # doc_id -> perceptual hash
        self._lsh = None
        self._init_lsh()

    def _init_lsh(self):
        """Initialize MinHash LSH index."""
        try:
            from datasketch import MinHashLSH
            self._lsh = MinHashLSH(threshold=self.threshold, num_perm=self.num_perm)
            logger.info(f"Initialized MinHash LSH (threshold={self.threshold}, perm={self.num_perm})")
        except ImportError:
            logger.warning("datasketch not installed, text dedup will use fallback")
            self._lsh = None

    def _create_minhash(self, text: str):
        """Create MinHash from text content."""
        try:
            from datasketch import MinHash
            m = MinHash(num_perm=self.num_perm)
            # Shingle the text into 3-grams for robust similarity
            words = text.lower().split()
            for i in range(max(1, len(words) - 2)):
                shingle = " ".join(words[i:i+3])
                m.update(shingle.encode("utf-8"))
            return m
        except ImportError:
            return None

    def _compute_image_hash(self, image: Image.Image) -> Optional[str]:
        """Compute perceptual hash of an image."""
        try:
            import imagehash
            return str(imagehash.phash(image, hash_size=16))
        except ImportError:
            logger.warning("imagehash not installed, image dedup disabled")
            return None

    def _image_hash_similarity(self, hash1: str, hash2: str) -> float:
        """Compute similarity between two perceptual hashes."""
        try:
            import imagehash
            h1 = imagehash.hex_to_hash(hash1)
            h2 = imagehash.hex_to_hash(hash2)
            max_diff = len(h1.hash.flatten())
            diff = h1 - h2
            return 1.0 - (diff / max_diff) if max_diff > 0 else 1.0
        except Exception:
            return 0.0

    def add_document(self, doc_id: str, text: str, image: Optional[Image.Image] = None) -> DuplicateResult:
        """
        Add a document and check for duplicates.
        
        Returns DuplicateResult indicating whether this doc is a near-duplicate.
        """
        text_sim = 0.0
        image_sim = 0.0
        duplicate_of = None

        # Text-based dedup via MinHash LSH
        minhash = self._create_minhash(text)
        if minhash and self._lsh is not None:
            try:
                candidates = self._lsh.query(minhash)
                for cand_id in candidates:
                    if cand_id in self._text_index:
                        sim = minhash.jaccard(self._text_index[cand_id])
                        if sim > text_sim:
                            text_sim = sim
                            duplicate_of = cand_id
                self._lsh.insert(doc_id, minhash)
                self._text_index[doc_id] = minhash
            except Exception as e:
                logger.warning(f"LSH error for {doc_id}: {e}")

        # Image-based dedup via perceptual hash
        if image is not None:
            img_hash = self._compute_image_hash(image)
            if img_hash:
                for existing_id, existing_hash in self._image_index.items():
                    sim = self._image_hash_similarity(img_hash, existing_hash)
                    if sim > image_sim:
                        image_sim = sim
                        if sim > text_sim:
                            duplicate_of = existing_id
                self._image_index[doc_id] = img_hash

        is_dup = text_sim > self.threshold or image_sim > self.threshold

        result = DuplicateResult(
            doc_id=doc_id, is_duplicate=is_dup, duplicate_of=duplicate_of,
            text_similarity=round(text_sim, 4), image_similarity=round(image_sim, 4),
        )
        if is_dup:
            logger.info(f"Duplicate detected: {doc_id} ≈ {duplicate_of} "
                        f"(text={text_sim:.3f}, image={image_sim:.3f})")
        return result

    def deduplicate_batch(self, documents: list[dict]) -> list[DuplicateResult]:
        """
        Deduplicate a batch of documents.
        
        Each document dict should have: id, text, and optionally image_path.
        """
        results = []
        for doc in documents:
            image = None
            if "image_path" in doc and Path(doc["image_path"]).exists():
                image = Image.open(doc["image_path"])
            result = self.add_document(doc["id"], doc.get("text", ""), image)
            results.append(result)
        
        dups = sum(1 for r in results if r.is_duplicate)
        logger.info(f"Deduplication complete: {dups}/{len(results)} duplicates found")
        return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    dedup = DocumentDeduplicator()
    
    # Test with similar texts
    r1 = dedup.add_document("doc_001", "Rajesh Kumar born on 15/08/1990 Aadhaar number 9234 5678 9012")
    r2 = dedup.add_document("doc_002", "Rajesh Kumar born on 15/08/1990 Aadhaar number 9234 5678 9012")
    r3 = dedup.add_document("doc_003", "Priya Sharma invoice number INV-2024-0001 total amount 50000")
    
    for r in [r1, r2, r3]:
        status = "DUPLICATE" if r.is_duplicate else "unique"
        print(f"  {r.doc_id}: {status} (text_sim={r.text_similarity}, img_sim={r.image_similarity})")
