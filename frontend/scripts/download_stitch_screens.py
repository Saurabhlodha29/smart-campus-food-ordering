import json, os, requests, pathlib

# Load the screens JSON output from the MCP list step
json_path = r"C:/Users/saura/.gemini/antigravity-ide/brain/5ff6ee88-fbe9-4d21-84a4-ac028ddcfdef/.system_generated/steps/179/output.txt"
with open(json_path, "r", encoding="utf-8") as f:
    data = json.load(f)

screens = data.get("screens", [])

# Titles we need (spaces removed for file naming)
TARGET_TITLES = {"MyOrders", "Notifications", "StudentProfile", "MyPenalties"}

# Base directory to store downloaded HTML files
base_dir = pathlib.Path(r"C:/Users/saura/OneDrive/Desktop/AntiGravity Project/smart-campus-food-ordering/frontend/tmp/stitch_screens")
base_dir.mkdir(parents=True, exist_ok=True)

for screen in screens:
    title_raw = screen.get("title", "unknown")
    title = title_raw.replace(" ", "")
    if title not in TARGET_TITLES:
        continue
    html_info = screen.get("htmlCode", {})
    url = html_info.get("downloadUrl")
    if not url:
        continue
    resp = requests.get(url)
    if resp.status_code != 200:
        print(f"Failed to download {title}: {resp.status_code}")
        continue
    safe_name = "".join(c for c in title if c.isalnum() or c in "_-")
    out_path = base_dir / f"{safe_name}.html"
    out_path.write_bytes(resp.content)
    print(f"Saved {title} to {out_path}")

print("All targeted downloads completed.")
