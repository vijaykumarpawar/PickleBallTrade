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
10. Data enrichment & verification
"""
import json
import os
import re
import asyncio
from typing import List, Dict, Optional, Set
from ddgs import DDGS
import httpx
from bs4 import BeautifulSoup
from urllib.parse import quote_plus, urlparse
import time


class SearchEngine:
    def __init__(self):
        config_path = "agent/config/cities.json"
        if os.path.exists(config_path):
            with open(config_path) as f:
                self.cities_config = json.load(f)
        else:
            self.cities_config = {"tier_1": [], "tier_2": [], "tier_3": []}
        
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
            "amazon.in", "amazon.com", "flipkart.com", "myntra.com",
            "snapdeal.com", "meesho.com", "ajio.com",
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

    def _extract_contact_info(self, text: str) -> Dict:
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
                    'support@', 'info@example', 'email@', 'your@', 'name@'
                ])
            ]
            if filtered_emails:
                contact["email"] = filtered_emails[0]
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
        
        # Try to extract WhatsApp number specifically
        whatsapp_patterns = [
            r"whatsapp[\s:]*\+?[\d\s.-]{10,15}",
            r"wa[\s:]*\+?[\d\s.-]{10,15}",
            r"📱[\s:]*\+?[\d\s.-]{10,15}",
        ]
        
        for pattern in whatsapp_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                wa_num = re.sub(r'[^\d+]', '', matches[0])
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

    async def _fetch_page_details(self, url: str) -> Dict:
        """Fetch additional details from a webpage."""
        details = {"email": None, "phone": None, "address": None, "whatsapp": None}
        try:
            if not self.http_client:
                self.http_client = httpx.AsyncClient(
                    timeout=10.0, 
                    follow_redirects=True,
                    limits=httpx.Limits(max_connections=10)
                )
            
            self._rate_limit()
            
            response = await self.http_client.get(url, headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            })
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                text = soup.get_text(separator=" ", strip=True)
                
                # Extract contact info
                contact = self._extract_contact_info(text)
                details.update(contact)
                
                # Try to find address
                address_patterns = [
                    r"address[\s:]+([^,\n]{20,150})",
                    r"located at[\s:]+([^,\n]{20,150})",
                    r"office[\s:]+([^,\n]{20,150})",
                ]
                
                for pattern in address_patterns:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        details["address"] = match.group(1).strip()[:200]
                        break
                
                # Also check specific HTML elements
                for tag in soup.find_all(["address", "div", "span"], class_=re.compile(r"address|location|contact", re.I)):
                    tag_text = tag.get_text(strip=True)
                    if 20 < len(tag_text) < 200 and any(x in tag_text.lower() for x in ["india", "road", "street", "nagar"]):
                        details["address"] = tag_text
                        break
                        
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
                     'linkedin', 'google', 'yellowpages', 'marketplaces', 'sports_shops'
            limit: Maximum results
        """
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

    async def close(self):
        """Close HTTP client."""
        if self.http_client:
            await self.http_client.aclose()
