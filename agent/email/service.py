import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class EmailService:
    """Gmail SMTP email service for sending proposals."""
    
    def __init__(self):
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        self.sender_email = os.getenv("GMAIL_EMAIL", "")
        self.sender_password = os.getenv("GMAIL_APP_PASSWORD", "")
        
        # Default proposal template
        self.default_template = """Dear Sir / Madam,

Greetings.

We are pleased to introduce Manh Thang Industrial Service Development Company Limited (Vietnam), a specialized manufacturer and OEM producer of tournament-grade pickleball balls, and propose a potential collaboration for bulk supply and distribution in the Indian market.

Manh Thang Pickleball Factory operates with advanced rotational hot molding technology, strict quality management systems, and international compliance standards. The factory currently supplies to domestic and export markets including the USA and Europe.

✅ Product Highlight – E-WIN (ONE WIN) Pickleball Balls
• Certified compliant with USA Pickleball Association (USAPA) standards
• Designed for international competition and tournaments
• Indoor ball weight: ~26 g
• Outdoor ball weight: ~26.5 g
• Diameter: 74 mm (±5%)
• Hardness: 44–46 HD (balanced control & durability)
• 40 precision-drilled holes
• Manufactured from high-quality PE virgin plastic with performance additives
• Stable in hot and cold climates; does not soften during extended play
• High-visibility green and yellow colors

🏭 Manufacturing Strength
• 5 automatic rotational casting technology production lines
• Current capacity: 25,000–30,000 balls per day
• Expansion plan: up to 50,000 balls per day
• Factory area: over 7,000 m²
• 65 skilled staff members
• Continuous process improvement and strict inspection before packing

📦 Product Portfolio
• S2 Tournament Pickleball
• E-WIN (ONE WIN) Tournament Series
• Vincent Series
• Multi-color Pickleballs
• Mini Pickleballs
• 100% Biodegradable Pickleballs (eco-friendly option)

🤝 Why Partner With Manh Thang
• Consistent tournament-grade quality
• Competitive factory-direct pricing
• OEM / Private label manufacturing available
• Reliable production capacity & delivery schedules
• Suitable for clubs, academies, tournaments, retailers, and e-commerce platforms

We are currently appointing India distributors, state partners, and bulk buyers and would welcome discussions on:
• Distribution / dealership model
• Bulk purchase pricing
• OEM branding
• Sample evaluation

📞 Factory Contact (Vietnam – Head Office)
Manh Thang Industrial Service Development Company Limited
Phone: +84 91 253 16 66
Email: manhthang2666@gmail.com
Website: www.manhthangpickleballfactory.com

For India coordination, please feel free to connect with:
Vijay Pawar
India – Business Development
Mobile / WhatsApp: +91-7975397211
Email: vijaykp.kp@gmail.com

Looking forward to your positive response and the opportunity to build a long-term partnership.

Warm regards,
Vijay Pawar"""

    def is_configured(self) -> bool:
        """Check if email service is properly configured."""
        return bool(self.sender_email and self.sender_password)

    def send_email(
        self,
        to_email: str,
        subject: str = "Pickleball Partnership Opportunity - Manh Thang Factory",
        body: Optional[str] = None,
        recipient_name: Optional[str] = None
    ) -> dict:
        """
        Send email via Gmail SMTP.
        
        Args:
            to_email: Recipient email address
            subject: Email subject line
            body: Email body (uses default template if not provided)
            recipient_name: Name of recipient for personalization
            
        Returns:
            dict with success status and message
        """
        if not self.is_configured():
            return {
                "success": False,
                "error": "Email service not configured. Set GMAIL_EMAIL and GMAIL_APP_PASSWORD in .env"
            }
        
        if not to_email:
            return {
                "success": False,
                "error": "Recipient email address is required"
            }
        
        # Use default template if no body provided
        email_body = body or self.default_template
        
        # Personalize if recipient name provided
        if recipient_name:
            email_body = email_body.replace("Dear Sir / Madam", f"Dear {recipient_name}")
        
        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"Vijay Pawar <{self.sender_email}>"
            msg["To"] = to_email
            
            # Plain text version
            text_part = MIMEText(email_body, "plain", "utf-8")
            msg.attach(text_part)
            
            # HTML version (convert newlines to <br>)
            html_body = email_body.replace("\n", "<br>")
            html_content = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 700px; margin: 0 auto; padding: 20px;">
                    {html_body}
                </div>
            </body>
            </html>
            """
            html_part = MIMEText(html_content, "html", "utf-8")
            msg.attach(html_part)
            
            # Send via SMTP
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
            
            return {
                "success": True,
                "message": f"Email sent successfully to {to_email}",
                "to": to_email,
                "subject": subject
            }
            
        except smtplib.SMTPAuthenticationError:
            return {
                "success": False,
                "error": "Gmail authentication failed. Check your email and app password."
            }
        except smtplib.SMTPException as e:
            return {
                "success": False,
                "error": f"SMTP error: {str(e)}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to send email: {str(e)}"
            }

    def send_bulk_emails(self, recipients: list, subject: str = None) -> dict:
        """
        Send emails to multiple recipients.
        
        Args:
            recipients: List of dicts with 'email' and optional 'name'
            subject: Email subject line
            
        Returns:
            dict with success/failure counts and details
        """
        results = {
            "total": len(recipients),
            "sent": 0,
            "failed": 0,
            "details": []
        }
        
        for recipient in recipients:
            email = recipient.get("email")
            name = recipient.get("name")
            
            if not email:
                results["failed"] += 1
                results["details"].append({"email": None, "success": False, "error": "No email"})
                continue
            
            result = self.send_email(
                to_email=email,
                subject=subject or "Pickleball Partnership Opportunity - Manh Thang Factory",
                recipient_name=name
            )
            
            if result.get("success"):
                results["sent"] += 1
            else:
                results["failed"] += 1
            
            results["details"].append({
                "email": email,
                "success": result.get("success"),
                "error": result.get("error")
            })
        
        return results
