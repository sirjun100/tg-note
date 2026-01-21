#!/usr/bin/env python3
"""
Joplin Folder Discovery Script
Maps Joplin folders and saves configuration.
"""

import json
import requests
import sys

def discover_folders():
    """Discover all Joplin folders and create mapping"""
    try:
        response = requests.get("http://localhost:41184/folders", timeout=10)
        if response.status_code != 200:
            print(f"Error: Joplin API returned {response.status_code}")
            sys.exit(1)

        folders = response.json()
        folder_map = {}

        print("Available Joplin folders:")
        for folder in folders:
            title = folder.get('title', 'Untitled')
            folder_id = folder['id']
            folder_map[title] = folder_id
            print(f"  {title} -> {folder_id}")

        # Save to config
        config = {"joplin_folders": folder_map}
        with open("joplin_config.json", "w") as f:
            json.dump(config, f, indent=2)

        print("\n✅ Saved folder mapping to joplin_config.json")
        return folder_map

    except requests.RequestException as e:
        print(f"Error connecting to Joplin: {e}")
        print("Make sure Joplin is running with Web Clipper enabled")
        sys.exit(1)

if __name__ == "__main__":
    print("🔍 Discovering Joplin folders...")
    discover_folders()