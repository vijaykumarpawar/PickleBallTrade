import smtplib
import os
import mimetypes
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.application import MIMEApplication
from email import encoders
from typing import Optional, List
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Base directory for uploads
BASE_DIR = Path(__file__).parent.parent.parent
UPLOADS_DIR = BASE_DIR / "uploads"

# Google Drive Link for catalog/brochure
CATALOG_LINK = "https://drive.google.com/file/d/1h8w2aM2SvxvX7R40M51rAZznkljrmwHl/view?usp=sharing"

# Exact email template as provided
EMAIL_TEMPLATE = f"""Dear Sir / Madam,

Greetings.

We are pleased to introduce Manh Thang Industrial Service Development Company Limited (Vietnam), a specialized manufacturer and OEM producer of tournament-grade pickleball balls, and propose a potential collaboration for bulk supply and distribution in the Indian market.

Manh Thang Pickleball Factory operates with advanced rotational hot molding technology, strict quality management systems, and international compliance standards. The factory currently supplies to domestic and export markets including the USA and Europe.

📎 View Our Product Catalog & Factory Details: {CATALOG_LINK}

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


class EmailService:
    """Gmail SMTP email service for sending proposals with attachments."""
    
    # Default attachments from uploads folder
    DEFAULT_ATTACHMENTS = [
        "WhatsApp Image 2025-09-19 at 08.58.41.jpeg"
    ]
    
    def __init__(self):
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        self.sender_email = os.getenv("GMAIL_EMAIL", "")
        self.sender_password = os.getenv("GMAIL_APP_PASSWORD", "")
        self.uploads_dir = UPLOADS_DIR
        self.default_template = EMAIL_TEMPLATE

    def is_configured(self) -> bool:
        """Check if email service is properly configured."""
        return bool(self.sender_email and self.sender_password)

    def get_available_attachments(self) -> List[dict]:
        """Get list of available attachment files from uploads folder."""
        attachments = []
        if self.uploads_dir.exists():
            for file_path in self.uploads_dir.iterdir():
                if file_path.is_file() and not file_path.name.startswith('.'):
                    size_mb = file_path.stat().st_size / (1024 * 1024)
                    attachments.append({
                        "name": file_path.name,
                        "path": str(file_path),
                        "size_mb": round(size_mb, 2),
                        "too_large": size_mb > 20  # Gmail limit warning
                    })
        return attachments

    def _attach_file(self, msg: MIMEMultipart, file_path: Path) -> bool:
        """Attach a file to the email message."""
        if not file_path.exists():
            return False
        
        # Get MIME type
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if mime_type is None:
            mime_type = 'application/octet-stream'
        
        main_type, sub_type = mime_type.split('/', 1)
        
        try:
            with open(file_path, 'rb') as f:
                file_data = f.read()
            
            if main_type == 'image':
                attachment = MIMEImage(file_data, _subtype=sub_type)
            elif main_type == 'application' and sub_type == 'pdf':
                attachment = MIMEApplication(file_data, _subtype=sub_type)
            else:
                attachment = MIMEBase(main_type, sub_type)
                attachment.set_payload(file_data)
                encoders.encode_base64(attachment)
            
            # Clean filename for attachment
            clean_name = file_path.name
            if len(clean_name) > 50:
                ext = file_path.suffix
                clean_name = clean_name[:45] + ext
            
            attachment.add_header(
                'Content-Disposition',
                'attachment',
                filename=clean_name
            )
            msg.attach(attachment)
            return True
            
        except Exception as e:
            print(f"Error attaching file {file_path}: {e}")
            return False

    def send_email(
        self,
        to_email: str,
        subject: str = "Pickleball Partnership Opportunity - Manh Thang Factory",
        body: Optional[str] = None,
        recipient_name: Optional[str] = None,
        include_attachments: bool = True,
        attachment_files: Optional[List[str]] = None
    ) -> dict:
        """Send email via Gmail SMTP with attachments."""
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
            # Create message with mixed content (text + attachments)
            msg = MIMEMultipart("mixed")
            msg["Subject"] = subject
            msg["From"] = f"Vijay Pawar <{self.sender_email}>"
            msg["To"] = to_email
            
            # Create alternative part for text/html
            alt_part = MIMEMultipart("alternative")
            
            # Plain text version
            text_part = MIMEText(email_body, "plain", "utf-8")
            alt_part.attach(text_part)
            
            # HTML version - convert to proper HTML with clickable link
            html_body = email_body.replace("\n", "<br>")
            # Make the Google Drive link clickable
            html_body = html_body.replace(
                CATALOG_LINK,
                f'<a href="{CATALOG_LINK}" style="color: #1a73e8; text-decoration: underline; font-weight: bold;">Click Here to View Catalog</a>'
            )
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
            alt_part.attach(html_part)
            
            msg.attach(alt_part)
            
            # Add attachments (only small files)
            attached_files = []
            skipped_files = []
            
            if include_attachments:
                files_to_attach = attachment_files or self.DEFAULT_ATTACHMENTS
                
                for filename in files_to_attach:
                    file_path = self.uploads_dir / filename
                    if file_path.exists():
                        size_mb = file_path.stat().st_size / (1024 * 1024)
                        if size_mb > 20:
                            skipped_files.append(f"{filename} (too large: {size_mb:.1f}MB)")
                            continue
                        
                        if self._attach_file(msg, file_path):
                            attached_files.append(filename)
                    else:
                        skipped_files.append(f"{filename} (not found)")
            
            # Send via SMTP
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
            
            result = {
                "success": True,
                "message": f"Email sent successfully to {to_email}",
                "to": to_email,
                "subject": subject,
                "attachments": attached_files,
                "catalog_link": CATALOG_LINK
            }
            
            if skipped_files:
                result["skipped_attachments"] = skipped_files
            
            return result
            
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

    def send_bulk_emails(
        self,
        recipients: list,
        subject: str = None,
        include_attachments: bool = True,
        delay_seconds: int = 2
    ) -> dict:
        """
        Send emails to multiple recipients with delay between sends.
        
        Args:
            recipients: List of dicts with 'email' and optional 'name'
            subject: Email subject line
            include_attachments: Whether to include file attachments
            delay_seconds: Delay between emails to avoid rate limits
            
        Returns:
            dict with success/failure counts and details
        """
        import time
        
        results = {
            "total": len(recipients),
            "sent": 0,
            "failed": 0,
            "skipped": 0,
            "details": []
        }
        
        for i, recipient in enumerate(recipients):
            email = recipient.get("email")
            name = recipient.get("name")
            
            if not email:
                results["skipped"] += 1
                results["details"].append({"email": None, "success": False, "error": "No email address"})
                continue
            
            # Add delay between emails (except first one)
            if i > 0:
                time.sleep(delay_seconds)
            
            result = self.send_email(
                to_email=email,
                subject=subject or "Pickleball Partnership Opportunity - Manh Thang Factory",
                recipient_name=name,
                include_attachments=include_attachments
            )
            
            if result.get("success"):
                results["sent"] += 1
            else:
                results["failed"] += 1
            
            results["details"].append({
                "email": email,
                "name": name,
                "success": result.get("success"),
                "error": result.get("error")
            })
        
        return results
