from typing import Dict

class EntityClassifier:
    def __init__(self):
        self.rules = {
            "Importer": ["import", "trading", "international"],
            "Dealer": ["dealer", "distributor", "wholesale"],
            "Academy": ["academy", "training", "coaching", "school"],
            "Retailer": ["shop", "store", "retail", "mart"]
        }
        self.priority_map = {"tier_1": "high", "tier_2": "medium", "tier_3": "low"}

    def classify(self, entity: Dict) -> Dict:
        name = entity.get("name", "").lower()
        entity_type = "Unknown"
        for etype, keywords in self.rules.items():
            if any(kw in name for kw in keywords):
                entity_type = etype
                break
        tier = entity.get("tier", "tier_2")
        priority = self.priority_map.get(tier, "medium")
        if entity_type in ["Importer", "Dealer"]:
            priority = "high"
        entity["type"] = entity_type
        entity["priority"] = priority
        return entity
