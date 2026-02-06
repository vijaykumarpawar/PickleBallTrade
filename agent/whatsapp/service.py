"""WhatsApp automation service for macOS using AppleScript"""
import subprocess
import urllib.parse
import time
from typing import Optional, List
from pathlib import Path

# Google Drive Link for catalog/brochure
CATALOG_LINK = "https://drive.google.com/file/d/1h8w2aM2SvxvX7R40M51rAZznkljrmwHl/view?usp=sharing"

# Default message template for Manh Thang Pickleball Factory
DEFAULT_WHATSAPP_MESSAGE = f"""Hi,

I'm *Vijay Pawar* from *Manh Thang Pickleball Factory* (Vietnam) 🏓

We are a USAPA-certified manufacturer of tournament-grade pickleball balls, currently expanding in India.

*🏭 What We Offer:*
✅ E-WIN (ONE WIN) Tournament Balls - USAPA Certified
✅ Indoor & Outdoor Balls (26g / 26.5g)
✅ OEM / Private Label Manufacturing
✅ Bulk Order Pricing
✅ 100% Biodegradable Options

*📦 Factory Capacity:* 25,000-50,000 balls/day

📎 *View Our Catalog:*
{CATALOG_LINK}

We're appointing *India distributors, state partners & bulk buyers*.

Would you be interested in exploring a partnership?

*📞 India Contact:*
Vijay Pawar
📱 +91-7975397211
📧 vijaykp.kp@gmail.com

*🏭 Vietnam Factory:*
Manh Thang Industrial Service
📱 +84 91 253 16 66
📧 manhthang2666@gmail.com
🌐 www.manhthangpickleballfactory.com

Looking forward to connecting!"""

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
    """Generate WhatsApp URL with pre-filled message"""
    # Clean phone number
    phone_clean = ''.join(filter(str.isdigit, phone))
    if not phone_clean.startswith('91') and len(phone_clean) == 10:
        phone_clean = '91' + phone_clean
    
    msg = message or DEFAULT_WHATSAPP_MESSAGE
    encoded_msg = urllib.parse.quote(msg)
    
    return f"https://wa.me/{phone_clean}?text={encoded_msg}"


