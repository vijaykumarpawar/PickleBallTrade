from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List

from agent.data.database import DatabaseManager
from agent.search.discovery import SearchEngine
from agent.classify.classifier import EntityClassifier
from agent.proposal.generator import ProposalGenerator
from agent.email.service import EmailService

app = FastAPI(title="Pickleball Agent API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
db = DatabaseManager()
search_engine = SearchEngine()
classifier = EntityClassifier()
proposal_gen = ProposalGenerator()
email_service = EmailService()


class DiscoverRequest(BaseModel):
    city: str
    limit: int = 10


class ProposalRequest(BaseModel):
    entity_id: int


class EmailRequest(BaseModel):
    to_email: str
    subject: Optional[str] = "Pickleball Partnership Opportunity - Manh Thang Factory"
    recipient_name: Optional[str] = None
    custom_body: Optional[str] = None


class BulkEmailRequest(BaseModel):
    recipients: List[dict]  # List of {"email": "...", "name": "..."}
    subject: Optional[str] = "Pickleball Partnership Opportunity - Manh Thang Factory"


@app.get("/")
async def root():
    return {"message": "Pickleball Agent API", "status": "running"}


@app.get("/stats")
async def get_stats():
    return db.get_stats()


@app.get("/entities")
async def list_entities(city: Optional[str] = Query(None), entity_type: Optional[str] = Query(None, alias="type")):
    entities = db.get_all_entities()
    if city:
        entities = [e for e in entities if e.get("city") == city]
    if entity_type:
        entities = [e for e in entities if e.get("type") == entity_type]
    return {"entities": entities, "count": len(entities)}


@app.post("/discover")
async def discover_entities(request: DiscoverRequest):
    results = await search_engine.discover_businesses(request.city, request.limit)
    stored = 0
    for result in results:
        classified = classifier.classify(result)
        db.store_entity(classified)
        stored += 1
    return {"city": request.city, "discovered": len(results), "stored": stored}


@app.post("/generate-proposal")
async def generate_proposal(request: ProposalRequest):
    entities = db.get_all_entities()
    entity = next((e for e in entities if e.get("id") == request.entity_id), None)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    proposal = await proposal_gen.generate_proposal(entity)
    return proposal


@app.get("/export/csv")
async def export_csv():
    path = db.export_entities()
    return FileResponse(path=path, filename="leads.csv")


@app.get("/cities")
async def list_cities():
    return {"cities": search_engine.get_all_cities()}


# ============ EMAIL ENDPOINTS ============

@app.get("/email/status")
async def email_status():
    """Check if email service is configured."""
    return {
        "configured": email_service.is_configured(),
        "sender": email_service.sender_email if email_service.is_configured() else None
    }


@app.post("/email/send")
async def send_email(request: EmailRequest):
    """Send a single email with the proposal."""
    result = email_service.send_email(
        to_email=request.to_email,
        subject=request.subject,
        body=request.custom_body,
        recipient_name=request.recipient_name
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error"))
    
    return result


@app.post("/email/send-bulk")
async def send_bulk_emails(request: BulkEmailRequest):
    """Send emails to multiple recipients."""
    result = email_service.send_bulk_emails(
        recipients=request.recipients,
        subject=request.subject
    )
    return result


@app.post("/email/send-to-entity/{entity_id}")
async def send_email_to_entity(entity_id: int, subject: Optional[str] = None):
    """Send email to a specific entity by ID."""
    entities = db.get_all_entities()
    entity = next((e for e in entities if e.get("id") == entity_id), None)
    
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    
    if not entity.get("email"):
        raise HTTPException(status_code=400, detail="Entity has no email address")
    
    result = email_service.send_email(
        to_email=entity["email"],
        subject=subject or "Pickleball Partnership Opportunity - Manh Thang Factory",
        recipient_name=entity.get("name")
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error"))
    
    return result


def create_app():
    return app


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("agent.api.server:app", host="0.0.0.0", port=8000, reload=True)
