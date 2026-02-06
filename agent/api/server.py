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
from agent.whatsapp.service import WhatsAppService, set_permission_granted

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
whatsapp_service = WhatsAppService()


class DiscoverRequest(BaseModel):
    city: str
    limit: int = 10
    strategy: Optional[str] = None  # Optional: specific strategy to use
    deep_search: bool = False  # Use deep search (slower, more comprehensive)


class ProposalRequest(BaseModel):
    entity_id: int


class EmailRequest(BaseModel):
    to_email: str
    subject: Optional[str] = "Pickleball Partnership Opportunity - Manh Thang Factory"
    recipient_name: Optional[str] = None
    custom_body: Optional[str] = None
    include_attachments: bool = True
    attachment_files: Optional[List[str]] = None
    entity_id: Optional[int] = None  # For tracking sent status


class BulkEmailRequest(BaseModel):
    recipients: List[dict]  # List of {"email": "...", "name": "...", "entity_id": ...}
    subject: Optional[str] = "Pickleball Partnership Opportunity - Manh Thang Factory"
    include_attachments: bool = True


class WhatsAppRequest(BaseModel):
    phone: str
    message: Optional[str] = None
    entity_id: Optional[int] = None  # For tracking sent status
    direct_send: bool = True  # If True, auto-send; if False, just open chat
    include_image: bool = True  # Include product image from uploads folder


class ScrapeRequest(BaseModel):
    url: str
    follow_contact_pages: bool = True


class EnrichRequest(BaseModel):
    entity_ids: Optional[List[int]] = None  # If None, enrich all leads
    limit: Optional[int] = 50  # Max leads to enrich at once


class AddLeadRequest(BaseModel):
    name: str
    website: str
    city: Optional[str] = None
    type: Optional[str] = "Distributor"
    scrape_contacts: bool = True  # Auto-scrape website for contact info


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
    """
    Discover businesses using comprehensive multi-source search.
    
    Strategies available:
    - directories: IndiaMART, TradeIndia, JustDial, Sulekha
    - manufacturers: Brand distributor lists
    - tradeshows: Expo & fair exhibitor lists
    - linkedin: LinkedIn company/profile search
    - google: Advanced Google search queries
    - yellowpages: Yellow pages & chamber of commerce
    - marketplaces: Amazon/Flipkart seller lookup
    - sports_shops: Related sports shops & academies
    - curated: Known pickleball companies from curated list
    
    Set deep_search=True for comprehensive search using ALL strategies.
    """
    if request.deep_search:
        results = await search_engine.deep_search(request.city, request.limit)
    elif request.strategy:
        results = await search_engine.discover_by_strategy(
            request.city, request.strategy, request.limit
        )
    else:
        results = await search_engine.discover_businesses(request.city, request.limit)
    
    stored = 0
    for result in results:
        classified = classifier.classify(result)
        db.store_entity(classified)
        stored += 1
    
    return {
        "city": request.city,
        "discovered": len(results),
        "stored": stored,
        "strategy": request.strategy or ("deep_search" if request.deep_search else "default"),
        "sources": list(set(r.get("source", "web_search") for r in results))
    }


