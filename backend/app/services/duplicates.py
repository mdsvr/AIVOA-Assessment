from difflib import SequenceMatcher

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Complaint

SIMILARITY_THRESHOLD = 0.6
MAX_CANDIDATES = 50  # ponytail: linear scan, fine at demo scale; prefilter by product first


def _signature(product_name: str | None, batch_lot_number: str | None, description: str | None) -> str:
    return " ".join(filter(None, [product_name, batch_lot_number, description])).lower()


def find_duplicates(db: Session, fields: dict) -> list[dict]:
    signature = _signature(
        fields.get("product_name"), fields.get("batch_lot_number"), fields.get("description")
    )
    if not signature.strip():
        return []

    query = select(Complaint).order_by(Complaint.created_at.desc())
    if fields.get("product_name"):
        # Case-insensitive: two documents about the same product can come back from
        # the LLM with different casing ("Amoxicillin Capsules" vs "amoxicillin
        # capsules") -- an exact match would silently drop real duplicates before they
        # ever reach the fuzzy comparison below.
        query = query.where(func.lower(Complaint.product_name) == fields["product_name"].lower())
    candidates = db.execute(query.limit(MAX_CANDIDATES)).scalars().all()

    matches = []
    for c in candidates:
        candidate_sig = _signature(c.product_name, c.batch_lot_number, c.description)
        similarity = SequenceMatcher(None, signature, candidate_sig).ratio()
        if similarity >= SIMILARITY_THRESHOLD:
            matches.append(
                {
                    "complaint_id": c.id,
                    "similarity": round(similarity, 2),
                    "product_name": c.product_name,
                    "customer_name": c.customer_name,
                }
            )
    return sorted(matches, key=lambda m: m["similarity"], reverse=True)
