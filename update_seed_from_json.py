#!/usr/bin/env python
"""
Update seed_database() and update_menu_with_new_items() functions 
with current menu items from JSON export.
"""
import json
import re

# Read the exported menu data
with open('menu_export_20251220_064159.json', 'r', encoding='utf-8') as f:
    menu_data = json.load(f)

# Create a mapping of name to image_url for items with custom images
custom_images = {}
for item in menu_data:
    name = item['name']
    image_url = item.get('image_url', '')
    # Only include items with custom uploaded images (not default Unsplash URLs)
    if image_url and image_url.startswith('/static/images/menu/'):
        custom_images[name] = image_url

print(f"Found {len(custom_images)} items with custom images:")
for name, url in sorted(custom_images.items()):
    print(f"  - {name}: {url}")

print("\n" + "=" * 80)
print("To update seed data, manually replace these items in seed_database()")
print("and update_menu_with_new_items() functions:")
print("=" * 80)

# Generate replacement instructions
for name, image_url in sorted(custom_images.items()):
    # Find the item in menu_data to get full details
    item = next((i for i in menu_data if i['name'] == name), None)
    if item:
        description = item['description'].replace("'", "\\'")
        price = item['price']
        category = item['category']
        print(f"\nReplace:")
        print(f"  ('{name}', '{description}', {price}, '{category}', 'OLD_URL'),")
        print(f"With:")
        print(f"  ('{name}', '{description}', {price}, '{category}', '{image_url}'),")