@app.get("/discover/strategies")
async def list_strategies():
    """List available discovery strategies."""
    return {
        "strategies": [
            {
                "id": "directories",
                "name": "Industry Directories",
                "description": "Search IndiaMART, TradeIndia, JustDial, Sulekha, ExportersIndia",
                "priority": "High - Best for finding verified business listings"
            },
            {
                "id": "manufacturers",
                "name": "Manufacturer Distributor Lists",
                "description": "Find authorized distributors from brand websites",
                "priority": "High - Authoritative, clean contact data"
            },
            {
                "id": "tradeshows",
                "name": "Trade Shows & Expos",
                "description": "Search exhibitor lists from sports trade shows",
                "priority": "Medium - Active industry players"
            },
            {
                "id": "linkedin",
                "name": "LinkedIn Search",
                "description": "Find decision-makers and company profiles",
                "priority": "Medium - Good for B2B contacts"
            },
            {
                "id": "google",
                "name": "Google Advanced Search",
                "description": "Use advanced search operators for targeted results",
                "priority": "Medium - Finds smaller businesses"
            },
            {
                "id": "yellowpages",
                "name": "Yellow Pages & Chambers",
                "description": "Search Yellow Pages, MSME directories, chambers of commerce",
                "priority": "Medium - Established local businesses"
            },
            {
                "id": "marketplaces",
                "name": "Marketplace Sellers",
                "description": "Find Amazon/Flipkart/Decathlon sellers",
                "priority": "Low - May be retailers, not distributors"
            },
            {
                "id": "sports_shops",
                "name": "Related Sports Shops",
                "description": "Tennis/badminton shops, sports academies, clubs",
                "priority": "Medium - Potential pickleball distributors"
            },
            {
                "id": "curated",
                "name": "🌟 Curated Companies List",
                "description": "Known pickleball importers, distributors, JOOLA dealers etc.",
                "priority": "Highest - Verified companies with direct website scraping"
            }
        ],
        "note": "Use deep_search=True in /discover to search ALL strategies at once"
    }


# ============ CURATED COMPANIES & SCRAPING ============

@app.get("/curated")
async def get_curated_companies():
    """Get the curated list of known pickleball companies in India."""
    companies = search_engine.get_curated_companies()
    return {
        "companies": companies,
        "count": len(companies),
        "categories": {
            "joola_dealers": [c for c in companies if "JOOLA" in c.get("role", "")],
            "manufacturers": [c for c in companies if "Manufacturer" in c.get("role", "")],
            "distributors": [c for c in companies if "Distributor" in c.get("role", "")],
            "retailers": [c for c in companies if "Retailer" in c.get("role", "")]
        }
    }


@app.post("/discover/curated")
async def discover_from_curated(city: Optional[str] = None):
    """
    Discover leads from the curated list of known pickleball companies.
    Automatically scrapes websites to extract contact details.
    
    This is the most reliable source as it contains verified companies.
    """
    results = await search_engine.discover_from_curated_list(city)
    
    stored = 0
    for result in results:
        classified = classifier.classify(result)
        db.store_entity(classified)
        stored += 1
    
    with_contacts = sum(1 for r in results if r.get("email") or r.get("phone"))
    
    return {
        "source": "curated_list",
        "city_filter": city,
        "discovered": len(results),
        "with_contacts": with_contacts,
        "stored": stored,
        "companies": [{"name": r["name"], "email": r.get("email"), "phone": r.get("phone")} for r in results]
    }


@app.post("/scrape")
async def scrape_website(request: ScrapeRequest):
    """
    Scrape a website URL to extract contact information.
    
    Extracts:
    - Email addresses (including mailto: links)
    - Phone numbers (Indian format)
    - WhatsApp numbers
    - Physical address
    - Social media links
    
    Set follow_contact_pages=True to also scrape /contact, /about pages.
    """
    result = await search_engine.scrape_website_contacts(
        request.url, 
        follow_contact_pages=request.follow_contact_pages
    )
    return result


@app.post("/enrich")
async def enrich_leads(request: EnrichRequest):
    """
    Enrich existing leads by scraping their website URLs for contact info.
    
    This will visit each lead's website and extract:
    - Email addresses
    - Phone numbers
    - WhatsApp numbers
    - Address
    
    If entity_ids is provided, only those leads are enriched.
    Otherwise, enriches all leads with website but missing contact info.
    """
    entities = db.get_all_entities()
    
    # Filter to leads that need enrichment
    if request.entity_ids:
        to_enrich = [e for e in entities if e["id"] in request.entity_ids]
    else:
        # Get leads with website but missing email/phone
        to_enrich = [
            e for e in entities 
            if e.get("website") and (not e.get("email") or not e.get("phone"))
        ]
    
    # Limit
    to_enrich = to_enrich[:request.limit]
    
    if not to_enrich:
        return {
            "success": True,
            "message": "No leads need enrichment",
            "enriched": 0
        }
    
    # Enrich leads
    enriched_leads = await search_engine.enrich_leads_batch(to_enrich)
    
    # Update database with enriched info
    updated = 0
    for lead in enriched_leads:
        if lead.get("enriched"):
            db.update_entity(lead["id"], {
                "email": lead.get("email"),
                "phone": lead.get("phone"),
                "whatsapp": lead.get("whatsapp"),
                "address": lead.get("address")
            })
            updated += 1
    
    return {
        "success": True,
        "processed": len(to_enrich),
        "enriched": updated,
        "leads": [
            {
                "id": l["id"],
                "name": l["name"],
                "email": l.get("email"),
                "phone": l.get("phone"),
                "enriched": l.get("enriched", False)
            } 
            for l in enriched_leads
        ]
    }


