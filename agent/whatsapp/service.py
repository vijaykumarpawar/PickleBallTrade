"""
WhatsApp Service for Mac - Direct messaging with image attachments
"""
import os
import subprocess
import urllib.parse
import time
from typing import Optional, List
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


def get_uploads_folder() -> Path:
    """Get the uploads folder path"""
    return Path(__file__).parent.parent.parent / 'uploads'


def get_image_attachment() -> Optional[str]:
    """Get image attachment path from uploads folder"""
    uploads_dir = get_uploads_folder()
    if uploads_dir.exists():
        for f in uploads_dir.iterdir():
            if f.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                return str(f.absolute())
    return None


def get_pdf_attachment() -> Optional[str]:
    """Get PDF attachment path from uploads folder"""
    uploads_dir = get_uploads_folder()
    if uploads_dir.exists():
        for f in uploads_dir.iterdir():
            if f.suffix.lower() == '.pdf':
                return str(f.absolute())
    return None


def get_all_attachments() -> List[dict]:
    """Get all available attachments from uploads folder"""
    attachments = []
    uploads_dir = get_uploads_folder()
    if uploads_dir.exists():
        for f in uploads_dir.iterdir():
            if f.is_file():
                size_mb = f.stat().st_size / (1024 * 1024)
                attachments.append({
                    'name': f.name,
                    'path': str(f.absolute()),
                    'size_mb': round(size_mb, 2),
                    'type': 'image' if f.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.webp'] else 'pdf' if f.suffix.lower() == '.pdf' else 'other'
                })
    return attachments


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


def send_whatsapp_with_image(phone: str, message: str = None, image_path: str = None) -> dict:
    """
    Send WhatsApp message with image attachment using AppleScript automation.
    
    This uses a two-step process:
    1. Send the text message first
    2. Then attach and send the image
    """
    global _permission_granted
    
    phone_clean = ''.join(c for c in phone if c.isdigit() or c == '+')
    if not phone_clean.startswith('+'):
        phone_clean = '+91' + phone_clean.lstrip('0')
    phone_for_url = phone_clean.lstrip('+')
    
    msg = message or DEFAULT_WHATSAPP_MESSAGE
    encoded_msg = urllib.parse.quote(msg)
    
    # Get image path if not provided
    if not image_path:
        image_path = get_image_attachment()
    
    # First, send the text message
    applescript_text = f'''
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
        # Send text message first
        result = subprocess.run(
            ['osascript', '-e', applescript_text],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
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
        
        _permission_granted = True
        
        # If we have an image, send it
        if image_path and os.path.exists(image_path):
            time.sleep(1)  # Wait for message to send
            
            # AppleScript to attach and send image
            # This copies the image to clipboard and pastes it into WhatsApp
            applescript_image = f'''
            -- Copy image to clipboard
            set theImage to POSIX file "{image_path}"
            set the clipboard to (read theImage as «class PNGf»)
            
            delay 0.5
            
            -- Paste into WhatsApp
            tell application "System Events"
                tell process "WhatsApp"
                    keystroke "v" using command down
                end tell
            end tell
            
            delay 1
            
            -- Send the image
            tell application "System Events"
                tell process "WhatsApp"
                    keystroke return
                end tell
            end tell
            '''
            
            # Try PNG first, if fails try JPEG
            try:
                img_result = subprocess.run(
                    ['osascript', '-e', applescript_image],
                    capture_output=True,
                    text=True,
                    timeout=15
                )
                
                if img_result.returncode != 0:
                    # Try JPEG format
                    applescript_image_jpeg = f'''
                    set theImage to POSIX file "{image_path}"
                    set the clipboard to (read theImage as JPEG picture)
                    
                    delay 0.5
                    
                    tell application "System Events"
                        tell process "WhatsApp"
                            keystroke "v" using command down
                        end tell
                    end tell
                    
                    delay 1
                    
                    tell application "System Events"
                        tell process "WhatsApp"
                            keystroke return
                        end tell
                    end tell
                    '''
                    
                    img_result2 = subprocess.run(
                        ['osascript', '-e', applescript_image_jpeg],
                        capture_output=True,
                        text=True,
                        timeout=15
                    )
                    
                    if img_result2.returncode != 0:
                        # Fall back to drag-drop method via Finder
                        applescript_finder = f'''
                        tell application "Finder"
                            set theFile to POSIX file "{image_path}" as alias
                            select theFile
                        end tell
                        
                        delay 0.5
                        
                        tell application "System Events"
                            keystroke "c" using command down
                        end tell
                        
                        delay 0.5
                        
                        tell application "WhatsApp"
                            activate
                        end tell
                        
                        delay 0.5
                        
                        tell application "System Events"
                            tell process "WhatsApp"
                                keystroke "v" using command down
                            end tell
                        end tell
                        
                        delay 1
                        
                        tell application "System Events"
                            tell process "WhatsApp"
                                keystroke return
                            end tell
                        end tell
                        '''
                        
                        subprocess.run(
                            ['osascript', '-e', applescript_finder],
                            capture_output=True,
                            text=True,
                            timeout=15
                        )
                
                return {
                    'success': True,
                    'action': 'sent_with_image',
                    'message': f'Message and image sent to {phone_clean}',
                    'image': image_path
                }
                
            except Exception as img_error:
                # Text was sent, image failed
                return {
                    'success': True,
                    'action': 'sent_text_only',
                    'message': f'Text message sent to {phone_clean}. Image attachment failed: {str(img_error)}',
                    'image_error': str(img_error)
                }
        
        return {
            'success': True,
            'action': 'sent',
            'message': f'Message sent to {phone_clean}',
            'image': None
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


def send_whatsapp_direct(phone: str, message: str = None, attachment_path: str = None) -> dict:
    """Send WhatsApp message directly using AppleScript automation (legacy, no image)"""
    global _permission_granted
    
    phone_clean = ''.join(c for c in phone if c.isdigit() or c == '+')
    if not phone_clean.startswith('+'):
        phone_clean = '+91' + phone_clean.lstrip('0')
    phone_for_url = phone_clean.lstrip('+')
    
    msg = message or DEFAULT_WHATSAPP_MESSAGE
    encoded_msg = urllib.parse.quote(msg)
    
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


class WhatsAppService:
    """WhatsApp service class for integration with image support"""
    
    def __init__(self):
        self.permission_granted = get_permission_status()
        self.default_message = DEFAULT_WHATSAPP_MESSAGE
    
    def get_url(self, phone: str, message: str = None) -> str:
        return generate_whatsapp_url(phone, message)
    
    def open_chat(self, phone: str, message: str = None) -> dict:
        return open_whatsapp_chat(phone, message)
    
    def send_direct(self, phone: str, message: str = None, with_attachment: bool = False) -> dict:
        """Send message without image (legacy method)"""
        attachment = get_pdf_attachment() if with_attachment else None
        return send_whatsapp_direct(phone, message, attachment)
    
    def send_with_image(self, phone: str, message: str = None, image_path: str = None) -> dict:
        """Send message with image attachment"""
        return send_whatsapp_with_image(phone, message, image_path)
    
    def get_available_attachments(self) -> List[dict]:
        """Get list of available attachments"""
        return get_all_attachments()
    
    def get_image_path(self) -> Optional[str]:
        """Get the default image path"""
        return get_image_attachment()
    
    def get_pdf_path(self) -> Optional[str]:
        """Get the default PDF path"""
        return get_pdf_attachment()
    
    def check_permission(self) -> dict:
        return {
            'permission_granted': get_permission_status(),
            'message': 'Automation ready' if get_permission_status() else 'Permission not yet granted'
        }
