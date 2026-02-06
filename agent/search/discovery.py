"""
Enhanced Lead Discovery Engine
Implements comprehensive search strategies across multiple sources:
1. Industry directories & trade portals (IndiaMART, TradeIndia, JustDial, Sulekha)
2. Manufacturer → authorized distributor lists
3. Trade shows & expo attendee lists
4. LinkedIn targeted search
5. Facebook/WhatsApp trade groups
6. Google advanced search + local SEO
7. Yellow pages & chamber of commerce
8. Marketplace seller lookup (Amazon, Flipkart)
9. Related sports shops & gyms
10. CURATED PICKLEBALL COMPANIES - Direct website scraping

NEW FEATURES:
- Curated list of known pickleball importers/distributors in India
- Website scraper to extract contact details from any URL
- Enrich existing leads by visiting their websites
"""
import json
import os
import re
import asyncio
from typing import List, Dict, Optional, Set, Tuple
from ddgs import DDGS
import httpx
from bs4 import BeautifulSoup
from urllib.parse import quote_plus, urlparse, urljoin
import time


class SearchEngine:
    def __init__(self):
        config_path = "agent/config/cities.json"
        if os.path.exists(config_path):
            with open(config_path) as f:
                self.cities_config = json.load(f)
        else:
            self.cities_config = {"tier_1": [], "tier_2": [], "tier_3": []}
        
        # === CURATED PICKLEBALL COMPANIES IN INDIA ===
        # These are known importers, manufacturers, dealers, and distributors
        self.curated_companies = [
            # JOOLA India and Authorized Dealers
            {
                "name": "JOOLA India",
                "role": "Manufacturer & Distributor",
                "city": "Bengaluru",
                "website": "https://joola.in",
                "additional_urls": [
                    "https://joola.in/pages/authorized-distributors",
                    "https://joola.in/pages/contact-us"
                ]
            },
            {
                "name": "Selection Centre Sports (SCS Sports)",
                "role": "Dealer (JOOLA Authorized)",
                "city": "Mumbai",
                "website": "https://scssports.in",
                "additional_urls": ["https://scssports.in/contact-us"]
            },
            {
                "name": "Pickleball Outlet",
                "role": "JOOLA Authorized Dealer",
                "city": "Hyderabad",
                "website": "https://pickleballoutlet.in",
                "additional_urls": ["https://pickleballoutlet.in/contact"]
            },
            {
                "name": "Cialfo Sports",
                "role": "JOOLA Authorized Dealer",
                "city": "Chennai",
                "website": "https://cialfosports.com",
                "additional_urls": ["https://cialfosports.com/contact"]
            },
            {
                "name": "Sporfy Store",
                "role": "JOOLA Authorized Dealer",
                "city": "Coimbatore",
                "website": "https://sporfystore.com",
                "additional_urls": ["https://sporfystore.com/contact-us"]
            },
            {
                "name": "Fyre Sports",
                "role": "JOOLA Authorized Dealer",
                "city": "Jaipur",
                "website": "https://fyresports.in",
                "additional_urls": ["https://fyresports.in/contact"]
            },
            {
                "name": "Play IQ",
                "role": "JOOLA Authorized Dealer",
                "city": "Bengaluru",
                "website": "https://playiq.in",
                "additional_urls": ["https://playiq.in/contact"]
            },
            {
                "name": "Lodhi Sports",
                "role": "JOOLA Authorized Dealer",
                "city": "Delhi",
                "website": "https://lodhisport.com",
                "additional_urls": ["https://lodhisport.com/contact-us"]
            },
            # Major Manufacturers & Suppliers
            {
                "name": "Vinex Enterprises",
                "role": "Manufacturer & Supplier",
                "city": "Meerut",
                "website": "https://www.vinex.in",
                "additional_urls": [
                    "https://www.vinex.in/Pickleball-Equipment.html",
                    "https://www.vinex.in/contact-us.html"
                ]
            },
            {
                "name": "Metco Sports India",
                "role": "Manufacturer & Dealer",
                "city": "Meerut",
                "website": "https://www.metcosportsindia.com",
                "additional_urls": [
                    "https://www.metcosportsindia.com/pickleball-pole-paddles-and-equipment.html",
                    "https://www.metcosportsindia.com/contact-us.html"
                ]
            },
            {
                "name": "Strokess Sporting Solutions",
                "role": "Manufacturer & Brand",
                "city": "Vadodara",
                "website": "https://strokess.com",
                "additional_urls": ["https://strokess.com/contact"]
            },
            # Wholesalers & Distributors
            {
                "name": "Total Pickleball",
                "role": "Wholesaler/Distributor",
                "city": "Jaipur",
                "website": "https://www.indiamart.com/total-pickleball",
                "additional_urls": [
                    "https://www.indiamart.com/total-pickleball/fitness-equipments.html",
                    "https://www.indiamart.com/total-pickleball/aboutus.html"
                ]
            },
            # Sports Equipment Companies
            {
                "name": "Cosco India",
                "role": "Sports Equipment Manufacturer",
                "city": "Delhi",
                "website": "https://www.cosco.in",
                "additional_urls": ["https://www.cosco.in/contact-us"]
            },
            {
                "name": "Nivia Sports",
                "role": "Sports Equipment Manufacturer",
                "city": "Jalandhar",
                "website": "https://niviasports.com",
                "additional_urls": ["https://niviasports.com/contact-us"]
            },
            {
                "name": "Vector X Sports",
                "role": "Sports Equipment Manufacturer",
                "city": "Meerut",
                "website": "https://vectorxsports.com",
                "additional_urls": ["https://vectorxsports.com/contact"]
            },
            # Online Retailers with Contact Info
            {
                "name": "Sports 365",
                "role": "Online Retailer",
                "city": "Mumbai",
                "website": "https://www.sports365.in",
                "additional_urls": ["https://www.sports365.in/contact-us"]
            },
            {
                "name": "Racquet Point",
                "role": "Racquet Sports Specialist",
                "city": "Delhi",
                "website": "https://racquetpoint.in",
                "additional_urls": ["https://racquetpoint.in/contact"]
            },
            # Regional Distributors
            {
                "name": "Meerut Sports Industries Association",
                "role": "Industry Association",
                "city": "Meerut",
                "website": "https://www.meerutsports.com",
                "additional_urls": ["https://www.meerutsports.com/contact"]
            },
            {
                "name": "Sports Wing",
                "role": "Sports Equipment Dealer",
                "city": "Chennai",
                "website": "https://sportswing.in",
                "additional_urls": ["https://sportswing.in/contact-us"]
            },
        ]
        
        # Keywords to search for
        self.keywords = [
            "pickleball",
            "pickle ball",
            "pickleball paddle",
            "pickleball ball",
            "pickleball equipment",
            "pickleball distributor",
            "pickleball wholesale",
            "pickleball importer",
            "sports equipment distributor",
            "racket sports wholesale",
            "paddle sports",
        ]
        
        # === STRATEGY 1: Industry Directories & Trade Portals ===
        self.directory_search_templates = [
            # IndiaMART
            'site:indiamart.com "pickleball" {city}',
            'site:indiamart.com "pickleball paddle" distributor',
            'site:indiamart.com "pickleball" "wholesale"',
            'site:indiamart.com "sports equipment" "pickleball" {city}',
            # TradeIndia
            'site:tradeindia.com "pickleball" {city}',
            'site:tradeindia.com "pickleball" distributor India',
            'site:tradeindia.com "sports equipment" wholesale {city}',
            # JustDial
            'site:justdial.com "pickleball" {city}',
            'site:justdial.com "sports equipment" dealer {city}',
            # ExportersIndia
            'site:exportersindia.com "pickleball"',
            'site:exportersindia.com "sports goods" "distributor"',
            # Sulekha
            'site:sulekha.com "sports equipment" {city}',
            'site:sulekha.com "sports shop" {city}',
            # Go4WorldBusiness
            'site:go4worldbusiness.com "pickleball" India',
            # Tradexcel
            'site:tradexcel.in "sports equipment"',
        ]
        
        # === STRATEGY 2: Manufacturer & Authorized Distributor Lists ===
        self.manufacturer_search_templates = [
            '"pickleball" "authorized distributor" India',
            '"pickleball" "where to buy" India {city}',
            '"pickleball" "dealer locator" India',
            '"pickleball brand" "India partner"',
            'USAPA pickleball distributor India',
            '"pickleball" manufacturer "India office"',
            '"HEAD pickleball" OR "Franklin pickleball" OR "Selkirk pickleball" distributor India',
            '"pickleball" "official distributor" {city}',
        ]
        
        # === STRATEGY 3: Trade Shows & Expos ===
        self.tradeshow_search_templates = [
            '"sports expo" exhibitor list India {city}',
            '"sporting goods fair" India exhibitors',
            '"IISF" India sports fair exhibitor',
            '"sports trade show" India 2024 2025 participants',
            '"pickleball" "trade show" India exhibitor',
            'sports equipment exhibition India exhibitor contact',
        ]
        
        # === STRATEGY 4: LinkedIn Targeted Search ===
        self.linkedin_search_templates = [
            'site:linkedin.com/in "pickleball" "distributor" India',
            'site:linkedin.com/in "sports equipment" "sales" India {city}',
            'site:linkedin.com/company "pickleball" India',
            'site:linkedin.com "channel partner" "sports" India',
            '"pickleball" "business development" India contact',
        ]
        
        # === STRATEGY 6: Google Advanced Search + Local SEO ===
        self.google_advanced_templates = [
            'intitle:distributor "pickleball" India',
            'intitle:wholesale "pickleball" {city}',
            '"pickleball" "wholesale" "contact" OR "mobile" India',
            '"pickleball" "dealer" "phone" {city}',
            '"pickleball equipment" supplier {city} contact email',
            '"pickleball" "bulk order" India',
            'inurl:contact "pickleball" India',
            '"sports goods" "wholesale dealer" {city} contact',
        ]
        
        # === STRATEGY 7: Yellow Pages & Chamber of Commerce ===
        self.yellowpages_search_templates = [
            'site:yellowpages.co.in "sports" {city}',
            'site:yellowpages.in "sports equipment" {city}',
            '"chamber of commerce" "sports goods" {city}',
            'MSME sports equipment {city} directory',
            '"sports goods association" {city} members',
        ]
        
        # === STRATEGY 8: Marketplace Sellers (Amazon, Flipkart) ===
        self.marketplace_search_templates = [
            'site:amazon.in "pickleball" "sold by" contact',
            '"amazon seller" "pickleball" India contact',
            '"flipkart seller" "pickleball" contact',
            '"pickleball" seller India wholesale bulk',
            'decathlon pickleball supplier India',
        ]
        
        # === STRATEGY 9: Related Sports Shops & Gyms ===
        self.sports_shop_search_templates = [
            '"tennis shop" "pickleball" {city}',
            '"badminton shop" {city} contact',
            '"sports academy" "pickleball" {city}',
            '"pickleball club" {city} equipment supplier',
            '"fitness center" "pickleball" {city}',
            '"racket sports" shop {city} wholesale',
        ]
        
        # All search templates combined
        self.all_search_templates = (
            self.directory_search_templates +
            self.manufacturer_search_templates +
            self.google_advanced_templates +
            self.yellowpages_search_templates +
            self.marketplace_search_templates +
            self.sports_shop_search_templates
        )
        
        # Priority domains (business directories - most reliable)
        self.priority_domains = {
            "indiamart.com": 10,
            "tradeindia.com": 10,
            "justdial.com": 9,
            "exportersindia.com": 9,
            "sulekha.com": 8,
            "yellowpages.co.in": 8,
            "go4worldbusiness.com": 7,
            "tradexcel.in": 7,
            "linkedin.com": 6,
            "alibaba.com": 6,
        }
        
        # Domains to skip
        self.skip_domains = [
            "youtube.com", "facebook.com", "twitter.com", "x.com",
            "instagram.com", "wikipedia.org", "pinterest.com",
            "news", "thehindu", "indiatimes", "ndtv", "india.com",
            "bbc.com", "cnn.com", "reuters", "bloomberg",
            "quora.com", "reddit.com", "medium.com",
        ]
        
        self.http_client = None
        self._request_count = 0
        self._last_request_time = 0

    def get_all_cities(self):
        cities = []
        for tier, city_list in self.cities_config.items():
            for city in city_list:
                cities.append({"name": city, "tier": tier})
        return cities

    def _get_tier(self, city: str) -> str:
        for tier, cities in self.cities_config.items():
            if city in cities:
                return tier
        return "tier_2"

    def _extract_contact_info(self, text: str, html_soup: Optional[BeautifulSoup] = None) -> Dict:
        """Extract email and phone from text with enhanced patterns."""
        contact = {}
        
        # Email patterns
        email_patterns = [
            r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
            r"[\w.-]+\s*@\s*[\w.-]+\.\w+",  # With spaces around @
            r"[\w.-]+\s*\[at\]\s*[\w.-]+\.\w+",  # [at] notation
        ]
        
        for pattern in email_patterns:
            emails = re.findall(pattern, text, re.IGNORECASE)
            # Filter out common non-business emails
            filtered_emails = [
                e.replace(" ", "").replace("[at]", "@") 
                for e in emails 
                if not any(x in e.lower() for x in [
                    'example', 'test', 'noreply', 'no-reply', 'admin@',
                    'support@', 'info@example', 'email@', 'your@', 'name@',
                    'sentry.io', 'wixpress', 'google.com', 'facebook.com'
                ])
            ]
            if filtered_emails:
                contact["email"] = filtered_emails[0]
                break
        
        # Also try to find email in mailto links (HTML)
        if html_soup and not contact.get("email"):
            mailto_links = html_soup.find_all("a", href=re.compile(r"mailto:", re.I))
            for link in mailto_links:
                href = link.get("href", "")
                email_match = re.search(r"mailto:([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})", href)
                if email_match:
                    email = email_match.group(1)
                    if not any(x in email.lower() for x in ['example', 'noreply', 'wixpress']):
                        contact["email"] = email
                        break
        
        # Phone patterns for India (enhanced)
        phone_patterns = [
            r"\+91[\s.-]*\d{5}[\s.-]*\d{5}",  # +91 XXXXX XXXXX
            r"\+91[\s.-]*\d{10}",  # +91XXXXXXXXXX
            r"91[\s.-]*\d{10}",  # 91XXXXXXXXXX
            r"0\d{2,4}[\s.-]*\d{6,8}",  # Landline with STD
            r"(?<![0-9])[789]\d{9}(?![0-9])",  # Mobile starting with 7/8/9
            r"(?<![0-9])\d{10}(?![0-9])",  # Any 10 digit
        ]
        
        for pattern in phone_patterns:
            phones = re.findall(pattern, text)
            if phones:
                phone = re.sub(r'[\s.-]', '', phones[0])
                # Ensure it's a valid length
                digits_only = re.sub(r'\D', '', phone)
                if 10 <= len(digits_only) <= 13:
                    # Format properly
                    if not phone.startswith('+'):
                        if phone.startswith('91') and len(digits_only) == 12:
                            phone = '+' + phone
                        elif len(digits_only) == 10:
                            phone = '+91' + digits_only
                    contact["phone"] = phone
                    break
        
        # Also try tel: links in HTML
        if html_soup and not contact.get("phone"):
            tel_links = html_soup.find_all("a", href=re.compile(r"tel:", re.I))
            for link in tel_links:
                href = link.get("href", "")
                phone_match = re.search(r"tel:[\+]?(\d[\d\s.-]{8,15})", href)
                if phone_match:
                    phone = re.sub(r'[\s.-]', '', phone_match.group(1))
                    digits_only = re.sub(r'\D', '', phone)
                    if 10 <= len(digits_only) <= 13:
                        if not phone.startswith('+'):
                            phone = '+91' + digits_only[-10:]
                        contact["phone"] = phone
                        break
        
        # Try to extract WhatsApp number specifically
        whatsapp_patterns = [
            r"whatsapp[\s:]*\+?[\d\s.-]{10,15}",
            r"wa[\s:]*\+?[\d\s.-]{10,15}",
            r"📱[\s:]*\+?[\d\s.-]{10,15}",
            r"wa\.me/(\d{10,15})",
            r"api\.whatsapp\.com/send\?phone=(\d{10,15})",
        ]
        
        for pattern in whatsapp_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                wa_num = re.sub(r'[^\d+]', '', matches[0] if isinstance(matches[0], str) else str(matches[0]))
                if len(wa_num) >= 10:
                    contact["whatsapp"] = wa_num if wa_num.startswith('+') else '+91' + wa_num[-10:]
                    if not contact.get("phone"):
                        contact["phone"] = contact["whatsapp"]
                    break
        
        return contact

    def _clean_business_name(self, title: str) -> str:
        """Clean up business name from search title."""
        remove_patterns = [
            r"\s*[-|–—].*$",
            r"\s*\|.*$",
            r"\s*::.*$",
            r"\s*-\s*IndiaMART.*$",
            r"\s*-\s*TradeIndia.*$",
            r"\s*-\s*JustDial.*$",
            r"\s*-\s*Sulekha.*$",
            r"\s*-\s*LinkedIn.*$",
            r"\s*,\s*\w+\s*$",
            r"\bPvt\.?\s*Ltd\.?\b",
            r"\bPrivate\s*Limited\b",
            r"\bLLP\b",
            r"\bInc\.?\b",
            r"\bLLC\b",
            r"^\d+\.\s*",  # Remove leading numbers
        ]
        name = title
        for pattern in remove_patterns:
            name = re.sub(pattern, "", name, flags=re.IGNORECASE)
        return name.strip()[:100]

    def _get_url_priority(self, url: str) -> int:
        """Get priority score for URL (higher = better)."""
        url_lower = url.lower()
        
        # Check against priority domains
        for domain, score in self.priority_domains.items():
            if domain in url_lower:
                return score
        
        # Business-like URL patterns
        if any(pattern in url_lower for pattern in ['/company/', '/supplier/', '/manufacturer/', '/dealer/']):
            return 5
        
        return 1

    def _is_business_url(self, url: str) -> bool:
        """Check if URL is likely a business listing."""
        url_lower = url.lower()
        
        # Skip non-business domains
        if any(domain in url_lower for domain in self.skip_domains):
            return False
        
        return True

    def _extract_business_type(self, text: str) -> str:
        """Determine business type from text content."""
        text_lower = text.lower()
        
        type_keywords = {
            "Manufacturer": ["manufacturer", "manufacturing", "factory", "produce", "maker"],
            "Distributor": ["distributor", "distribution", "channel partner"],
            "Importer": ["importer", "importing", "import"],
            "Exporter": ["exporter", "export"],
            "Wholesaler": ["wholesale", "wholesaler", "bulk supplier", "bulk order"],
            "Retailer": ["retail", "retailer", "shop", "store", "showroom"],
            "Dealer": ["dealer", "dealership", "authorized dealer"],
            "Supplier": ["supplier", "supply", "vendor"],
            "Trader": ["trader", "trading company", "trading firm"],
            "Academy": ["academy", "training", "coaching", "club"],
        }
        
        for biz_type, keywords in type_keywords.items():
            if any(kw in text_lower for kw in keywords):
                return biz_type
        
        return "Unknown"

    def _rate_limit(self):
        """Simple rate limiting to avoid getting blocked."""
        self._request_count += 1
        current_time = time.time()
        
        if self._request_count > 10:
            elapsed = current_time - self._last_request_time
            if elapsed < 2:
                time.sleep(2 - elapsed)
            self._request_count = 0
        
        self._last_request_time = current_time

    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if not self.http_client:
            self.http_client = httpx.AsyncClient(
                timeout=15.0, 
                follow_redirects=True,
                limits=httpx.Limits(max_connections=10),
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                }
            )
        return self.http_client

    async def scrape_website_contacts(self, url: str, follow_contact_pages: bool = True) -> Dict:
        """
        Scrape a website to extract contact information.
        
        Args:
            url: The website URL to scrape
            follow_contact_pages: Whether to also scrape contact/about pages
            
        Returns:
            Dictionary with email, phone, whatsapp, address, and other contact info
        """
        result = {
            "url": url,
            "email": None,
            "phone": None,
            "whatsapp": None,
            "address": None,
            "contact_person": None,
            "social_links": [],
            "pages_scraped": [],
            "success": False,
            "error": None
        }
        
        try:
            client = await self._get_http_client()
            self._rate_limit()
            
            # Scrape main page
            response = await client.get(url)
            
            if response.status_code != 200:
                result["error"] = f"HTTP {response.status_code}"
                return result
            
            soup = BeautifulSoup(response.text, "html.parser")
            text = soup.get_text(separator=" ", strip=True)
            result["pages_scraped"].append(url)
            
            # Extract contact info from main page
            contact = self._extract_contact_info(text, soup)
            result.update({k: v for k, v in contact.items() if v})
            
            # Try to find address
            address = self._extract_address(text, soup)
            if address:
                result["address"] = address
            
            # Look for social links
            social_links = self._extract_social_links(soup, url)
            result["social_links"] = social_links
            
            # If enabled, follow contact/about pages
            if follow_contact_pages:
                contact_pages = self._find_contact_pages(soup, url)
                
                for page_url in contact_pages[:3]:  # Limit to 3 contact pages
                    if page_url in result["pages_scraped"]:
                        continue
                    
                    try:
                        self._rate_limit()
                        page_response = await client.get(page_url)
                        
                        if page_response.status_code == 200:
                            page_soup = BeautifulSoup(page_response.text, "html.parser")
                            page_text = page_soup.get_text(separator=" ", strip=True)
                            result["pages_scraped"].append(page_url)
                            
                            page_contact = self._extract_contact_info(page_text, page_soup)
                            
                            # Update if we found new info
                            if page_contact.get("email") and not result.get("email"):
                                result["email"] = page_contact["email"]
                            if page_contact.get("phone") and not result.get("phone"):
                                result["phone"] = page_contact["phone"]
                            if page_contact.get("whatsapp") and not result.get("whatsapp"):
                                result["whatsapp"] = page_contact["whatsapp"]
                            
                            # Try to find address on contact page
                            if not result.get("address"):
                                address = self._extract_address(page_text, page_soup)
                                if address:
                                    result["address"] = address
                                    
                    except Exception as page_error:
                        pass  # Continue with other pages
            
            result["success"] = bool(result.get("email") or result.get("phone"))
            
        except Exception as e:
            result["error"] = str(e)
        
        return result

    def _extract_address(self, text: str, soup: Optional[BeautifulSoup] = None) -> Optional[str]:
        """Extract address from text or HTML."""
        address = None
        
        # Try specific HTML tags first
        if soup:
            # Look for address tag
            for tag in soup.find_all(["address"]):
                tag_text = tag.get_text(strip=True)
                if 20 < len(tag_text) < 300:
                    return tag_text[:250]
            
            # Look for address-related classes
            for tag in soup.find_all(["div", "span", "p"], class_=re.compile(r"address|location|office", re.I)):
                tag_text = tag.get_text(strip=True)
                if 20 < len(tag_text) < 300 and any(x in tag_text.lower() for x in ["india", "road", "street", "nagar", "pin", "zip"]):
                    return tag_text[:250]
        
        # Try text patterns
        address_patterns = [
            r"(?:address|office|location)[\s:]+([^,\n]{20,200}(?:india|pin|zip|\d{6}))",
            r"(?:corporate office|head office|registered office)[\s:]+([^,\n]{20,200})",
            r"(\d+[,/]?\s*[\w\s,]+(?:road|street|nagar|colony|area|sector|phase|block)[\w\s,]*(?:india|\d{6}))",
        ]
        
        for pattern in address_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()[:250]
        
        return None

    def _extract_social_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract social media links from page."""
        social_domains = ["linkedin.com", "facebook.com", "twitter.com", "instagram.com", "youtube.com"]
        social_links = []
        
        for link in soup.find_all("a", href=True):
            href = link.get("href", "")
            for domain in social_domains:
                if domain in href:
                    social_links.append(href)
                    break
        
        return list(set(social_links))[:5]

    def _find_contact_pages(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Find contact, about, and related pages."""
        contact_keywords = ["contact", "about", "reach", "connect", "enquiry", "inquiry", "dealer", "distributor", "where-to-buy"]
        contact_pages = []
        
        parsed_base = urlparse(base_url)
        base_domain = f"{parsed_base.scheme}://{parsed_base.netloc}"
        
        for link in soup.find_all("a", href=True):
            href = link.get("href", "").lower()
            text = link.get_text().lower()
            
            # Check if link contains contact-related keywords
            if any(kw in href or kw in text for kw in contact_keywords):
                full_url = href if href.startswith("http") else urljoin(base_domain, href)
                
                # Only include pages from same domain
                if parsed_base.netloc in full_url:
                    contact_pages.append(full_url)
        
        return list(set(contact_pages))

    async def discover_from_curated_list(self, city: Optional[str] = None) -> List[Dict]:
        """
        Discover leads from the curated list of known pickleball companies.
        Scrapes each website to get contact details.
        
        Args:
            city: Optional city filter
            
        Returns:
            List of enriched business dictionaries
        """
        results = []
        
        companies = self.curated_companies
        if city:
            companies = [c for c in companies if c.get("city", "").lower() == city.lower()]
        
        print(f"[Curated List] Scraping {len(companies)} known pickleball companies...")
        
        for i, company in enumerate(companies):
            print(f"  [{i+1}/{len(companies)}] {company['name']}...")
            
            # Scrape main website
            website = company.get("website", "")
            scraped = await self.scrape_website_contacts(website, follow_contact_pages=True)
            
            # Also scrape additional URLs if provided
            additional_urls = company.get("additional_urls", [])
            for add_url in additional_urls:
                if add_url not in scraped.get("pages_scraped", []):
                    try:
                        self._rate_limit()
                        add_scraped = await self.scrape_website_contacts(add_url, follow_contact_pages=False)
                        
                        if add_scraped.get("email") and not scraped.get("email"):
                            scraped["email"] = add_scraped["email"]
                        if add_scraped.get("phone") and not scraped.get("phone"):
                            scraped["phone"] = add_scraped["phone"]
                        if add_scraped.get("whatsapp") and not scraped.get("whatsapp"):
                            scraped["whatsapp"] = add_scraped["whatsapp"]
                        if add_scraped.get("address") and not scraped.get("address"):
                            scraped["address"] = add_scraped["address"]
                    except:
                        pass
            
            # Create business record
            business = {
                "name": company["name"],
                "city": company.get("city", ""),
                "tier": self._get_tier(company.get("city", "")),
                "type": company.get("role", "Distributor"),
                "website": website,
                "email": scraped.get("email"),
                "phone": scraped.get("phone"),
                "whatsapp": scraped.get("whatsapp"),
                "address": scraped.get("address"),
                "source": "curated_list",
                "priority_score": 15,  # High priority for curated companies
                "pages_scraped": len(scraped.get("pages_scraped", [])),
                "social_links": scraped.get("social_links", [])
            }
            
            results.append(business)
            
            # Rate limit between companies
            await asyncio.sleep(1)
        
        # Sort by whether we got contact info
        results.sort(key=lambda x: (bool(x.get("email")), bool(x.get("phone"))), reverse=True)
        
        print(f"[Curated List] Found contacts for {sum(1 for r in results if r.get('email') or r.get('phone'))}/{len(results)} companies")
        
        return results

    async def enrich_lead(self, lead: Dict) -> Dict:
        """
        Enrich a single lead by visiting its website.
        
        Args:
            lead: Dictionary with at least 'website' field
            
        Returns:
            Updated lead dictionary with contact info
        """
        website = lead.get("website", "")
        if not website:
            return lead
        
        # Ensure URL has scheme
        if not website.startswith("http"):
            website = "https://" + website
        
        scraped = await self.scrape_website_contacts(website, follow_contact_pages=True)
        
        # Update lead with scraped info (only if not already present)
        if scraped.get("email") and not lead.get("email"):
            lead["email"] = scraped["email"]
        if scraped.get("phone") and not lead.get("phone"):
            lead["phone"] = scraped["phone"]
        if scraped.get("whatsapp") and not lead.get("whatsapp"):
            lead["whatsapp"] = scraped["whatsapp"]
        if scraped.get("address") and not lead.get("address"):
            lead["address"] = scraped["address"]
        
        lead["enriched"] = True
        lead["pages_scraped"] = scraped.get("pages_scraped", [])
        
        return lead

    async def enrich_leads_batch(self, leads: List[Dict], max_concurrent: int = 3) -> List[Dict]:
        """
        Enrich multiple leads by visiting their websites.
        
        Args:
            leads: List of lead dictionaries
            max_concurrent: Max concurrent requests
            
        Returns:
            List of enriched leads
        """
        print(f"[Enrichment] Processing {len(leads)} leads...")
        
        enriched = []
        
        # Process in batches to be respectful
        for i in range(0, len(leads), max_concurrent):
            batch = leads[i:i+max_concurrent]
            
            tasks = [self.enrich_lead(lead.copy()) for lead in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for j, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    enriched.append(batch[j])
                else:
                    enriched.append(result)
            
            print(f"  Processed {min(i+max_concurrent, len(leads))}/{len(leads)} leads")
            
            # Rate limit between batches
            await asyncio.sleep(2)
        
        success_count = sum(1 for l in enriched if l.get("enriched") and (l.get("email") or l.get("phone")))
        print(f"[Enrichment] Successfully enriched {success_count}/{len(leads)} leads with contact info")
        
        return enriched

    async def _fetch_page_details(self, url: str) -> Dict:
        """Fetch additional details from a webpage."""
        details = {"email": None, "phone": None, "address": None, "whatsapp": None}
        try:
            client = await self._get_http_client()
            self._rate_limit()
            
            response = await client.get(url)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                text = soup.get_text(separator=" ", strip=True)
                
                # Extract contact info
                contact = self._extract_contact_info(text, soup)
                details.update(contact)
                
                # Extract address
                address = self._extract_address(text, soup)
                if address:
                    details["address"] = address
                        
        except Exception as e:
            pass
        return details

    async def _search_with_templates(self, templates: List[str], city: str, max_results: int = 5) -> List[Dict]:
        """Search using a list of templates."""
        results = []
        seen_urls = set()
        seen_names = set()
        
        ddgs = DDGS()
        
        for template in templates:
            if len(results) >= max_results:
                break
            
            query = template.format(city=city) if '{city}' in template else template
            
            try:
                self._rate_limit()
                search_results = list(ddgs.text(query, region="in-en", max_results=8))
                
                # Sort by URL priority
                search_results.sort(key=lambda x: self._get_url_priority(x.get("href", "")), reverse=True)
                
                for item in search_results:
                    if len(results) >= max_results:
                        break
                    
                    url = item.get("href", "")
                    title = item.get("title", "")
                    body = item.get("body", "")
                    
                    # Skip duplicates
                    if url in seen_urls:
                        continue
                    
                    # Check if valid business URL
                    if not self._is_business_url(url):
                        continue
                    
                    # Clean business name
                    name = self._clean_business_name(title)
                    if not name or len(name) < 3:
                        continue
                    
                    # Skip duplicate names
                    name_lower = name.lower()
                    if name_lower in seen_names:
                        continue
                    
                    seen_urls.add(url)
                    seen_names.add(name_lower)
                    
                    # Extract contact info
                    contact = self._extract_contact_info(body)
                    
                    # Determine business type
                    biz_type = self._extract_business_type(body + " " + title)
                    
                    # Determine source from URL
                    source = "web_search"
                    parsed_url = urlparse(url)
                    domain = parsed_url.netloc.lower()
                    if "indiamart" in domain:
                        source = "IndiaMART"
                    elif "tradeindia" in domain:
                        source = "TradeIndia"
                    elif "justdial" in domain:
                        source = "JustDial"
                    elif "linkedin" in domain:
                        source = "LinkedIn"
                    elif "sulekha" in domain:
                        source = "Sulekha"
                    elif "yellowpages" in domain:
                        source = "YellowPages"
                    
                    business = {
                        "name": name,
                        "city": city,
                        "tier": self._get_tier(city),
                        "type": biz_type,
                        "website": url,
                        "description": body[:400] if body else None,
                        "email": contact.get("email"),
                        "phone": contact.get("phone"),
                        "whatsapp": contact.get("whatsapp"),
                        "source": source,
                        "search_query": query,
                        "priority_score": self._get_url_priority(url)
                    }
                    
                    results.append(business)
                    
            except Exception as e:
                print(f"Search error for query '{query}': {e}")
                continue
        
        return results

    async def discover_businesses(self, city: str, limit: int = 10) -> List[Dict]:
        """
        Discover real businesses using comprehensive multi-source search.
        
        Implements strategies:
        1. Industry directories (IndiaMART, TradeIndia, JustDial)
        2. Google advanced search
        3. Manufacturer distributor lists
        4. Yellow pages & local directories
        
        Args:
            city: City name to search in
            limit: Maximum number of results to return
            
        Returns:
            List of discovered business dictionaries
        """
        all_results = []
        seen_names = set()
        
        # Calculate how many results to get from each strategy
        per_strategy = max(3, limit // 3)
        
        # Strategy 1: Industry Directories (highest priority)
        print(f"[Strategy 1] Searching industry directories for {city}...")
        directory_results = await self._search_with_templates(
            self.directory_search_templates[:6], city, per_strategy
        )
        all_results.extend(directory_results)
        
        # Strategy 2: Google Advanced Search
        print(f"[Strategy 2] Running advanced Google searches for {city}...")
        google_results = await self._search_with_templates(
            self.google_advanced_templates[:4], city, per_strategy
        )
        for r in google_results:
            if r["name"].lower() not in seen_names:
                all_results.append(r)
                seen_names.add(r["name"].lower())
        
        # Strategy 3: Manufacturer distributor lists
        print(f"[Strategy 3] Searching manufacturer distributor lists...")
        mfr_results = await self._search_with_templates(
            self.manufacturer_search_templates[:3], city, per_strategy // 2
        )
        for r in mfr_results:
            if r["name"].lower() not in seen_names:
                all_results.append(r)
                seen_names.add(r["name"].lower())
        
        # Strategy 4: Sports shops & related businesses
        print(f"[Strategy 4] Searching related sports shops for {city}...")
        sports_results = await self._search_with_templates(
            self.sports_shop_search_templates[:3], city, per_strategy // 2
        )
        for r in sports_results:
            if r["name"].lower() not in seen_names:
                all_results.append(r)
                seen_names.add(r["name"].lower())
        
        # Dedupe by name
        unique_results = []
        seen = set()
        for r in all_results:
            name_key = r["name"].lower()
            if name_key not in seen:
                seen.add(name_key)
                unique_results.append(r)
        
        # Sort by priority score
        unique_results.sort(key=lambda x: x.get("priority_score", 0), reverse=True)
        
        # Limit results
        results = unique_results[:limit]
        
        # Enrich top results with page scraping
        if results:
            print(f"[Enrichment] Fetching contact details for top {min(5, len(results))} results...")
            for i, biz in enumerate(results[:5]):
                try:
                    details = await self._fetch_page_details(biz["website"])
                    if details.get("email") and not biz.get("email"):
                        biz["email"] = details["email"]
                    if details.get("phone") and not biz.get("phone"):
                        biz["phone"] = details["phone"]
                    if details.get("whatsapp") and not biz.get("whatsapp"):
                        biz["whatsapp"] = details["whatsapp"]
                    if details.get("address"):
                        biz["address"] = details["address"]
                except Exception as e:
                    pass
        
        print(f"[Complete] Found {len(results)} unique businesses for {city}")
        return results

    async def discover_by_strategy(self, city: str, strategy: str, limit: int = 10) -> List[Dict]:
        """
        Discover businesses using a specific strategy.
        
        Args:
            city: City name
            strategy: One of 'directories', 'manufacturers', 'tradeshows', 
                     'linkedin', 'google', 'yellowpages', 'marketplaces', 'sports_shops',
                     'curated' (for curated list)
            limit: Maximum results
        """
        if strategy == "curated":
            return await self.discover_from_curated_list(city)
        
        templates_map = {
            "directories": self.directory_search_templates,
            "manufacturers": self.manufacturer_search_templates,
            "tradeshows": self.tradeshow_search_templates,
            "linkedin": self.linkedin_search_templates,
            "google": self.google_advanced_templates,
            "yellowpages": self.yellowpages_search_templates,
            "marketplaces": self.marketplace_search_templates,
            "sports_shops": self.sports_shop_search_templates,
        }
        
        templates = templates_map.get(strategy, self.directory_search_templates)
        return await self._search_with_templates(templates, city, limit)

    async def search_all_cities(self, limit_per_city: int = 5) -> List[Dict]:
        """Search for businesses in all configured cities."""
        all_results = []
        cities = self.get_all_cities()
        
        for city_info in cities:
            city = city_info["name"]
            print(f"\n{'='*50}")
            print(f"Searching {city}...")
            print(f"{'='*50}")
            results = await self.discover_businesses(city, limit_per_city)
            all_results.extend(results)
            await asyncio.sleep(1)  # Rate limiting between cities
        
        return all_results

    async def deep_search(self, city: str, limit: int = 20) -> List[Dict]:
        """
        Run a deep search using ALL strategies for maximum coverage.
        This is slower but finds more leads.
        """
        all_results = []
        seen_names = set()
        
        strategies = [
            ("Industry Directories", self.directory_search_templates),
            ("Manufacturer Lists", self.manufacturer_search_templates),
            ("Trade Shows", self.tradeshow_search_templates),
            ("LinkedIn", self.linkedin_search_templates),
            ("Google Advanced", self.google_advanced_templates),
            ("Yellow Pages", self.yellowpages_search_templates),
            ("Marketplaces", self.marketplace_search_templates),
            ("Sports Shops", self.sports_shop_search_templates),
        ]
        
        per_strategy = max(3, limit // len(strategies))
        
        for strategy_name, templates in strategies:
            print(f"\n[{strategy_name}] Searching...")
            results = await self._search_with_templates(templates, city, per_strategy)
            
            for r in results:
                name_key = r["name"].lower()
                if name_key not in seen_names:
                    r["discovery_strategy"] = strategy_name
                    all_results.append(r)
                    seen_names.add(name_key)
            
            print(f"  Found {len(results)} results, {len(all_results)} unique total")
        
        # Sort by priority
        all_results.sort(key=lambda x: x.get("priority_score", 0), reverse=True)
        
        # Enrich top results
        print(f"\n[Enrichment] Fetching details for top {min(10, len(all_results))} results...")
        for biz in all_results[:10]:
            try:
                details = await self._fetch_page_details(biz["website"])
                if details.get("email") and not biz.get("email"):
                    biz["email"] = details["email"]
                if details.get("phone") and not biz.get("phone"):
                    biz["phone"] = details["phone"]
                if details.get("whatsapp"):
                    biz["whatsapp"] = details["whatsapp"]
                if details.get("address"):
                    biz["address"] = details["address"]
            except:
                pass
        
        return all_results[:limit]

    def get_curated_companies(self) -> List[Dict]:
        """Return the curated list of known pickleball companies."""
        return self.curated_companies

    async def close(self):
        """Close HTTP client."""
        if self.http_client:
            await self.http_client.aclose()
