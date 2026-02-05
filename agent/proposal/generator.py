from typing import Dict

class ProposalGenerator:
    def __init__(self):
        self.email_template = "Subject: Partnership\n\nDear {contact},\n\nWe are a pickleball supplier and would like to partner with {company} in {city}.\n\nBest regards"
        self.whatsapp_template = "Hi {contact}, interested in pickleball equipment for {company} in {city}?"

    async def generate_proposal(self, entity: Dict, template: str = None) -> Dict:
        company = entity.get("name", "Your Company")
        city = entity.get("city", "")
        contact = entity.get("contact_person", "Team")
        email = self.email_template.format(contact=contact, company=company, city=city)
        whatsapp = self.whatsapp_template.format(contact=contact, company=company, city=city)
        return {"email_proposal": email, "whatsapp_message": whatsapp, "template_used": "default"}
