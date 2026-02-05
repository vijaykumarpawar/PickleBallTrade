import json
import os
import re
import asyncio
from typing import List, Dict, Optional
from duckduckgo_search import DDGS
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
        
        self.search_templates = [
            "{city} pickleball equipment importer",
            "{city} pickleball paddle distributor",
            "{city} pickleball sports goods wholesale",
            "{city} pickleball equipment dealer",
            "pickleball equipment supplier {city} India",
            "{city} sports equipment importer pickleball",
            "pickleball wholesale distributor {city}",
            "{city} racket sports equipment dealer",
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
        if emails:
            contact["email"] = emails[0]
        
        # Phone patterns for India
        phone_patterns = [
            r"\+91[\s-]?\d{10}",
            r"\+91[\s-]?\d{5}[\s-]?\d{5}",
            r"0\d{2,4}[\s-]?\d{6,8}",
            r"\d{10}",
        ]
        for pattern in phone_patterns:
            phones = re.findall(pattern, text)
            if phones:
                contact["phone"] = phones[0].strip()
                break
        
        return contact

    def _clean_business_name(self, title: str) -> str:
        """Clean up business name from search title."""
        remove_patterns = [
            r"\s*[-|].*$",
            r"\s*\|.*$",
            r"\s*:.*$",
            r"\bPvt\.?\s*Ltd\.?\b",
            r"\bPrivate\s*Limited\b",
            r"\bLLP\b",
            r"\bInc\.?\b",
        ]
        name = title
        for pattern in remove_patterns:
            name = re.sub(pattern, "", name, flags=re.IGNORECASE)
        return name.strip()[:100]

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
                    if any(kw in tag_text.lower() for kw in ["address", "located", "office"]):
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
        
        with DDGS() as ddgs:
            for template in self.search_templates:
                if len(results) >= limit:
                    break
                
                query = template.format(city=city)
                try:
                    search_results = list(ddgs.text(query, region="in-en", max_results=5))
                    
                    for item in search_results:
                        if len(results) >= limit:
                            break
                        
                        url = item.get("href", "")
                        title = item.get("title", "")
                        body = item.get("body", "")
                        
                        # Skip duplicates
                        if url in seen_urls:
                            continue
                        
                        # Skip social media and marketplace sites
                        skip_domains = ["youtube.com", "facebook.com", "twitter.com", 
                                       "instagram.com", "linkedin.com", "wikipedia.org",
                                       "amazon", "flipkart", "myntra", "snapdeal"]
                        if any(domain in url.lower() for domain in skip_domains):
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
                        
                        business = {
                            "name": name,
                            "city": city,
                            "tier": tier,
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
