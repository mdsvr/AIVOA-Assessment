from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import Base, Complaint
from app.services.duplicates import find_duplicates


def _make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_detects_near_identical_complaint():
    db = _make_session()
    db.add(
        Complaint(
            product_name="Amoxicillin 500mg",
            batch_lot_number="B123",
            description="Tablets arrived discolored and brittle.",
        )
    )
    db.commit()

    matches = find_duplicates(
        db,
        {
            "product_name": "Amoxicillin 500mg",
            "batch_lot_number": "B123",
            "description": "Tablets arrived discolored and brittle.",
        },
    )
    assert len(matches) == 1


def test_detects_duplicate_despite_different_product_name_casing():
    db = _make_session()
    db.add(
        Complaint(
            product_name="Amoxicillin 500mg",
            batch_lot_number="B123",
            description="Tablets arrived discolored and brittle.",
        )
    )
    db.commit()

    matches = find_duplicates(
        db,
        {
            "product_name": "amoxicillin 500MG",
            "batch_lot_number": "B123",
            "description": "Tablets arrived discolored and brittle.",
        },
    )
    assert len(matches) == 1


def test_does_not_flag_unrelated_complaint_with_same_product():
    db = _make_session()
    db.add(
        Complaint(
            product_name="Amoxicillin 500mg",
            batch_lot_number="B123",
            description="Tablets arrived discolored and brittle.",
        )
    )
    db.commit()

    matches = find_duplicates(
        db,
        {
            "product_name": "Amoxicillin 500mg",
            "batch_lot_number": "Z999",
            "description": "Bottle cap was loose upon delivery, no product defect.",
        },
    )
    assert matches == []
