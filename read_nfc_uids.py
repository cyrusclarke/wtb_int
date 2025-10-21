#!/usr/bin/env python3
"""
Simple NFC UID reader for WTB project
Scan your cards and this will display the UIDs
"""

import serial
import time

# Serial port from Arduino - adjust if needed
PORT = "/dev/tty.usbmodem101"
BAUD = 115200

print("🔍 NFC UID Reader")
print("=" * 50)

try:
    ser = serial.Serial(PORT, BAUD, timeout=0.1)
    time.sleep(1)  # Wait for connection
    ser.reset_input_buffer()
    
    print(f"✅ Connected to {PORT}")
    print("\n📝 Scan your NFC cards now...")
    print("   (Press Ctrl+C to stop)\n")
    
    seen_uids = set()
    
    while True:
        try:
            line = ser.readline().decode().strip()
            
            if line.startswith("SCAN,"):
                uid = line.split(",")[1].strip().upper()
                
                if uid not in seen_uids:
                    seen_uids.add(uid)
                    print(f"✨ New UID detected: {uid}")
                    print(f"   Add to code as: \"{uid}\": \"PlayerX\" or \"RESOURCE_NAME\"\n")
                else:
                    print(f"♻️  Already scanned: {uid}")
                    
        except UnicodeDecodeError:
            pass
        except KeyboardInterrupt:
            print("\n\n📋 Summary of scanned UIDs:")
            print("=" * 50)
            for uid in sorted(seen_uids):
                print(f"  \"{uid}\": \"\",")
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"⚠️  Error: {e}")
            
except serial.SerialException as e:
    print(f"❌ Could not connect to {PORT}")
    print(f"   Error: {e}")
    print(f"\n💡 Tips:")
    print(f"   - Check if Arduino is connected")
    print(f"   - Update PORT in this script if needed")
    print(f"   - Make sure no other program is using the port")

