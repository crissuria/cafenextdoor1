#!/usr/bin/env python
"""
Export current menu items from local database to update seed data.
This script reads your current database and outputs the menu items
in a format that can be used to update the seed_database function.
"""
import sqlite3
import os
import json
from datetime import datetime

# Database path
DATABASE_DIR = 'database'
DATABASE_PATH = os.path.join(DATABASE_DIR, 'cafe.db')

def export_menu_items():
    """Export all menu items from the database."""
    if not os.path.exists(DATABASE_PATH):
        print(f"ERROR: Database not found at: {DATABASE_PATH}")
        print("Make sure you've run the app at least once to create the database.")
        return
    
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get all menu items
        cursor.execute('SELECT * FROM menu_items ORDER BY category, name')
        items = cursor.fetchall()
        
        if not items:
            print("ERROR: No menu items found in database.")
            conn.close()
            return
        
        print(f"OK: Found {len(items)} menu items\n")
        print("=" * 80)
        print("MENU ITEMS EXPORT")
        print("=" * 80)
        print("\nCopy this data to update seed_database() function:\n")
        
        # Group by category
        categories = {}
        for item in items:
            category = item['category'] if isinstance(item, dict) else item[4]
            if category not in categories:
                categories[category] = []
            categories[category].append(item)
        
        # Output in seed_database format
        output_lines = []
        for category in sorted(categories.keys()):
            output_lines.append(f"        # {category}")
            for item in categories[category]:
                if isinstance(item, dict):
                    name = item['name']
                    description = item['description'] or ''
                    price = item['price']
                    image_url = item.get('image_url', '') or ''
                else:
                    name = item[1]
                    description = item[2] or ''
                    price = item[3]
                    image_url = item[5] if len(item) > 5 else ''
                
                # Escape quotes in strings
                description = description.replace("'", "\\'")
                image_url = image_url.replace("'", "\\'")
                
                output_lines.append(f"        ('{name}', '{description}', {price}, '{category}', '{image_url}'),")
            output_lines.append("")
        
        print("\n".join(output_lines))
        
        # Also create a JSON export
        json_data = []
        for item in items:
            if isinstance(item, dict):
                json_data.append({
                    'name': item['name'],
                    'description': item['description'],
                    'price': item['price'],
                    'category': item['category'],
                    'image_url': item.get('image_url', ''),
                    'is_available': item.get('is_available', 1)
                })
            else:
                json_data.append({
                    'name': item[1],
                    'description': item[2],
                    'price': item[3],
                    'category': item[4],
                    'image_url': item[5] if len(item) > 5 else '',
                    'is_available': item[6] if len(item) > 6 else 1
                })
        
        # Save to JSON file
        json_filename = f'menu_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
        
        print("\n" + "=" * 80)
        print(f"OK: JSON export saved to: {json_filename}")
        print("=" * 80)
        
        # Show items with custom images (different from default)
        print("\nItems with custom images (different from default):")
        print("-" * 80)
        default_images = {
            'Cold Brew': 'https://images.unsplash.com/photo-1509042239860-f550ce710b93?w=800&h=600&fit=crop'
        }
        
        custom_count = 0
        for item in items:
            if isinstance(item, dict):
                name = item['name']
                image_url = item.get('image_url', '') or ''
            else:
                name = item[1]
                image_url = item[5] if len(item) > 5 else ''
            
            if name in default_images and image_url != default_images[name] and image_url:
                print(f"  • {name}:")
                print(f"    Old: {default_images[name]}")
                print(f"    New: {image_url}")
                custom_count += 1
        
        if custom_count == 0:
            print("  (No custom images detected)")
        
        conn.close()
        
    except Exception as e:
        print(f"ERROR: Error exporting menu items: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    export_menu_items()