@app.post("/enrich/{entity_id}")
async def enrich_single_lead(entity_id: int):
    """Enrich a single lead by scraping its website."""
    entity = db.get_entity_by_id(entity_id)
    
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    
    if not entity.get("website"):
        raise HTTPException(status_code=400, detail="Entity has no website URL")
    
    # Scrape website
    enriched = await search_engine.enrich_lead(dict(entity))
    
    if enriched.get("enriched"):
        # Update database
        db.update_entity(entity_id, {
            "email": enriched.get("email"),
            "phone": enriched.get("phone"),
            "whatsapp": enriched.get("whatsapp"),
            "address": enriched.get("address")
        })
    
    return {
        "success": True,
        "entity_id": entity_id,
        "name": entity["name"],
        "website": entity["website"],
        "email": enriched.get("email"),
        "phone": enriched.get("phone"),
        "whatsapp": enriched.get("whatsapp"),
        "address": enriched.get("address"),
        "pages_scraped": enriched.get("pages_scraped", [])
    }


@app.post("/leads/add")
async def add_lead_manually(request: AddLeadRequest):
    """
    Add a lead manually with automatic website scraping.
    
    Use this to add known companies from the curated list or other sources.
    If scrape_contacts=True, will automatically visit the website to get contact info.
    """
    lead = {
        "name": request.name,
        "website": request.website,
        "city": request.city,
        "type": request.type,
        "source": "manual_add"
    }
    
    # Optionally scrape website
    if request.scrape_contacts:
        scraped = await search_engine.scrape_website_contacts(request.website)
        lead["email"] = scraped.get("email")
        lead["phone"] = scraped.get("phone")
        lead["whatsapp"] = scraped.get("whatsapp")
        lead["address"] = scraped.get("address")
    
    # Classify and store
    classified = classifier.classify(lead)
    db.store_entity(classified)
    
    return {
        "success": True,
        "lead": classified,
        "scraped": request.scrape_contacts
    }


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


# ============ TRACKING ENDPOINTS ============

