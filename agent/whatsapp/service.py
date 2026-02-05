"""
WhatsApp Service for Mac - Direct messaging with automation
"""
import os
import subprocess
import urllib.parse
import time
from typing import Optional
from pathlib import Path

# Default message template for Manh Thang Pickleball Factory
DEFAULT_WHATSAPP_MESSAGE = """Hi,

I'm Vijay from *Manh Thang Pickleball Factory* 🏓

We are a leading manufacturer of high-quality pickleball equipment with competitive pricing for retailers and wholesalers.

*What we offer:*
✅ Premium Pickleball Paddles
✅ Professional Pickleball Balls
✅ Nets & Accessories
✅ Custom Branding Available
✅ Bulk Order Discounts

I'd love to discuss a partnership opportunity with you. Could we schedule a quick call?

Looking forward to your response!

Best regards,
Vijay
Manh Thang Pickleball Factory
📧 vijaykp.kp@gmail.com"""

# Store permission status (persisted in memory during session)
_permission_granted = False


def get_permission_status() -> bool:
    """Check if user has granted automation permission"""
    global _permission_granted
    return _permission_granted


def set_permission_granted(granted: bool = True):
    """Set permission status after user grants it"""
    global _permission_granted
    _permission_granted = granted


def generate_whatsapp_url(phone: str, message: str = None) -> str:
    """Generate WhatsApp URL scheme for Mac desktop app"""
    phone_clean = ''.join(c for c in phone if c.isdigit() or c == '+')
    if not phone_clean.startswith('+'):
        phone_clean = '+91' + phone_clean.lstrip('0')
    
    phone_for_url = phone_clean.lstrip('+')
    msg = message or DEFAULT_WHATSAPP_MESSAGE
    encoded_msg = urllib.parse.quote(msg)
    
    return f"whatsapp://send?phone={phone_for_url}&text={encoded_msg}"


def open_whatsapp_chat(phone: str, message: str = None) -> dict:
    """Open WhatsApp on Mac with pre-filled message"""
    url = generate_whatsapp_url(phone, message)
    
    try:
        subprocess.run(['open', url], check=True)
        return {
            'success': True,
            'action': 'opened',
            'message': 'WhatsApp opened with chat ready. Press Enter/Send to deliver.',
            'url': url
        }
    except subprocess.CalledProcessError as e:
        return {
            'success': False,
            'error': f'Failed to open WhatsApp: {str(e)}',
            'url': url
        }


def send_whatsapp_direct(phone: str, message: str = None, attachment_path: str = None) -> dict:
    """Send WhatsApp message directly using AppleScript automation"""
    global _permission_granted
    
    phone_clean = ''.join(c for c in phone if c.isdigit() or c == '+')
    if not phone_clean.startswith('+'):
        phone_clean = '+91' + phone_clean.lstrip('0')
    phone_for_url = phone_clean.lstrip('+')
    
    msg = message or DEFAULT_WHATSAPP_MESSAGE
    encoded_msg = urllib.parse.quote(msg)
    
    # AppleScript to automate WhatsApp - opens chat, waits for it to load, then sends
    applescript = f'''
    tell application "WhatsApp"
        activate
    end tell
    
    delay 1
    
    do shell script "open 'whatsapp://send?phone={phone_for_url}&text={encoded_msg}'"
    
    delay 2
    
    tell application "System Events"
        tell process "WhatsApp"
            keystroke return
        end tell
    end tell
    '''
    
    try:
        result = subprocess.run(
            ['osascript', '-e', applescript],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            _permission_granted = True
            return {
                'success': True,
                'action': 'sent',
                'message': f'Message sent to {phone_clean}',
                'attachment': attachment_path if attachment_path else None
            }
        else:
            error_msg = result.stderr.strip()
            
            if 'not allowed' in error_msg.lower() or 'accessibility' in error_msg.lower() or 'assistive' in error_msg.lower():
                return {
                    'success': False,
                    'needs_permission': True,
                    'error': 'Accessibility permission required',
                    'instructions': [
                        '1. Open System Settings > Privacy & Security > Accessibility',
                        '2. Click the lock icon to make changes',
                        '3. Add and enable "Terminal" or your IDE (VS Code)',
                        '4. Try again - this is a one-time setup'
                    ]
                }
            
            return {
                'success': False,
                'error': f'AppleScript error: {error_msg}'
            }
            
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'error': 'Timeout - WhatsApp may not be responding'
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def get_default_attachment() -> Optional[str]:
    """Get the PDF attachment path from uploads folder"""
    uploads_dir = Path(__file__).parent.parent.parent / 'uploads'
    if uploads_dir.exists():
        for f in uploads_dir.iterdir():
            if f.suffix.lower() == '.pdf':
                return str(f.absolute())
    return None


class WhatsAppService:
    """WhatsApp service class for integration"""
    
    def __init__(self):
        self.permission_granted = get_permission_status()
        self.default_message = DEFAULT_WHATSAPP_MESSAGE
    
    def get_url(self, phone: str, message: str = None) -> str:
        return generate_whatsapp_url(phone, message)
    
    def open_chat(self, phone: str, message: str = None) -> dict:
        return open_whatsapp_chat(phone, message)
    
    def send_direct(self, phone: str, message: str = None, with_attachment: bool = False) -> dict:
        attachment = get_default_attachment() if with_attachment else None
        return send_whatsapp_direct(phone, message, attachment)
    
    def check_permission(self) -> dict:
        return {
            'permission_granted': get_permission_status(),
            'message': 'Automation ready' if get_permission_status() else 'Permission not yet granted'
        }
