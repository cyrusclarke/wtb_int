#!/usr/bin/env python3
"""
NFC Card Categorizer for WTB Project
Scan cards and automatically add them to FIRE, ELECTRICITY, WATER, or LAND categories
"""

import serial
import time

# Serial port from Arduino
PORT = "/dev/tty.usbmodem101"
BAUD = 115200

# Storage for categorized cards
categories = {
    "FIRE": [],
    "ELECTRICITY": [],
    "WATER": [],
    "LAND": [],
}

category_names = {
    "1": "FIRE",
    "2": "ELECTRICITY",
    "3": "WATER",
    "4": "LAND",
}

def print_header():
    print("\n" + "="*60)
    print("       NFC CARD CATEGORIZER - WTB Project")
    print("="*60)

def print_current_counts():
    print("\n📊 Current card counts:")
    for cat_name, uids in categories.items():
        print(f"   {cat_name:12} : {len(uids)} cards")

def select_category():
    print("\n🎯 Select category to scan:")
    print("   1 - FIRE 🔥")
    print("   2 - ELECTRICITY ⚡")
    print("   3 - WATER 💧")
    print("   4 - LAND 🌍")
    print("   Q - Quit and generate code")
    
    choice = input("\nEnter choice (1-4 or Q): ").strip().upper()
    
    if choice == "Q":
        return None
    
    if choice in category_names:
        return category_names[choice]
    
    print("❌ Invalid choice. Try again.")
    return select_category()

def scan_cards_for_category(ser, category):
    print(f"\n🔍 Scanning {category} cards...")
    print(f"   Scan your {category} cards now.")
    print(f"   Press ENTER when done with this category.\n")
    
    seen_uids = set()
    
    while True:
        # Check for keyboard input (Enter to finish)
        import sys
        import select
        
        if select.select([sys.stdin], [], [], 0)[0]:
            sys.stdin.readline()
            break
        
        # Check for serial data
        try:
            if ser.in_waiting > 0:
                line = ser.readline().decode().strip()
                
                if line.startswith("SCAN,"):
                    uid = line.split(",")[1].strip().upper()
                    
                    if uid not in seen_uids:
                        seen_uids.add(uid)
                        categories[category].append(uid)
                        print(f"   ✅ Added: {uid} ({len(categories[category])} total)")
                    else:
                        print(f"   ♻️  Already scanned: {uid}")
        except Exception as e:
            pass
        
        time.sleep(0.1)
    
    print(f"\n✨ Done! Added {len(seen_uids)} new {category} cards.")

def generate_code():
    print("\n" + "="*60)
    print("📋 GENERATED CODE - Copy this into game_mode.py:")
    print("="*60 + "\n")
    
    print("RESOURCE_CARDS = {")
    for cat_name in ["FIRE", "ELECTRICITY", "WATER", "LAND"]:
        uids = categories[cat_name]
        print(f'    "{cat_name}": [')
        for uid in uids:
            print(f'        "{uid}",')
        print("    ],")
    print("}")
    
    print("\n" + "="*60)
    print(f"\n✅ Total cards scanned: {sum(len(uids) for uids in categories.values())}")
    for cat_name, uids in categories.items():
        print(f"   {cat_name:12} : {len(uids)} cards")
    print("\n")

def main():
    print_header()
    
    print("\n🔌 Connecting to Arduino...")
    
    try:
        ser = serial.Serial(PORT, BAUD, timeout=0.1)
        time.sleep(1)  # Wait for connection
        ser.reset_input_buffer()
        print(f"✅ Connected to {PORT}\n")
        
        while True:
            print_current_counts()
            category = select_category()
            
            if category is None:
                # User chose to quit
                break
            
            scan_cards_for_category(ser, category)
        
        # Generate the code
        generate_code()
        
        ser.close()
        print("👋 Goodbye!\n")
        
    except serial.SerialException as e:
        print(f"\n❌ Could not connect to {PORT}")
        print(f"   Error: {e}")
        print(f"\n💡 Tips:")
        print(f"   1. Close Arduino Serial Monitor if it's open")
        print(f"   2. Make sure Arduino is connected")
        print(f"   3. Upload nfc_lcd_input.ino to Arduino first")
        print(f"   4. Check the port with: ls /dev/tty.usb*\n")
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        generate_code()

if __name__ == "__main__":
    main()