@app.post("/entities/{entity_id}/mark-email-sent")
async def mark_email_sent(entity_id: int):
    """Mark an entity as having received an email."""
    entity = db.get_entity_by_id(entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    
    db.mark_email_sent(entity_id)
    return {"success": True, "entity_id": entity_id, "email_sent": True}


@app.post("/entities/{entity_id}/mark-whatsapp-sent")
async def mark_whatsapp_sent(entity_id: int):
    """Mark an entity as having received a WhatsApp message."""
    entity = db.get_entity_by_id(entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    
    db.mark_whatsapp_sent(entity_id)
    return {"success": True, "entity_id": entity_id, "whatsapp_sent": True}


@app.post("/entities/{entity_id}/reset-sent-status")
async def reset_sent_status(entity_id: int, channel: Optional[str] = None):
    """Reset sent status for an entity. channel can be 'email', 'whatsapp', or None for both."""
    entity = db.get_entity_by_id(entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    
    db.reset_sent_status(entity_id, channel)
    return {"success": True, "entity_id": entity_id, "channel": channel or "all", "reset": True}


# ============ EMAIL ENDPOINTS ============

@app.get("/email/status")
async def email_status():
    """Check if email service is configured and list available attachments."""
    attachments = email_service.get_available_attachments()
    return {
        "configured": email_service.is_configured(),
        "sender": email_service.sender_email if email_service.is_configured() else None,
        "attachments": attachments,
        "default_attachments": email_service.DEFAULT_ATTACHMENTS
    }


@app.get("/email/attachments")
async def list_attachments():
    """List available attachment files from uploads folder."""
    return {
        "attachments": email_service.get_available_attachments(),
        "default_attachments": email_service.DEFAULT_ATTACHMENTS
    }


@app.post("/email/send")
async def send_email(request: EmailRequest):
    """Send a single email with the proposal and attachments."""
    result = email_service.send_email(
        to_email=request.to_email,
        subject=request.subject,
        body=request.custom_body,
        recipient_name=request.recipient_name,
        include_attachments=request.include_attachments,
        attachment_files=request.attachment_files
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error"))
    
    # Mark entity as email sent if entity_id provided
    if request.entity_id:
        db.mark_email_sent(request.entity_id)
        result["entity_marked"] = True
    
    return result


@app.post("/email/send-bulk")
async def send_bulk_emails(request: BulkEmailRequest):
    """Send emails to multiple recipients with attachments."""
    result = email_service.send_bulk_emails(
        recipients=request.recipients,
        subject=request.subject,
        include_attachments=request.include_attachments
    )
    
    # Mark entities as sent for successful emails
    for detail in result.get("details", []):
        if detail.get("success") and detail.get("entity_id"):
            db.mark_email_sent(detail["entity_id"])
    
    return result


@app.post("/email/send-to-entity/{entity_id}")
async def send_email_to_entity(
    entity_id: int,
    subject: Optional[str] = None,
    include_attachments: bool = True
):
    """Send email to a specific entity by ID with attachments."""
    entity = db.get_entity_by_id(entity_id)
    
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    
    if not entity.get("email"):
        raise HTTPException(status_code=400, detail="Entity has no email address")
    
    result = email_service.send_email(
        to_email=entity["email"],
        subject=subject or "Pickleball Partnership Opportunity - Manh Thang Factory",
        recipient_name=entity.get("name"),
        include_attachments=include_attachments
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error"))
    
    # Mark entity as email sent
    db.mark_email_sent(entity_id)
    result["entity_marked"] = True
    
    return result


# ============ WHATSAPP ENDPOINTS ============

@app.get("/whatsapp/status")
async def whatsapp_status():
    """Check WhatsApp automation permission status and available attachments."""
    perm_status = whatsapp_service.check_permission()
    perm_status["image_available"] = whatsapp_service.get_image_path() is not None
    perm_status["pdf_available"] = whatsapp_service.get_pdf_path() is not None
    perm_status["attachments"] = whatsapp_service.get_available_attachments()
    return perm_status


@app.post("/whatsapp/grant-permission")
async def grant_whatsapp_permission():
    """Confirm that user has granted accessibility permission."""
    set_permission_granted(True)
    return {"success": True, "message": "Permission status updated. Automation is now enabled."}


@app.post("/whatsapp/send")
async def send_whatsapp(request: WhatsAppRequest):
    """
    Send WhatsApp message with optional image attachment.
    
    - direct_send=True: Automatically sends message (requires Mac accessibility permission)
    - include_image=True: Attaches product image from uploads folder
    """
    if request.direct_send:
        if request.include_image:
            # Send with image
            result = whatsapp_service.send_with_image(request.phone, request.message)
        else:
            # Send text only
            result = whatsapp_service.send_direct(request.phone, request.message)
    else:
        result = whatsapp_service.open_chat(request.phone, request.message)
    
    # If permission is needed, return instructions
    if result.get("needs_permission"):
        return {
            "success": False,
            "needs_permission": True,
            "error": result.get("error"),
            "instructions": result.get("instructions"),
            "action_required": "Grant accessibility permission and call /whatsapp/grant-permission endpoint"
        }
    
    # Mark entity as whatsapp sent if successful and entity_id provided
    if result.get("success") and request.entity_id:
        db.mark_whatsapp_sent(request.entity_id)
        result["entity_marked"] = True
    
    return result


@app.post("/whatsapp/send-to-entity/{entity_id}")
async def send_whatsapp_to_entity(
    entity_id: int,
    message: Optional[str] = None,
    direct_send: bool = True,
    include_image: bool = True
):
    """Send WhatsApp message with image to a specific entity by ID."""
    entity = db.get_entity_by_id(entity_id)
    
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    
    # Use phone or whatsapp field
    phone = entity.get("phone") or entity.get("whatsapp")
    if not phone:
        raise HTTPException(status_code=400, detail="Entity has no phone number")
    
    if direct_send:
        if include_image:
            result = whatsapp_service.send_with_image(phone, message)
        else:
            result = whatsapp_service.send_direct(phone, message)
    else:
        result = whatsapp_service.open_chat(phone, message)
    
    # If permission is needed, return instructions
    if result.get("needs_permission"):
        return {
            "success": False,
            "needs_permission": True,
            "error": result.get("error"),
            "instructions": result.get("instructions"),
            "entity_phone": phone,
            "action_required": "Grant accessibility permission and call /whatsapp/grant-permission endpoint"
        }
    
    # Mark entity as whatsapp sent if successful
    if result.get("success"):
        db.mark_whatsapp_sent(entity_id)
        result["entity_marked"] = True
    
    return result


@app.get("/whatsapp/url")
async def get_whatsapp_url(phone: str, message: Optional[str] = None):
    """Generate WhatsApp URL for manual opening."""
    return {
        "url": whatsapp_service.get_url(phone, message),
        "phone": phone
    }


@app.get("/whatsapp/attachments")
async def get_whatsapp_attachments():
    """List available WhatsApp attachments from uploads folder."""
    return {
        "attachments": whatsapp_service.get_available_attachments(),
        "image_path": whatsapp_service.get_image_path(),
        "pdf_path": whatsapp_service.get_pdf_path()
    }




# AUTO-SEND ENDPOINT

class AutoSendRequest(BaseModel):
    skip_already_sent: bool = True
    limit: Optional[int] = None
    delay_seconds: int = 2
    include_attachments: bool = True

@app.post("/email/send-all")
async def send_all(r: AutoSendRequest = None):
    import time
    if r is None: r = AutoSendRequest()
    all_e = db.get_all_entities()
    with_email = [e for e in all_e if e.get("email")]
    to_send = [e for e in with_email if not e.get("email_sent")] if r.skip_already_sent else with_email
    if r.limit: to_send = to_send[:r.limit]
    if not to_send: return {"sent": 0, "message": "No pending"}
    res = {"sent": 0, "failed": 0, "details": []}
    for i, l in enumerate(to_send):
        if i > 0: time.sleep(r.delay_seconds)
        try:
            x = email_service.send_email(to_email=l["email"], recipient_name=l.get("name"), include_attachments=r.include_attachments)
            if x.get("success"):
                res["sent"] += 1
                db.mark_email_sent(l["id"])
                res["details"].append({"id": l["id"], "email": l["email"], "ok": True})
            else:
                res["failed"] += 1
                res["details"].append({"id": l["id"], "email": l["email"], "ok": False, "err": x.get("error")})
        except Exception as ex:
            res["failed"] += 1
            res["details"].append({"id": l["id"], "email": l["email"], "ok": False, "err": str(ex)})
    return res

@app.get("/email/pending")
async def pending():
    a = db.get_all_entities()
    w = [e for e in a if e.get("email")]
    p = [e for e in w if not e.get("email_sent")]
    return {"total": len(a), "with_email": len(w), "pending": len(p), "leads": [{"id": e["id"], "name": e.get("name"), "email": e.get("email")} for e in p]}

def create_app():
    return app


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("agent.api.server:app", host="0.0.0.0", port=8000, reload=True)
