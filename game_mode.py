#! WTB integrated version 7th August 2025 Cyrus Clarke


import serial
import threading
from datetime import datetime
import pygame
import uuid
import sys
import select
import time
from test_onchain import trigger_transaction  # must be defined

# Serial port from Arduino
PORT = "/dev/tty.usbmodem101"  # Replace as needed
BAUD = 115200
ser = serial.Serial(PORT, BAUD, timeout=0)  # non-blocking
try:
    ser.setDTR(False); ser.setRTS(False)     # avoid auto-reset loops
except Exception:
    pass
time.sleep(0.3)
ser.reset_input_buffer()


# Map scanned UIDs to known players/resourcesc
PLAYER_TAGS = {
    "8F5F261F": "A",
    "EF89FE1E": "B"
}
RESOURCE_TAGS = {
    "047BB30CBE2A81": "FIRE",
    "0429A40CBE2A81": "ELECTRICITY"
}

# Game state
# per-player pending choice (resource + uid)
pending = {
    "A": {"resource": None, "uid": None},
    "B": {"resource": None, "uid": None},
}
# UIDs that are permanently burned (consumed in a completed trade)
used_block_uids = set()
active_player = None

# Sounds
pygame.mixer.init()
sounds = {
    "confirm": pygame.mixer.Sound("sounds/confirm.wav"),
    "reset": pygame.mixer.Sound("sounds/reset.mp3"),
    "activate": pygame.mixer.Sound("sounds/activate.mp3"),
    "FIRE": pygame.mixer.Sound("sounds/fire.mp3"),
    "ELECTRICITY": pygame.mixer.Sound("sounds/land.mp3")
}

# Serial connection
ser = serial.Serial(PORT, BAUD, timeout=0.1)

def send_lcd(message):
    try:
        ser.write(f"DISPLAY:{message}\n".encode())
    except:
        pass

def reset_state():
    global active_player, pending
    active_player = None
    pending = {"A": {"resource": None, "uid": None},
               "B": {"resource": None, "uid": None}}
    print("🔁 State reset.")
    send_lcd("Ready to scan")
    try:
        sounds["reset"].play()
    except:
        pass

def check_and_commit_trade(force=False):
    a_res = pending["A"]["resource"]
    b_res = pending["B"]["resource"]

    if not (a_res and b_res) and not force:
        print("⚠️ Need both players + resources before confirm.")
        send_lcd("Need both sides")
        return

    print("\n🎉 Trade Confirmed")
    if a_res: print(f"  A → B : {a_res}")
    if b_res: print(f"  B → A : {b_res}")
    send_lcd("Sending tx…")
    try:
        if a_res:
            tx_a = trigger_transaction("A", a_res)  # A pays B
            print(f"📡 TX (A→B): {tx_a}")
            send_lcd(f"A→B {tx_a[:10]}")
            # burn A's block UID
            if pending["A"]["uid"]:
                used_block_uids.add(pending["A"]["uid"])

        if b_res:
            tx_b = trigger_transaction("B", b_res)  # B pays A
            print(f"📡 TX (B→A): {tx_b}")
            send_lcd(f"B→A {tx_b[:10]}")
            # burn B's block UID
            if pending["B"]["uid"]:
                used_block_uids.add(pending["B"]["uid"])

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

    if uid in PLAYER_TAGS:
        active_player = PLAYER_TAGS[uid]
        print(f"👤 Player {active_player} entered trade mode.")
        sounds["activate"].play()
        send_lcd(f"Player {active_player}")
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
            return

        resource = RESOURCE_TAGS[uid].upper()
        pending[active_player]["resource"] = resource
        pending[active_player]["uid"] = uid
        print(f"📦 {resource} set for Player {active_player} (UID: {uid})")
        if resource in sounds:
            sounds[resource].play()
        send_lcd(f"{resource} ready")
        return

    print(f"❓ Unknown UID: {uid}")
    send_lcd("Unknown tag")


def serial_loop():
    while True:
        try:
            line = ser.readline().decode().strip()
            if line.startswith("SCAN,"):
                uid = line.split(",")[1]
                process_scan(uid)
        except Exception as e:
            print("Serial read error:", e)

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

# Start threads
threading.Thread(target=serial_loop, daemon=True).start()
threading.Thread(target=check_for_keypress, daemon=True).start()

print("🔌 Ready. Tap Player, then Resource. Press C to confirm, P to reset.")
while True:
    time.sleep(1)