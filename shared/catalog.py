import csv
import os

class CardDatabase:
    """
    Loads and stores the shared out-of-band card catalog in memory.
    """
    _catalog = {}

    @classmethod
    def load_catalog(cls, master_csv_path=None, instances_csv_path=None):
        """
        Reads the exported Google Sheets and builds the protocol-ready dictionary.
        """
        import os
        import csv
        
        base_dir = os.path.dirname(__file__)

        if master_csv_path is None:
            master_csv_path = os.path.join(base_dir, "data", "master_list.csv")
        if instances_csv_path is None:
            instances_csv_path = os.path.join(base_dir, "data", "instances.csv")

        if not os.path.exists(master_csv_path) or not os.path.exists(instances_csv_path):
            print(f"Warning: CSV files not found. Checked:\n{master_csv_path}\n{instances_csv_path}")
            return

        master_data = {}
        
        # Parse Master List for base stats
        with open(master_csv_path, mode='r', encoding='utf-8-sig') as master_file:
            # Skip Row 1
            next(master_file) 
            
            reader = csv.DictReader(master_file)
            for row in reader:
                card_name = row.get("Card Name", "").strip()
                if not card_name:
                    continue # Skip empty rows
                    
                master_data[card_name] = {
                    "base_id": row.get("Card ID Base"),
                    "type": row.get("Card Type"),
                    "subtype": row.get("Subtype"),
                    "color": row.get("Color"),
                    "cmc": int(row.get("CMC", 0) or 0),
                    "power": int(row.get("Power", 0) if row.get("Power", "").isdigit() else 0),
                    "toughness": int(row.get("Toughness", 0) if row.get("Toughness", "").isdigit() else 0),
                    "effect": row.get("Simplified Effect")
                }

        # Parse instances list and map the master stats
        with open(instances_csv_path, mode='r', encoding='utf-8-sig') as instances_file:
            # Skip Row 1
            next(instances_file)
            
            reader = csv.DictReader(instances_file)
            for row in reader:
                protocol_id = row.get("card_id (protocol reference)", "").strip()
                card_name = row.get("Card Name", "").strip()
                
                if card_name in master_data and protocol_id:
                    cls._catalog[protocol_id] = master_data[card_name].copy()
                    cls._catalog[protocol_id]["protocol_id"] = protocol_id

    @classmethod
    def get_card(cls, card_id: str) -> dict:
        """Retrieves card data by its ID (e.g., 'mountain_001')."""
        return cls._catalog.get(card_id, {})

if __name__ == "__main__":
    import pprint 
    
    print("Loading catalog...")
    CardDatabase.load_catalog() # The dynamic defaults handle the paths now

    print(f"Total card instances loaded: {len(CardDatabase._catalog)}")

    print("\n--- Testing a Land Card (mountain_001) ---")
    mountain = CardDatabase.get_card("white_knight_002")
    pprint.pprint(mountain)