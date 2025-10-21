#!/usr/bin/env python3
import serial
import time

PORTS = {
    "ModuleA": "/dev/tty.usbmodem101",
    "ModuleB": "/dev/tty.usbmodem1101"
}

BAUD_RATES = [9600, 115200, 57600, 38400]

def test_port_baud(name, port, baud):
    print(f"\n--- Testing {name} on {port} at {baud} baud ---")
    try:
        # Try to open the port
        ser = serial.Serial(port, baud, timeout=0.1)
        print(f"✅ Successfully opened {port} at {baud} baud")
        
        # Set DTR/RTS like the game code does
        try:
            ser.setDTR(False)
            ser.setRTS(False)
        except Exception:
            pass
        
        # Wait for Arduino to reset and stabilize
        time.sleep(2)
        
        # Clear any existing data
        ser.reset_input_buffer()
        
        # Try to read for a few seconds
        start_time = time.time()
        received_data = []
        
        while time.time() - start_time < 3:
            if ser.in_waiting:
                try:
                    line = ser.readline().decode(errors="ignore").strip()
                    if line:
                        print(f"📥 Received: {line}")
                        received_data.append(line)
                except Exception as e:
                    print(f"❌ Read error: {e}")
            time.sleep(0.1)
        
        ser.close()
        
        if received_data:
            print(f"✅ {name} received {len(received_data)} messages at {baud} baud")
            return True, received_data
        else:
            print(f"⚠️ {name} received no messages at {baud} baud")
            return False, []
        
    except Exception as e:
        print(f"❌ Failed to open {port} at {baud} baud: {e}")
        return False, []

def test_port(name, port):
    print(f"\n--- Testing {name} on {port} ---")
    
    # Test different baud rates
    for baud in BAUD_RATES:
        success, data = test_port_baud(name, port, baud)
        if success:
            print(f"🎯 Found working baud rate: {baud}")
            return True, baud, data
    
    print(f"❌ No working baud rate found for {name}")
    return False, None, []

def main():
    print("🔌 Testing Serial Port Connections with Multiple Baud Rates")
    print("=" * 60)
    
    results = {}
    for name, port in PORTS.items():
        success, working_baud, data = test_port(name, port)
        results[name] = (success, working_baud, data)
    
    print("\n" + "=" * 60)
    print("📊 Test Results:")
    for name, (success, baud, data) in results.items():
        if success:
            print(f"  {name}: ✅ PASS at {baud} baud")
            if data:
                print(f"    Messages: {data}")
        else:
            print(f"  {name}: ❌ FAIL - no working baud rate")
    
    print("\n💡 If no data is received, the Arduino might:")
    print("   - Not be sending serial messages")
    print("   - Have a different baud rate than expected")
    print("   - Be stuck in an error state")
    print("   - Need to be reprogrammed")

if __name__ == "__main__":
    main()
