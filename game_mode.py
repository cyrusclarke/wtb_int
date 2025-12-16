#! WTB integrated version 15dec October 2025 Cyrus Clarke - 4 player mode


import serial
import serial.tools.list_ports
import threading
from datetime import datetime
import pygame
import uuid
import sys
import select
import time
import json
import os
import re
from onchain import trigger_transaction  # must be defined

# Configuration file to remember ports
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(SCRIPT_DIR, "port_config.json")
SOUNDS_DIR = os.path.join(SCRIPT_DIR, "sounds")
BAUD = 115200

def get_available_ports():
    """Get list of available serial ports with Arduino devices."""
    ports = serial.tools.list_ports.comports()
    arduino_ports = []
    for port in ports:
        # Look for Arduino or USB serial devices
        if 'usbmodem' in port.device or 'usbserial' in port.device or 'Arduino' in str(port.description):
            arduino_ports.append({
                'device': port.device,
                'description': port.description,
                'hwid': port.hwid
            })
    return arduino_ports

def load_port_config():
    """Load previously saved port configuration."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except:
            return None
    return None

def save_port_config(port1, port2):
    """Save port configuration for next time."""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump({'PORT1': port1, 'PORT2': port2}, f)
        print(f"✓ Port configuration saved to {CONFIG_FILE}")
    except Exception as e:
        print(f"Warning: Could not save port config: {e}")

def extract_port_number(device_path):
    """Extract numeric value from port path (e.g., '101' from '/dev/tty.usbmodem101')."""
    # Look for number after "usbmodem" or "usbserial"
    match = re.search(r'(usbmodem|usbserial)(\d+)', device_path)
    if match:
        return int(match.group(2))
    # Fallback: extract all numbers and use the last one
    numbers = re.findall(r'\d+', device_path)
    if numbers:
        return int(numbers[-1])
    return 999999  # If no number found, put it last

def select_ports():
    """Auto-detect or interactively select the two Arduino ports."""
    available = get_available_ports()
    
    if len(available) < 2:
        print(f"❌ Error: Found only {len(available)} Arduino port(s). Need 2 readers.")
        if available:
            for i, p in enumerate(available, 1):
                print(f"   {i}. {p['device']} - {p['description']}")
        sys.exit(1)
    
    # Sort ports by numeric value (lower number = Reader 1)
    available.sort(key=lambda p: extract_port_number(p['device']))
    
    # Try to load saved configuration
    config = load_port_config()
    if config:
        port1 = config.get('PORT1')
        port2 = config.get('PORT2')
        
        # Check if saved ports are still available
        available_devices = [p['device'] for p in available]
        if port1 in available_devices and port2 in available_devices:
            # Verify Reader 1 has lower number than Reader 2, swap if needed
            num1 = extract_port_number(port1)
            num2 = extract_port_number(port2)
            if num1 > num2:
                print("⚠️ Correcting port assignment (Reader 1 must have lower number)...")
                port1, port2 = port2, port1
                save_port_config(port1, port2)  # Save corrected config
            
            print(f"✓ Using saved port configuration:")
            print(f"   Reader 1: {port1}")
            print(f"   Reader 2: {port2}")
            return port1, port2
        else:
            print("⚠️ Saved ports not available, need to reconfigure...")
    
    # Interactive selection
    print("\n🔌 Available Arduino ports (sorted by port number):")
    for i, p in enumerate(available, 1):
        print(f"   {i}. {p['device']} - {p['description']}")
    
    if len(available) == 2:
        print("\n✓ Auto-selecting the 2 available ports (lower number = Reader 1)...")
        port1 = available[0]['device']  # Lower number
        port2 = available[1]['device']  # Higher number
    else:
        # More than 2 ports, ask user to select
        while True:
            try:
                choice1 = int(input("\nSelect Reader 1 (Player1 & Player2) [1-{}]: ".format(len(available))))
                if 1 <= choice1 <= len(available):
                    break
                print("Invalid choice, try again.")
            except (ValueError, KeyboardInterrupt):
                sys.exit(0)
        
        while True:
            try:
                choice2 = int(input("Select Reader 2 (Player3 & Player4) [1-{}]: ".format(len(available))))
                if 1 <= choice2 <= len(available) and choice2 != choice1:
                    break
                if choice2 == choice1:
                    print("Please select a different port.")
                else:
                    print("Invalid choice, try again.")
            except (ValueError, KeyboardInterrupt):
                sys.exit(0)
        
        port1 = available[choice1-1]['device']
        port2 = available[choice2-1]['device']
    
    print(f"\n✓ Selected:")
    print(f"   Reader 1: {port1}")
    print(f"   Reader 2: {port2}")
    
    # Save for next time
    save_port_config(port1, port2)
    
    return port1, port2

# Auto-detect or select ports
PORT1, PORT2 = select_ports()

# Initialize both serial connections
ser1 = serial.Serial(PORT1, BAUD, timeout=0)  # non-blocking
try:
    ser1.setDTR(False); ser1.setRTS(False)     # avoid auto-reset loops
except Exception:
    pass

ser2 = serial.Serial(PORT2, BAUD, timeout=0)  # non-blocking
try:
    ser2.setDTR(False); ser2.setRTS(False)     # avoid auto-reset loops
except Exception:
    pass

time.sleep(0.3)
ser1.reset_input_buffer()
ser2.reset_input_buffer()


# Map scanned UIDs to known players
PLAYER_TAGS = {
    "EF89FE1E": "Player1", #FIRE
    "8F5F261F": "Player2", #ELECTRICITY 
    "AF38DD1C": "Player3", #WATER
    "6351EAD9": "Player4", #LAND
}

# Special cancel tag
CANCEL_TAG = "B9230502"

# Define resource cards by type
RESOURCE_CARDS = {
    "FIRE": [
        "047BB30CBE2A81",
        "534DE1D9410001",
        "53BF94DA410001",
        "536B3ADA410001",
        "535FF3D9410001",
        "53E4C2DA410001",
        "5311A0DA410001",
        "53DBAEDA410001",
        "539478DA410001",
        "53BCB2DA410001",
        "53AB8FDA410001",
        "5360F3D9410001",
        "53BBB2DA410001",
        "53E9C2DA410001",
        "5348E1D9410001",
        "53DD90DA410001",
        "532FDED9410001",
        "53A6B2DA410001",
    ],
    "ELECTRICITY": [
        "0429A40CBE2A81",
        "537BDAD9410001",
        "537FE5D9410001",
        "533FEBD9410001",
        "5380DAD9410001",
        "5353E1D9410001",
        "538DD7D9410001",
        "536BF4DA410001",
        "538CD7D9410001",
        "5381DAD9410001",
        "53978FDA410001",
        "5398D7D9410001",
    ],
    "WATER": [
        "5387D4D9410001",
        "5370D4D9410001",
        "53D3DDD9410001",
        "53C5DAD9410001",
        "533BF7DA410001",
        "53D0DAD9410001",
        "5344EFD9410001",
        "5305F0D9410001",
        "539978DA410001",
        "533177DA410001",
        "536FD4D9410001",
        "53F2E4D9410001",
        "53C8E1D9410001",
        "5386D4D9410001",
        "53C4DAD9410001",
        "538AD4D9410001",
        "53D0DDD9410001",
    ],
    "LAND": [
        "5336DED9410001",
        "5358D7D9410001",
        "538F68DA410001",
        "538C7CDA410001",
        "538BD4D9410001",
        "535FD7D9410001",
        "5310A0DA410001",
        "532067DA410001",
        "53694EDA410001",
        "53EDE4D9410001",
        "530B9FDA410001",
        "5378E5D9410001",
        "53D2DDD9410001",
        "53A48FDA410001",
        "53C9DAD9410001",
        "53EAEBD9410001",
        "53F8A3DA410001",
        "53EEAEDA410001",
        "53EEAEDA410001",
    ],
}

# Build reverse lookup: UID -> Resource Type
RESOURCE_TAGS = {}
for resource_type, uids in RESOURCE_CARDS.items():
    for uid in uids:
        RESOURCE_TAGS[uid] = resource_type

# Game state
# per-player pending choice (resource + uid)
pending = {
    "Player1": {"resource": None, "uid": None},
    "Player2": {"resource": None, "uid": None},
    "Player3": {"resource": None, "uid": None},
    "Player4": {"resource": None, "uid": None},
}
# UIDs that are permanently burned (consumed in a completed trade)
used_block_uids = set()
active_player = None

# Sounds
pygame.mixer.init()
sounds = {
    "confirm": pygame.mixer.Sound(os.path.join(SOUNDS_DIR, "confirm.mp3")),
    "double_spend": pygame.mixer.Sound(os.path.join(SOUNDS_DIR, "double_spend.mp3")),
    "reset": pygame.mixer.Sound(os.path.join(SOUNDS_DIR, "reset.mp3")),
    "activate": pygame.mixer.Sound(os.path.join(SOUNDS_DIR, "activate.mp3")),
    "FIRE": pygame.mixer.Sound(os.path.join(SOUNDS_DIR, "fire.mp3")),
    "ELECTRICITY": pygame.mixer.Sound(os.path.join(SOUNDS_DIR, "electricity.mp3")),
    "WATER": pygame.mixer.Sound(os.path.join(SOUNDS_DIR, "water.mp3")),
    "LAND": pygame.mixer.Sound(os.path.join(SOUNDS_DIR, "land.mp3")),
}

def send_lcd(message, reader=None):
    """Send message to LCD screen(s). If reader specified, send to that reader only."""
    try:
        if reader == 1 or reader is None:
            ser1.write(f"DISPLAY:{message}\n".encode())
        if reader == 2 or reader is None:
            ser2.write(f"DISPLAY:{message}\n".encode())
    except:
        pass

def reset_state():
    global active_player, pending
    active_player = None
    pending = {
        "Player1": {"resource": None, "uid": None},
        "Player2": {"resource": None, "uid": None},
        "Player3": {"resource": None, "uid": None},
        "Player4": {"resource": None, "uid": None}
    }
    print("🔁 State reset.")
    send_lcd("Ready to scan")
    try:
        sounds["reset"].play()
    except:
        pass

def check_and_commit_trade(force=False):
    # Collect all players with resources
    players_with_resources = []
    for player in ["Player1", "Player2", "Player3", "Player4"]:
        if pending[player]["resource"]:
            players_with_resources.append(player)
    
    # Need at least 2 players to trade
    if len(players_with_resources) < 2 and not force:
        print("⚠️ Need at least 2 players with resources before confirm.")
        send_lcd("Need 2+ players")
        return

    print("\n🎉 Trade Confirmed")
    for player in players_with_resources:
        res = pending[player]["resource"]
        print(f"  {player} trading: {res}")
    
    send_lcd("Sending tx…")
    
    try:
        # Each player with a resource sends to the next player in rotation
        # This creates a circular trade: P1→P2→P3→P4→P1
        for i, sender in enumerate(players_with_resources):
            recipient = players_with_resources[(i + 1) % len(players_with_resources)]
            resource = pending[sender]["resource"]
            
            if resource:
                tx_hash = trigger_transaction(sender, recipient, resource)
                print(f"📡 TX ({sender}→{recipient}): {tx_hash}")
                # Display player numbers (e.g., "P1>P2 OK")
                sender_num = sender[-1]  # Last char of "Player1" = "1"
                recipient_num = recipient[-1]  # Last char of "Player2" = "2"
                send_lcd(f"P{sender_num}>P{recipient_num} OK")
                
                # Burn the sender's block UID
                if pending[sender]["uid"]:
                    used_block_uids.add(pending[sender]["uid"])
                
                time.sleep(0.5)  # Brief delay between transactions

        try:
            sounds["confirm"].play()
        except:
            pass

    except Exception as e:
        print(f"⚠️ Transaction failed: {e}")
        send_lcd("Tx failed")

    time.sleep(2)
    reset_state()
    
def process_scan(uid):
    global active_player, pending
    uid = uid.strip().upper()

    # Check for cancel tag - only works if there's an active trade to cancel
    if uid == CANCEL_TAG:
        # Check if any player has selected a resource (i.e., there's something to cancel)
        has_pending_trade = any(pending[p]["resource"] is not None for p in pending)
        
        if has_pending_trade:
            print("🔙 Trade canceled! Starting over...")
            send_lcd("Trade canceled")
            try:
                sounds["reset"].play()
            except Exception as e:
                print(f"Sound error: {e}")
            time.sleep(1)
            reset_state()
        else:
            print("⚠️ No active trade to cancel.")
            send_lcd("Nothing to cancel")
        return

    if uid in PLAYER_TAGS:
        player = PLAYER_TAGS[uid]
        
        # Check if this player already has a resource (ready to confirm)
        if pending[player]["resource"] is not None:
            print(f"🟢 {player} confirmed the trade!")
            send_lcd(f"{player} confirms")
            check_and_commit_trade()
            return
        
        # Otherwise, set them as the active player
        active_player = player
        print(f"👤 {active_player} entered trade mode.")
        try:
            sounds["activate"].play()
        except Exception as e:
            print(f"Sound error: {e}")
        send_lcd(f"{active_player}")
        return

    # resource?
    if uid in RESOURCE_TAGS:
        if not active_player:
            print("⚠️ Scan a player first.")
            send_lcd("Scan player first")
            return

        if uid in used_block_uids:
            print("⛔ This block (UID) was already used in a previous trade.")
            send_lcd("Block used!")
            try:
                sounds["double_spend"].play()
            except Exception as e:
                print(f"Sound error: {e}")
            return

        resource = RESOURCE_TAGS[uid].upper()
        pending[active_player]["resource"] = resource
        pending[active_player]["uid"] = uid
        print(f"📦 {resource} set for {active_player} (UID: {uid})")
        if resource in sounds:
            try:
                sounds[resource].play()
            except Exception as e:
                print(f"Sound error: {e}")
        send_lcd(f"{resource} ready")
        return

    print(f"❓ Unknown UID: {uid}")
    send_lcd("Unknown tag")


def serial_loop_reader1():
    """Handle scans from Reader 1 (Player1 & Player2)"""
    while True:
        try:
            line = ser1.readline().decode().strip()
            if line.startswith("SCAN,"):
                uid = line.split(",")[1]
                process_scan(uid)
        except Exception as e:
            print("Reader 1 error:", e)

def serial_loop_reader2():
    """Handle scans from Reader 2 (Player3 & Player4)"""
    while True:
        try:
            line = ser2.readline().decode().strip()
            if line.startswith("SCAN,"):
                uid = line.split(",")[1]
                process_scan(uid)
        except Exception as e:
            print("Reader 2 error:", e)

def check_for_keypress():
    while True:
        if select.select([sys.stdin], [], [], 0.1)[0]:
            key = sys.stdin.readline().strip().upper()
            if key == "C":
                print("🟢 Manual confirm.")
                check_and_commit_trade()
            elif key == "P":
                print("🛑 Manual reset.")
                reset_state()

# Start threads for both readers
threading.Thread(target=serial_loop_reader1, daemon=True).start()
threading.Thread(target=serial_loop_reader2, daemon=True).start()
threading.Thread(target=check_for_keypress, daemon=True).start()

print("🔌 Ready for 4-player mode with 2 NFC readers!")
print(f"   Reader 1 ({PORT1}): Player1 & Player2")
print(f"   Reader 2 ({PORT2}): Player3 & Player4")
print("   Scan cancel tag to reset current trade.")
print("   Keyboard: Press C to confirm trade, P to reset all.")
while True:
    time.sleep(1)
