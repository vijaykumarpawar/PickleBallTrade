import json
import os

class SearchEngine:
    def __init__(self):
        config_path = "agent/config/cities.json"
        if os.path.exists(config_path):
            with open(config_path) as f:
                self.cities_config = json.load(f)
        else:
            self.cities_config = {"tier_1": [], "tier_2": [], "tier_3": []}

    def get_all_cities(self):
        cities = []
        for tier, city_list in self.cities_config.items():
            for city in city_list:
                cities.append({"name": city, "tier": tier})
        return cities

    async def discover_businesses(self, city, limit=10):
        tier = "tier_2"
        for t, cities in self.cities_config.items():
            if city in cities:
                tier = t
                break
        results = []
        for i in range(min(limit, 5)):
            results.append({
                "name": f"Pickleball {city} Business {i+1}",
                "city": city,
                "tier": tier,
                "website": f"https://pickleball{city.lower()}{i+1}.com",
                "source": "discovery"
            })
        return results
