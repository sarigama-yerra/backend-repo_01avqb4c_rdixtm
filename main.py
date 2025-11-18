import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from bson.objectid import ObjectId

from database import db, create_document, get_documents
from schemas import User, TherapistAvailability, BookingRequest, Message, JournalEntry

app = FastAPI(title="Psylio-style Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def to_str_id(doc):
    if not doc:
        return doc
    d = dict(doc)
    if d.get("_id"):
        d["id"] = str(d.pop("_id"))
    # convert nested ObjectIds if any
    for k, v in list(d.items()):
        if isinstance(v, ObjectId):
            d[k] = str(v)
        if isinstance(v, list):
            d[k] = [str(x) if isinstance(x, ObjectId) else x for x in v]
    return d


@app.get("/")
def read_root():
    return {"message": "Psylio-style API running"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = db.name if hasattr(db, 'name') else "Unknown"
            response["connection_status"] = "Connected"
            try:
                response["collections"] = db.list_collection_names()
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️ Connected but Error: {str(e)[:80]}"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:80]}"
    return response


# ---------- Schemas endpoint (for viewer/tools) ----------
class SchemaInfo(BaseModel):
    name: str
    schema: dict


@app.get("/schema", response_model=List[SchemaInfo])
def get_schema():
    models = [
        ("user", User.model_json_schema()),
        ("therapistavailability", TherapistAvailability.model_json_schema()),
        ("bookingrequest", BookingRequest.model_json_schema()),
        ("message", Message.model_json_schema()),
        ("journalentry", JournalEntry.model_json_schema()),
    ]
    return [SchemaInfo(name=name, schema=schema) for name, schema in models]


# ---------- Therapists (directory) ----------
@app.get("/api/therapists")
def list_therapists(
    search: Optional[str] = None,
    specialty: Optional[str] = None,
    language: Optional[str] = None,
    virtual: Optional[bool] = None,
    in_person: Optional[bool] = None,
):
    query = {"role": "therapist"}
    if search:
        # simple regex OR across name and bio
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"bio": {"$regex": search, "$options": "i"}},
            {"specialties": {"$elemMatch": {"$regex": search, "$options": "i"}}},
        ]
    if specialty:
        query["specialties"] = {"$elemMatch": {"$regex": specialty, "$options": "i"}}
    if language:
        query["languages"] = {"$elemMatch": {"$regex": language, "$options": "i"}}
    if virtual is not None:
        query["virtual"] = virtual
    if in_person is not None:
        query["in_person"] = in_person

    docs = get_documents("user", query, limit=None)
    return [to_str_id(d) for d in docs]


@app.post("/api/therapists")
def create_therapist(therapist: User):
    if therapist.role != "therapist":
        raise HTTPException(status_code=400, detail="role must be 'therapist'")
    inserted_id = create_document("user", therapist)
    return {"id": inserted_id}


@app.get("/api/therapists/{therapist_id}")
def get_therapist(therapist_id: str):
    try:
        doc = db["user"].find_one({"_id": ObjectId(therapist_id)})
        if not doc:
            raise HTTPException(status_code=404, detail="Not found")
        return to_str_id(doc)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")


# ---------- Booking Requests ----------
@app.post("/api/booking-requests")
def create_booking(req: BookingRequest):
    inserted_id = create_document("bookingrequest", req)
    return {"id": inserted_id}


@app.get("/api/booking-requests")
def list_bookings(
    therapist_id: Optional[str] = None,
    client_email: Optional[EmailStr] = None,
):
    query = {}
    if therapist_id:
        query["therapist_id"] = therapist_id
    if client_email:
        query["client_email"] = str(client_email)
    docs = get_documents("bookingrequest", query)
    return [to_str_id(d) for d in docs]


# ---------- Messages ----------
@app.post("/api/messages")
def send_message(msg: Message):
    inserted_id = create_document("message", msg)
    return {"id": inserted_id}


@app.get("/api/messages")
def list_messages(
    therapist_id: Optional[str] = None,
    client_email: Optional[EmailStr] = None,
    thread_id: Optional[str] = None,
):
    query = {}
    if therapist_id:
        query["therapist_id"] = therapist_id
    if client_email:
        query["client_email"] = str(client_email)
    if thread_id:
        query["thread_id"] = thread_id
    docs = db["message"].find(query).sort("created_at", 1)
    return [to_str_id(d) for d in docs]


# ---------- Journal ----------
@app.post("/api/journal")
def create_journal(entry: JournalEntry):
    inserted_id = create_document("journalentry", entry)
    return {"id": inserted_id}


@app.get("/api/journal")
def list_journal(client_email: EmailStr):
    docs = db["journalentry"].find({"client_email": str(client_email)}).sort("created_at", -1)
    return [to_str_id(d) for d in docs]


# ---------- Seed sample data ----------
@app.post("/seed")
def seed():
    sample = [
        User(
            role="therapist",
            name="Dr. Maya Patel",
            email="maya.patel@example.com",
            bio="Trauma-informed therapist focusing on mindfulness and CBT.",
            specialties=["Trauma", "CBT", "Mindfulness"],
            modalities=["CBT", "ACT"],
            languages=["English", "Hindi"],
            location="Toronto, ON",
            virtual=True,
            in_person=True,
            fee_min=120,
            fee_max=180,
            years_experience=8,
        ),
        User(
            role="therapist",
            name="Jean-Luc Tremblay",
            email="jeanluc.t@example.com",
            bio="Francophone therapist specializing in couples and family systems.",
            specialties=["Couples", "Family", "Anxiety"],
            modalities=["EFT", "SFT"],
            languages=["French", "English"],
            location="Montreal, QC",
            virtual=True,
            in_person=False,
            fee_min=110,
            fee_max=160,
            years_experience=12,
        ),
        User(
            role="therapist",
            name="Sofia Ramirez",
            email="sofia.r@example.com",
            bio="Bilingual therapist helping with stress, burnout, and life transitions.",
            specialties=["Stress", "Burnout", "Transitions"],
            modalities=["CBT", "Narrative"],
            languages=["Spanish", "English"],
            location="Vancouver, BC",
            virtual=True,
            in_person=True,
            fee_min=100,
            fee_max=150,
            years_experience=6,
        ),
    ]
    inserted = []
    for s in sample:
        # idempotent-ish: avoid duplicates by email
        existing = db["user"].find_one({"email": s.email})
        if not existing:
            inserted.append(create_document("user", s))
    return {"inserted": inserted, "count": len(inserted)}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