def open_whatsapp_chat(phone: str, message: str = None) -> dict:
    """Open WhatsApp on Mac with pre-filled message"""
    url = generate_whatsapp_url(phone, message)
    
    try:
        subprocess.run(['open', url], check=True)
        return {
            'success': True,
            'action': 'chat_opened',
            'message': 'WhatsApp opened with chat ready. Press Enter/Send to deliver.',
            'url': url,
            'catalog_link': CATALOG_LINK
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def send_whatsapp_with_image(phone: str, message: str = None, image_path: str = None) -> dict:
    """
    Send WhatsApp message with image attachment using AppleScript automation.
    
    Process:
    1. Send the text message first
    2. Wait for message to be sent
    3. Send the image as a separate message
    
    Returns dict with success status and details.
    """
    # Clean phone number
    phone_clean = ''.join(filter(str.isdigit, phone))
    if not phone_clean.startswith('91') and len(phone_clean) == 10:
        phone_clean = '91' + phone_clean
    
    msg = message or DEFAULT_WHATSAPP_MESSAGE
    
    # Get image path if not provided
    if not image_path:
        image_path = get_image_attachment()
    
    if image_path and not Path(image_path).exists():
        image_path = None
    
    # First, send the text message
    applescript_text = f'''
    tell application "WhatsApp"
        activate
        delay 2
    end tell
    
    -- Open chat with phone number using wa.me URL
    do shell script "open 'https://wa.me/{phone_clean}'"
    delay 3
    
    tell application "System Events"
        tell process "WhatsApp"
            set frontmost to true
            delay 1
            
            -- Type the message
            keystroke "{msg.replace('"', '\\"').replace("'", "'").replace(chr(10), '\\n')}"
            delay 0.5
            
            -- Send text message
            keystroke return
            delay 2
        end tell
    end tell
    '''
    
    # If we have an image, add image sending
    if image_path:
        applescript_with_image = applescript_text + f'''
        -- Now send the image
        tell application "System Events"
            tell process "WhatsApp"
                -- Click on attachment button (paperclip icon)
                -- Use keyboard shortcut if available, or we'll use a different approach
                
                -- Copy image to clipboard first
                set the clipboard to (read (POSIX file "{image_path}") as JPEG picture)
                delay 0.5
                
                -- Paste image
                keystroke "v" using command down
                delay 2
                
                -- Send image
                keystroke return
                delay 1
            end tell
        end tell
        '''
        
        # Try sending with image
        try:
            # First try to check if we have permission
            test_script = 'tell application "System Events" to return name of first process'
            test_result = subprocess.run(
                ['osascript', '-e', test_script],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if test_result.returncode != 0 and "not allowed" in test_result.stderr.lower():
                return {
                    'success': False,
                    'error': 'Accessibility permission required',
                    'action_required': 'Grant permission in System Preferences > Security & Privacy > Privacy > Accessibility',
                    'phone': phone_clean
                }
            
            # Send text message first (simpler approach without image initially)
            url = generate_whatsapp_url(phone, msg)
            subprocess.run(['open', url], check=True)
            time.sleep(3)  # Wait for WhatsApp to open
            
            # Use AppleScript to press Enter to send
            send_script = '''
            tell application "System Events"
                tell process "WhatsApp"
                    set frontmost to true
                    delay 1
                    keystroke return
                    delay 2
                end tell
            end tell
            '''
            
            result = subprocess.run(
                ['osascript', '-e', send_script],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                # Text sent, now try to send image
                try:
                    # Read image and copy to clipboard using AppleScript
                    img_path_escaped = image_path.replace("'", "'\\''")
                    
                    # Different approach: use Finder to copy file, then paste in WhatsApp
                    image_script = f'''
                    tell application "Finder"
                        set theFile to POSIX file "{img_path_escaped}" as alias
                        set the clipboard to theFile
                    end tell
                    
                    delay 0.5
                    
                    tell application "System Events"
                        tell process "WhatsApp"
                            set frontmost to true
                            delay 0.5
                            keystroke "v" using command down
                            delay 2
                            keystroke return
                        end tell
                    end tell
                    '''
                    
                    img_result = subprocess.run(
                        ['osascript', '-e', image_script],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    
                    if img_result.returncode == 0:
                        set_permission_granted(True)
                        return {
                            'success': True,
                            'action': 'message_and_image_sent',
                            'message': f'Message and image sent to {phone_clean}',
                            'phone': phone_clean,
                            'image': Path(image_path).name if image_path else None,
                            'catalog_link': CATALOG_LINK
                        }
                    else:
                        # Image failed but text was sent
                        set_permission_granted(True)
                        return {
                            'success': True,
                            'action': 'text_sent_image_failed',
                            'message': f'Text message sent to {phone_clean}. Image attachment failed: {str(img_result.stderr)}',
                            'phone': phone_clean,
                            'catalog_link': CATALOG_LINK
                        }
                except Exception as img_error:
                    return {
                        'success': True,
                        'action': 'text_sent_image_failed', 
                        'message': f'Text message sent to {phone_clean}. Image attachment failed: {str(img_error)}',
                        'phone': phone_clean,
                        'catalog_link': CATALOG_LINK
                    }
            else:
                return {
                    'success': True,
                    'action': 'chat_opened',
                    'message': f'Message sent to {phone_clean}',
                    'phone': phone_clean,
                    'catalog_link': CATALOG_LINK
                }
                
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': 'Timeout waiting for WhatsApp automation',
                'phone': phone_clean
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'phone': phone_clean
            }
    else:
        # No image, just send text
        return send_whatsapp_direct(phone, msg)


def send_whatsapp_direct(phone: str, message: str = None, attachment_path: str = None) -> dict:
    """Send WhatsApp message directly using AppleScript automation (legacy, no image)"""
    # Clean phone number
    phone_clean = ''.join(filter(str.isdigit, phone))
    if not phone_clean.startswith('91') and len(phone_clean) == 10:
        phone_clean = '91' + phone_clean
    
    msg = message or DEFAULT_WHATSAPP_MESSAGE
    
    try:
        # Open WhatsApp with pre-filled message
        url = generate_whatsapp_url(phone, msg)
        subprocess.run(['open', url], check=True)
        time.sleep(3)
        
        # Use AppleScript to press Enter to send
        send_script = '''
        tell application "System Events"
            tell process "WhatsApp"
                set frontmost to true
                delay 1
                keystroke return
            end tell
        end tell
        '''
        
        result = subprocess.run(
            ['osascript', '-e', send_script],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            set_permission_granted(True)
            return {
                'success': True,
                'action': 'message_sent',
                'message': f'Message sent to {phone_clean}',
                'phone': phone_clean,
                'catalog_link': CATALOG_LINK
            }
        else:
            # AppleScript failed, but chat is open
            return {
                'success': True,
                'action': 'chat_opened',
                'message': f'Chat opened for {phone_clean}. Press Enter to send.',
                'phone': phone_clean,
                'warning': result.stderr,
                'catalog_link': CATALOG_LINK
            }
            
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'error': 'Timeout waiting for WhatsApp',
            'phone': phone_clean
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'phone': phone_clean
        }


class WhatsAppService:
    """WhatsApp service class for cleaner integration"""
    
    def __init__(self):
        self.default_message = DEFAULT_WHATSAPP_MESSAGE
        self.catalog_link = CATALOG_LINK
    
    def get_url(self, phone: str, message: str = None) -> str:
        return generate_whatsapp_url(phone, message)
    
    def open_chat(self, phone: str, message: str = None) -> dict:
        return open_whatsapp_chat(phone, message)
    
    def send_direct(self, phone: str, message: str = None, with_attachment: bool = False) -> dict:
        """Send message without image (legacy method)"""
        attachment = get_image_attachment() if with_attachment else None
        return send_whatsapp_direct(phone, message, attachment)
    
    def send_with_image(self, phone: str, message: str = None, image_path: str = None) -> dict:
        """Send message with image attachment"""
        return send_whatsapp_with_image(phone, message, image_path)
    
    def get_image_path(self) -> Optional[str]:
        """Get available image attachment"""
        return get_image_attachment()
    
    def get_pdf_path(self) -> Optional[str]:
        """Get available PDF attachment"""
        return get_pdf_attachment()
    
    def get_available_attachments(self) -> List[dict]:
        """Get all available attachments"""
        return get_all_attachments()
    
    def check_permission(self) -> dict:
        """Check if accessibility permission is granted"""
        return {
            'permission_granted': get_permission_status(),
            'message': 'Automation ready' if get_permission_status() else 'Permission not yet granted',
            'catalog_link': CATALOG_LINK
        }
