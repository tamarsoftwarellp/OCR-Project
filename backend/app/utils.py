from datetime import datetime, timezone
from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def to_object_id(id_str: str) -> ObjectId:
    """Safely convert a string to a Mongo ObjectId, or raise a clean 400."""
    try:
        return ObjectId(id_str)
    except (InvalidId, TypeError):
        raise HTTPException(status_code=400, detail=f"Invalid id: {id_str}")


def serialize_doc(doc: dict) -> dict:
    """Convert a Mongo document's _id (ObjectId) to a plain string 'id' field
    so it can be safely returned as JSON."""
    if not doc:
        return doc
    doc = dict(doc)
    if "_id" in doc:
        doc["id"] = str(doc.pop("_id"))
    return doc
