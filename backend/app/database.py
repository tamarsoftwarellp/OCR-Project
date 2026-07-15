"""
MongoDB connection.

We use Motor (the official async MongoDB driver) because FastAPI is async
and we don't want to block the event loop on DB calls.

Why MongoDB and not Postgres here?
- OCR engine output has DYNAMIC keys (all_extracted_entities is a flat dict
  whose keys differ per document / per run). Forcing this into rigid SQL
  columns means constant migrations. Mongo stores it as-is, no schema fights.
"""
from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings

client: AsyncIOMotorClient = AsyncIOMotorClient(settings.MONGO_URI)
database = client[settings.MONGO_DB_NAME]

# Collections
claims_collection = database["claims"]
documents_collection = database["documents"]  # one row per OCR-extracted sub-document
users_collection = database["users"]  # admin / reviewer login accounts


async def ensure_indexes() -> None:
    """Called once on app startup (see app.main).

    The unique index on (claim_id, source_file_name) is what actually
    guarantees a second invoice/prescription/lab report never overwrites the
    first one - document_type alone is NOT unique per claim.
    partialFilterExpression keeps it from choking on the legacy fallback
    documents that have no source_file_name at all.
    """
    await documents_collection.create_index(
        [("claim_id", 1), ("source_file_name", 1)],
        unique=True,
        partialFilterExpression={"source_file_name": {"$type": "string"}},
        name="uniq_claim_source_file",
    )
    await documents_collection.create_index(
        [("claim_id", 1), ("document_type", 1), ("sequence", 1)],
        name="claim_type_sequence",
    )
    await claims_collection.create_index("created_at", name="claims_created_at")
    await claims_collection.create_index("status", name="claims_status")
    await users_collection.create_index(
        "email", unique=True, name="uniq_user_email"
    )
