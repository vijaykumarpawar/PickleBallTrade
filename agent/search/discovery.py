import json
import os
import re
import asyncio
from typing import List, Dict, Optional
from ddgs import DDGS
import httpx
from bs4 import BeautifulSoup


class SearchEngine:
    def __init__(self):
        config_path = "agent/config/cities.json"
        if os.path.exists(config_path):
            with open(config_path) as f:
                self.cities_config = json.load(f)
        else:
            self.cities_config = {"tier_1": [], "tier_2": [], "tier_3": []}
        
        # Prioritize business directories in search queries
        self.search_templates = [
            "site:indiamart.com pickleball {city}",
            "site:tradeindia.com pickleball {city}",
            "site:justdial.com pickleball {city}",
            "site:exportersindia.com pickleball",
            "{city} pickleball equipment manufacturer contact",
            "{city} pickleball paddle wholesale dealer",
            "{city} pickleball importer distributor",
            "pickleball equipment supplier {city} India contact",
            "{city} sports goods dealer pickleball paddle",
            "buy pickleball paddles wholesale {city}",
        ]
        
        # Domains to prioritize (business directories)
        self.priority_domains = [
            "indiamart.com", "tradeindia.com", "justdial.com",
            "exportersindia.com", "yellowpages.co.in", "sulekha.com",
            "tradexcel.in", "go4worldbusiness.com"
        ]
        
        # Domains to skip
        self.skip_domains = [
            "youtube.com", "facebook.com", "twitter.com", "x.com",
            "instagram.com", "linkedin.com", "wikipedia.org",
            "amazon", "flipkart", "myntra", "snapdeal", "meesho",
            "news", "thehindu", "indiatimes", "ndtv", "india.com",
            "bbc.com", "cnn.com", "reuters", "bloomberg"
        ]
        
        self.http_client = None

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
        """Extract email and phone from text."""
        contact = {}
        
        # Email pattern
        email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
        emails = re.findall(email_pattern, text)
        # Filter out common non-business emails
        filtered_emails = [e for e in emails if not any(
            x in e.lower() for x in ['example', 'test', 'noreply', 'no-reply', 'admin@', 'support@']
        )]
        if filtered_emails:
            contact["email"] = filtered_emails[0]
        
        # Phone patterns for India
        phone_patterns = [
            r"\+91[\s-]?\d{10}",
            r"\+91[\s-]?\d{5}[\s-]?\d{5}",
            r"0\d{2,4}[\s-]?\d{6,8}",
            r"(?<!\d)\d{10}(?!\d)",  # 10 digit number not surrounded by digits
        ]
        for pattern in phone_patterns:
            phones = re.findall(pattern, text)
            if phones:
                phone = phones[0].strip()
                # Validate it looks like a phone number
                if len(re.sub(r'\D', '', phone)) >= 10:
                    contact["phone"] = phone
                    break
        
        return contact

    def _clean_business_name(self, title: str) -> str:
        """Clean up business name from search title."""
        # Remove common suffixes and website names
        remove_patterns = [
            r"\s*[-|–].*$",
            r"\s*\|.*$",
            r"\s*::.*$",
            r"\s*-\s*IndiaMART.*$",
            r"\s*-\s*TradeIndia.*$",
            r"\s*-\s*JustDial.*$",
            r"\s*,\s*\w+\s*$",  # Remove trailing city names
            r"\bPvt\.?\s*Ltd\.?\b",
            r"\bPrivate\s*Limited\b",
            r"\bLLP\b",
            r"\bInc\.?\b",
        ]
        name = title
        for pattern in remove_patterns:
            name = re.sub(pattern, "", name, flags=re.IGNORECASE)
        return name.strip()[:100]

    def _is_business_url(self, url: str) -> bool:
        """Check if URL is likely a business listing."""
        url_lower = url.lower()
        
        # Skip non-business domains
        if any(domain in url_lower for domain in self.skip_domains):
            return False
        
        # Prioritize business directories
        if any(domain in url_lower for domain in self.priority_domains):
            return True
        
        # Check for business-like patterns
        business_patterns = [
            r'/company/', r'/supplier/', r'/manufacturer/',
            r'/dealer/', r'/distributor/', r'/seller/',
            r'/shop/', r'/store/', r'/products/'
        ]
        if any(re.search(pattern, url_lower) for pattern in business_patterns):
            return True
        
        return True  # Allow other URLs but they'll be lower priority

    def _get_url_priority(self, url: str) -> int:
        """Get priority score for URL (higher = better)."""
        url_lower = url.lower()
        
        # Highest priority for business directories
        if any(domain in url_lower for domain in self.priority_domains):
            return 10
        
        # Medium priority for business-like URLs
        if any(pattern in url_lower for pattern in ['/company/', '/supplier/', '/manufacturer/']):
            return 5
        
        return 1

    async def _fetch_page_details(self, url: str) -> Dict:
        """Fetch additional details from a webpage."""
        details = {"email": None, "phone": None, "address": None}
        try:
            if not self.http_client:
                self.http_client = httpx.AsyncClient(timeout=10.0, follow_redirects=True)
            
            response = await self.http_client.get(url, headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            })
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                text = soup.get_text(separator=" ", strip=True)
                
                # Extract contact info
                contact = self._extract_contact_info(text)
                details.update(contact)
                
                # Try to find address
                for tag in soup.find_all(["address", "p", "div", "span"]):
                    tag_text = tag.get_text(strip=True)
                    if any(kw in tag_text.lower() for kw in ["address", "located", "office", "warehouse"]):
                        if len(tag_text) > 20 and len(tag_text) < 200:
                            details["address"] = tag_text
                            break
        except Exception as e:
            pass
        return details

    async def discover_businesses(self, city: str, limit: int = 10) -> List[Dict]:
        """
        Discover real businesses using DuckDuckGo web search.
        
        Args:
            city: City name to search in
            limit: Maximum number of results to return
            
        Returns:
            List of discovered business dictionaries
        """
        tier = self._get_tier(city)
        results = []
        seen_urls = set()
        seen_names = set()
        
        ddgs = DDGS()
        
        for template in self.search_templates:
            if len(results) >= limit:
                break
            
            query = template.format(city=city)
            try:
                search_results = list(ddgs.text(query, region="in-en", max_results=10))
                
                # Sort by URL priority
                search_results.sort(key=lambda x: self._get_url_priority(x.get("href", "")), reverse=True)
                
                for item in search_results:
                    if len(results) >= limit:
                        break
                    
                    url = item.get("href", "")
                    title = item.get("title", "")
                    body = item.get("body", "")
                    
                    # Skip duplicates
                    if url in seen_urls:
                        continue
                    
                    # Check if it's a valid business URL
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
                    
                    # Extract contact info from snippet
                    contact = self._extract_contact_info(body)
                    
                    # Determine business type from content
                    biz_type = "Unknown"
                    body_lower = body.lower()
                    if "manufacturer" in body_lower:
                        biz_type = "Manufacturer"
                    elif "distributor" in body_lower:
                        biz_type = "Distributor"
                    elif "importer" in body_lower:
                        biz_type = "Importer"
                    elif "wholesale" in body_lower or "wholesaler" in body_lower:
                        biz_type = "Wholesaler"
                    elif "retailer" in body_lower or "shop" in body_lower:
                        biz_type = "Retailer"
                    elif "dealer" in body_lower:
                        biz_type = "Dealer"
                    elif "supplier" in body_lower:
                        biz_type = "Supplier"
                    
                    business = {
                        "name": name,
                        "city": city,
                        "tier": tier,
                        "type": biz_type,
                        "website": url,
                        "description": body[:300] if body else None,
                        "email": contact.get("email"),
                        "phone": contact.get("phone"),
                        "source": "web_search",
                        "search_query": query
                    }
                    
                    results.append(business)
                    
            except Exception as e:
                print(f"Search error for query '{query}': {e}")
                continue
        
        # Enrich first few results with page scraping
        if results:
            enriched = []
            for biz in results[:min(5, len(results))]:
                try:
                    details = await self._fetch_page_details(biz["website"])
                    if details.get("email") and not biz.get("email"):
                        biz["email"] = details["email"]
                    if details.get("phone") and not biz.get("phone"):
                        biz["phone"] = details["phone"]
                    if details.get("address"):
                        biz["address"] = details["address"]
                except:
                    pass
                enriched.append(biz)
            
            results = enriched + results[5:]
        
        return results

    async def search_all_cities(self, limit_per_city: int = 5) -> List[Dict]:
        """Search for businesses in all configured cities."""
        all_results = []
        cities = self.get_all_cities()
        
        for city_info in cities:
            city = city_info["name"]
            results = await self.discover_businesses(city, limit_per_city)
            all_results.extend(results)
        
        return all_results

    async def close(self):
        """Close HTTP client."""
        if self.http_client:
            await self.http_client.aclose()
