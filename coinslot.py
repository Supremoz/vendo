import RPi.GPIO as GPIO
import time
import sys
import tty
import termios
import threading
import requests
import json
from datetime import datetime

# Firebase configuration
FIREBASE_HOST = "https://napkinvendo-default-rtdb.firebaseio.com/"
FIREBASE_AUTH = "332a5927c0bd1bf572f995558e21b07d348e071d"  # Your Firebase auth token if needed

# Clean up any previous GPIO setups
GPIO.cleanup()

# Configure GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# Pin definitions
COIN_PIN = 17       # Coin acceptor input pin
BUTTON1_PIN = 27    # First button input pin
RELAY1_PIN = 22     # First relay control pin
LED1_PIN = 23       # LED to indicate when first button is active
BUTTON2_PIN = 24    # Second button input pin
RELAY2_PIN = 25     # Second relay control pin
LED2_PIN = 26       # LED to indicate when second button is active
IR1_PIN = 18        # First IR sensor input pin
IR2_PIN = 19        # Second IR sensor input pin

# Setup GPIO pins
GPIO.setup(COIN_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(BUTTON1_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(RELAY1_PIN, GPIO.OUT)
GPIO.setup(LED1_PIN, GPIO.OUT)
GPIO.setup(BUTTON2_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(RELAY2_PIN, GPIO.OUT)
GPIO.setup(LED2_PIN, GPIO.OUT)
GPIO.setup(IR1_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(IR2_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Initialize outputs
GPIO.output(RELAY1_PIN, GPIO.HIGH)  # Relay1 starts ON
GPIO.output(LED1_PIN, GPIO.LOW)     # LED1 starts OFF
GPIO.output(RELAY2_PIN, GPIO.HIGH)  # Relay2 starts ON
GPIO.output(LED2_PIN, GPIO.LOW)     # LED2 starts OFF

# Variables for coin detection
total_value = 0.0
pulse_count = 0
last_pulse_time = 0
MINIMUM_AMOUNT = 10.0  # Minimum amount required (10 pesos)
keyboard_enabled = False  # Flag to enable keyboard input after initialization

# Define peso values based on calibration
coin_values = {
    1: 1.00,    # H1: 1 peso coin (new)
    5: 5.00,    # H3: 5 peso coin (new)
    10: 10.00,  # H5: 10 peso coin (new)
}

# Flag to control program execution
running = True

# IR sensor status
ir1_triggered = False
ir2_triggered = False

# Relay activation tracking
relay1_active = False
relay2_active = False

# Inventory tracking
relay1_inventory = 0
relay2_inventory = 0

# Firebase communication functions
def initialize_firebase():
    """Initialize and fetch data from Firebase"""
    global relay1_inventory, relay2_inventory
    
    try:
        # Fetch initial inventory values
        response = requests.get(f"{FIREBASE_HOST}/inventory.json")
        if response.status_code == 200:
            data = response.json()
            if data and 'relay1' in data:
                relay1_inventory = data['relay1']
            if data and 'relay2' in data:
                relay2_inventory = data['relay2']
            print(f"Firebase connected. Inventory: Relay1={relay1_inventory}, Relay2={relay2_inventory}")
        else:
            print(f"Failed to fetch inventory data. Status code: {response.status_code}")
            
        # Send initial system status
        update_system_status()
        return True
    except Exception as e:
        print(f"Firebase initialization error: {e}")
        return False

def update_inventory():
    """Update inventory in Firebase"""
    try:
        inventory_data = {
            "relay1": relay1_inventory,
            "relay2": relay2_inventory
        }
        response = requests.patch(f"{FIREBASE_HOST}/inventory.json", data=json.dumps(inventory_data))
        if response.status_code == 200:
            print("Inventory updated in Firebase")
        else:
            print(f"Failed to update inventory. Status code: {response.status_code}")
    except Exception as e:
        print(f"Firebase inventory update error: {e}")

def update_transactions(relay_num, amount):
    """Record transaction in Firebase"""
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        transaction_data = {
            "relay": relay_num,
            "amount": amount,
            "timestamp": timestamp
        }
        # Use push() equivalent for HTTP requests to add to list
        response = requests.post(f"{FIREBASE_HOST}/transactions.json", data=json.dumps(transaction_data))
        if response.status_code == 200:
            print(f"Transaction recorded: Relay {relay_num}, ₱{amount:.2f}")
        else:
            print(f"Failed to record transaction. Status code: {response.status_code}")
    except Exception as e:
        print(f"Firebase transaction recording error: {e}")

def update_money_collected(amount):
    """Update money collection in Firebase"""
    try:
        # Get current total first
        response = requests.get(f"{FIREBASE_HOST}/money_collected.json")
        current_total = 0
        if response.status_code == 200 and response.json() is not None:
            current_total = float(response.json())
        
        # Update with new amount
        new_total = current_total + amount
        response = requests.put(f"{FIREBASE_HOST}/money_collected.json", data=json.dumps(new_total))
        if response.status_code == 200:
            print(f"Money collected updated: ₱{new_total:.2f}")
        else:
            print(f"Failed to update money collected. Status code: {response.status_code}")
    except Exception as e:
        print(f"Firebase money collection update error: {e}")

def update_system_status():
    """Update system status in Firebase"""
    try:
        status_data = {
            "total_value": total_value,
            "relay1_active": relay1_active,
            "relay2_active": relay2_active,
            "relay1_inventory": relay1_inventory,
            "relay2_inventory": relay2_inventory,
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        response = requests.patch(f"{FIREBASE_HOST}/system_status.json", data=json.dumps(status_data))
        if response.status_code == 200:
            print("System status updated in Firebase")
        else:
            print(f"Failed to update system status. Status code: {response.status_code}")
    except Exception as e:
        print(f"Firebase status update error: {e}")

def check_firebase_updates():
    """Thread function to periodically check for updates from Firebase"""
    global relay1_inventory, relay2_inventory, running
    
    while running:
        try:
            response = requests.get(f"{FIREBASE_HOST}/inventory.json")
            if response.status_code == 200:
                data = response.json()
                if data:
                    # Update local inventory if changed in Firebase
                    if 'relay1' in data and relay1_inventory != data['relay1']:
                        relay1_inventory = data['relay1']
                        print(f"Relay 1 inventory updated from Firebase: {relay1_inventory}")
                    if 'relay2' in data and relay2_inventory != data['relay2']:
                        relay2_inventory = data['relay2']
                        print(f"Relay 2 inventory updated from Firebase: {relay2_inventory}")
            
            # Check for remote commands
            response = requests.get(f"{FIREBASE_HOST}/commands.json")
            if response.status_code == 200:
                commands = response.json()
                if commands:
                    if 'shutdown' in commands and commands['shutdown']:
                        print("Remote shutdown command received")
                        running = False
                        
                    # Reset commands after processing
                    requests.put(f"{FIREBASE_HOST}/commands.json", data=json.dumps({"shutdown": False}))
                        
        except Exception as e:
            print(f"Error checking Firebase updates: {e}")
        
        # Check every 5 seconds
        time.sleep(5)

def update_button_status():
    """Update the button status LEDs based on available credit and inventory"""
    # Check both credit and inventory conditions
    relay1_available = total_value >= MINIMUM_AMOUNT and relay1_inventory > 0
    relay2_available = total_value >= MINIMUM_AMOUNT and relay2_inventory > 0
    
    # Update LED status based on availability
    GPIO.output(LED1_PIN, GPIO.HIGH if relay1_available else GPIO.LOW)
    GPIO.output(LED2_PIN, GPIO.HIGH if relay2_available else GPIO.LOW)
    
    # Print status update
    if relay1_available and relay2_available:
        print(f"Both buttons are ACTIVE (₱{total_value:.2f} available)")
    elif relay1_available:
        print(f"Only Button 1 ACTIVE (₱{total_value:.2f} available, Relay 2 out of stock)")
    elif relay2_available:
        print(f"Only Button 2 ACTIVE (₱{total_value:.2f} available, Relay 1 out of stock)")
    else:
        if total_value < MINIMUM_AMOUNT:
            print(f"Buttons are INACTIVE (₱{total_value:.2f} available, need ₱{MINIMUM_AMOUNT-total_value:.2f} more)")
        else:
            print("Buttons are INACTIVE (Out of stock)")
    
    # Update system status in Firebase
    update_system_status()

def check_ir_sensors():
    """Check the status of IR sensors and handle relay deactivation if needed"""
    global ir1_triggered, ir2_triggered, relay1_active, relay2_active
    
    # Check IR sensor 1
    ir1_state = GPIO.input(IR1_PIN)
    if ir1_state == GPIO.LOW:  # Object detected (LOW when object is present)
        if not ir1_triggered and relay1_active:
            print("IR Sensor 1: Object detected - stopping relay 1")
            GPIO.output(RELAY1_PIN, GPIO.HIGH)  # Turn OFF relay immediately
            relay1_active = False
            ir1_triggered = True
            update_system_status()  # Update Firebase about relay state change
    else:
        if ir1_triggered:
            print("IR Sensor 1: Path clear")
            ir1_triggered = False
    
    # Check IR sensor 2
    ir2_state = GPIO.input(IR2_PIN)
    if ir2_state == GPIO.LOW:  # Object detected (LOW when object is present)
        if not ir2_triggered and relay2_active:
            print("IR Sensor 2: Object detected - stopping relay 2")
            GPIO.output(RELAY2_PIN, GPIO.HIGH)  # Turn OFF relay immediately
            relay2_active = False
            ir2_triggered = True
            update_system_status()  # Update Firebase about relay state change
    else:
        if ir2_triggered:
            print("IR Sensor 2: Path clear")
            ir2_triggered = False

def activate_relay1():
    """Function to activate the first relay"""
    global total_value, relay1_active, relay1_inventory
    
    # Check IR sensor before activating relay
    if GPIO.input(IR1_PIN) == GPIO.LOW:
        print("Cannot activate relay 1: Object detected by IR sensor 1")
        return False
    
    # Check both credit and inventory
    if total_value >= MINIMUM_AMOUNT and relay1_inventory > 0:
        print("Activating relay 1...")
        GPIO.output(RELAY1_PIN, GPIO.LOW)  # Turn ON relay1
        relay1_active = True
        
        # Update inventory in local tracking
        relay1_inventory -= 1
        
        # Start a monitoring thread for the relay activation
        relay_monitor = threading.Thread(target=monitor_relay_activation, args=(1, RELAY1_PIN, IR1_PIN))
        relay_monitor.daemon = True
        relay_monitor.start()
        
        # Deduct the amount used
        total_value -= MINIMUM_AMOUNT
        
        # Record this transaction
        update_transactions(1, MINIMUM_AMOUNT)
        update_money_collected(MINIMUM_AMOUNT)
        
        # Update Firebase with new inventory and system status
        update_inventory()
        update_system_status()
        
        print(f"Relay 1 activated. Remaining credit: ₱{total_value:.2f}, Inventory: {relay1_inventory}")
        update_button_status()
        return True
    else:
        if total_value < MINIMUM_AMOUNT:
            print(f"Not enough credit. Need ₱{MINIMUM_AMOUNT-total_value:.2f} more.")
        else:
            print("Relay 1 is out of stock.")
        return False

def activate_relay2():
    """Function to activate the second relay"""
    global total_value, relay2_active, relay2_inventory
    
    # Check IR sensor before activating relay
    if GPIO.input(IR2_PIN) == GPIO.LOW:
        print("Cannot activate relay 2: Object detected by IR sensor 2")
        return False
    
    # Check both credit and inventory
    if total_value >= MINIMUM_AMOUNT and relay2_inventory > 0:
        print("Activating relay 2...")
        GPIO.output(RELAY2_PIN, GPIO.LOW)  # Turn ON relay2
        relay2_active = True
        
        # Update inventory in local tracking
        relay2_inventory -= 1
        
        # Start a monitoring thread for the relay activation
        relay_monitor = threading.Thread(target=monitor_relay_activation, args=(2, RELAY2_PIN, IR2_PIN))
        relay_monitor.daemon = True
        relay_monitor.start()
        
        # Deduct the amount used
        total_value -= MINIMUM_AMOUNT
        
        # Record this transaction
        update_transactions(2, MINIMUM_AMOUNT)
        update_money_collected(MINIMUM_AMOUNT)
        
        # Update Firebase with new inventory and system status
        update_inventory()
        update_system_status()
        
        print(f"Relay 2 activated. Remaining credit: ₱{total_value:.2f}, Inventory: {relay2_inventory}")
        update_button_status()
        return True
    else:
        if total_value < MINIMUM_AMOUNT:
            print(f"Not enough credit. Need ₱{MINIMUM_AMOUNT-total_value:.2f} more.")
        else:
            print("Relay 2 is out of stock.")
        return False

def monitor_relay_activation(relay_num, relay_pin, ir_pin):
    """Monitor the IR sensor during relay activation and stop if needed"""
    global relay1_active, relay2_active
    
    activation_time = time.time()
    max_activation_time = 5  # Maximum time the relay can stay active (5 seconds)
    
    # Use relay_active flags instead of trying to read GPIO output
    active = True
    while active:
        # Update the active state based on relay number
        if relay_num == 1:
            active = relay1_active
        else:
            active = relay2_active
            
        # Check if IR sensor detects an object
        if GPIO.input(ir_pin) == GPIO.LOW:
            print(f"IR Sensor {relay_num}: Object detected - stopping relay {relay_num}")
            GPIO.output(relay_pin, GPIO.HIGH)  # Turn OFF relay immediately
            if relay_num == 1:
                relay1_active = False
            else:
                relay2_active = False
            update_system_status()  # Update Firebase about relay state change
            break
        
        # Check if maximum activation time is reached
        if time.time() - activation_time >= max_activation_time:
            print(f"Maximum activation time reached for relay {relay_num}")
            GPIO.output(relay_pin, GPIO.HIGH)  # Turn OFF relay
            if relay_num == 1:
                relay1_active = False
            else:
                relay2_active = False
            update_system_status()  # Update Firebase about relay state change
            break
        
        time.sleep(0.05)  # Short delay to reduce CPU usage
    
    print(f"Relay {relay_num} monitoring ended")

def getch():
    """Get a single character from the terminal"""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch

def keyboard_monitor():
    """Thread function to monitor keyboard input"""
    global running, keyboard_enabled
    
    # Wait for system to fully initialize before accepting keyboard input
    time.sleep(3)
    keyboard_enabled = True
    print("Keyboard monitor active. Press '1' to activate button 1, '2' to activate button 2, 'q' to quit.")
    
    while running:
        char = getch()
        if char == '1' and keyboard_enabled:
            print("Key '1' pressed - attempting to activate button 1")
            activate_relay1()
        elif char == '2' and keyboard_enabled:
            print("Key '2' pressed - attempting to activate button 2")
            activate_relay2()
        elif char == 'q':
            print("Quit command received")
            running = False
            break

try:
    print("System initializing...")
    print("Connecting to Firebase...")
    
    # Initialize Firebase connection
    firebase_ready = initialize_firebase()
    if not firebase_ready:
        print("Warning: Firebase connection failed. System will run in offline mode.")
    
    # Start Firebase monitoring thread
    firebase_thread = threading.Thread(target=check_firebase_updates)
    firebase_thread.daemon = True
    firebase_thread.start()
    
    print("Coin detector active. Insert coins...")
    print(f"Minimum amount required: ₱{MINIMUM_AMOUNT:.2f}")
    print("IR sensors active. Will stop relays when objects are detected.")
    
    # Start the keyboard monitoring thread AFTER initialization
    keyboard_thread = threading.Thread(target=keyboard_monitor)
    keyboard_thread.daemon = True
    keyboard_thread.start()
    
    last_state = GPIO.input(COIN_PIN)
    update_button_status()
    print("System ready! Press '1' to activate button 1, '2' to activate button 2, 'q' to quit")
    
    while running:
        # Check IR sensors
        check_ir_sensors()
        
        # Check for coin pulses
        current_state = GPIO.input(COIN_PIN)
        current_time = time.time()
        
        # Detect signal change (coin pulse)
        if last_state == GPIO.HIGH and current_state == GPIO.LOW:
            # New sequence or continuing current coin?
            if current_time - last_pulse_time > 0.5:
                # Process previous coin if exists
                if pulse_count > 0:
                    if pulse_count in coin_values:
                        coin_value = coin_values[pulse_count]
                        total_value += coin_value
                        print(f"Coin detected: ₱{coin_value:.2f}, Total: ₱{total_value:.2f}")
                        update_button_status()
                        
                        # Update money collected in Firebase
                        update_money_collected(coin_value)
                    else:
                        print(f"Unknown coin: {pulse_count} pulses")
                pulse_count = 0
            
            # Count this pulse
            pulse_count += 1
            last_pulse_time = current_time
            print(f"Pulse detected: {pulse_count}")
        
        last_state = current_state
        
        # Process coin after timeout (no pulses for a while)
        if pulse_count > 0 and current_time - last_pulse_time > 0.5:
            if pulse_count in coin_values:
                coin_value = coin_values[pulse_count]
                total_value += coin_value
                print(f"Coin detected: ₱{coin_value:.2f}, Total: ₱{total_value:.2f}")
                update_button_status()
                
                # Update money collected in Firebase
                update_money_collected(coin_value)
            else:
                print(f"Unknown coin: {pulse_count} pulses")
            pulse_count = 0
        
        # Check for physical button presses
        if GPIO.input(BUTTON1_PIN) == GPIO.LOW:  # Button 1 pressed (LOW because of pull-up)
            print("Physical button 1 pressed")
            activate_relay1()
            time.sleep(0.5)  # Debounce delay
            
        if GPIO.input(BUTTON2_PIN) == GPIO.LOW:  # Button 2 pressed
            print("Physical button 2 pressed")
            activate_relay2()
            time.sleep(0.5)  # Debounce delay
            
        time.sleep(0.01)  # Reduce CPU usage

except KeyboardInterrupt:
    print("Program interrupted")
finally:
    running = False
    # Final update to Firebase before exit
    update_system_status()
    time.sleep(0.5)  # Give threads time to close
    GPIO.cleanup()
    print("Program ended. GPIO cleaned up.")