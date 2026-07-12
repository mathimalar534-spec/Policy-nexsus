import os
import json
import csv

# Directories
data_dir = "sample_data"

def convert_json_to_csv():
    print("Synchronizing JSON files to CSV format using standard csv library...")
    for name in ["policy_metadata", "obligation_extracts_labels", "findings_labels"]:
        json_path = os.path.join(data_dir, f"{name}.json")
        csv_path = os.path.join(data_dir, f"{name}.csv")
        
        if os.path.exists(json_path):
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            if not data:
                print(f"Empty data in {json_path}. Skipping.")
                continue
                
            # Collect union of all headers across all rows
            all_keys = set()
            for row in data:
                all_keys.update(row.keys())
            headers = list(all_keys)
            
            with open(csv_path, "w", encoding="utf-8", newline="") as csv_f:
                writer = csv.DictWriter(csv_f, fieldnames=headers)
                writer.writeheader()
                writer.writerows(data)
                
            print(f"Successfully converted {json_path} -> {csv_path}")
        else:
            print(f"Warning: {json_path} not found.")

if __name__ == "__main__":
    convert_json_to_csv()
