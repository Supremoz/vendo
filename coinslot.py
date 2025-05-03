import RPi.GPIO as GPIO
import time
import sys
import tty
import termios
import threading

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
BUTTON2_PIN = 24    # Second button input pin (new)
RELAY2_PIN = 25     # Second relay control pin (new)
LED2_PIN = 26       # LED to indicate when second button is active (new)

# Setup GPIO pins
GPIO.setup(COIN_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(BUTTON1_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(RELAY1_PIN, GPIO.OUT)
GPIO.setup(LED1_PIN, GPIO.OUT)
GPIO.setup(BUTTON2_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # New second button
GPIO.setup(RELAY2_PIN, GPIO.OUT)                           # New second relay
GPIO.setup(LED2_PIN, GPIO.OUT)                             # New second LED

# Initialize outputs
GPIO.output(RELAY1_PIN, GPIO.HIGH)  # Relay1 starts ON
GPIO.output(LED1_PIN, GPIO.LOW)     # LED1 starts OFF
GPIO.output(RELAY2_PIN, GPIO.HIGH)  # Relay2 starts ON (new)
GPIO.output(LED2_PIN, GPIO.LOW)     # LED2 starts OFF (new)

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

def update_button_status():
    """Update the button status LEDs based on available credit"""
    if total_value >= MINIMUM_AMOUNT:
        GPIO.output(LED1_PIN, GPIO.HIGH)  # Turn ON LED1 to indicate button1 is active
        GPIO.output(LED2_PIN, GPIO.HIGH)  # Turn ON LED2 to indicate button2 is active (new)
        print(f"Both buttons are now ACTIVE (₱{total_value:.2f} available)")
    else:
        GPIO.output(LED1_PIN, GPIO.LOW)   # Turn OFF LED1
        GPIO.output(LED2_PIN, GPIO.LOW)   # Turn OFF LED2 (new)
        print(f"Buttons are INACTIVE (₱{total_value:.2f} available, need ₱{MINIMUM_AMOUNT-total_value:.2f} more)")

def activate_relay1():
    """Function to activate the first relay"""
    global total_value
    
    if total_value >= MINIMUM_AMOUNT:
        print("Activating relay 1...")
        GPIO.output(RELAY1_PIN, GPIO.LOW)  # Turn ON relay1
        time.sleep(1)  # Keep relay on for 1 second (adjust as needed)
        GPIO.output(RELAY1_PIN, GPIO.HIGH)   # Turn OFF relay1
        
        # Deduct the amount used
        total_value -= MINIMUM_AMOUNT
        print(f"Completed action on relay 1. Remaining credit: ₱{total_value:.2f}")
        update_button_status()
        return True
    else:
        print(f"Not enough credit. Need ₱{MINIMUM_AMOUNT-total_value:.2f} more.")
        return False

def activate_relay2():
    """Function to activate the second relay (new)"""
    global total_value
    
    if total_value >= MINIMUM_AMOUNT:
        print("Activating relay 2...")
        GPIO.output(RELAY2_PIN, GPIO.LOW)  # Turn ON relay2
        time.sleep(1)  # Keep relay on for 1 second (adjust as needed)
        GPIO.output(RELAY2_PIN, GPIO.HIGH)   # Turn OFF relay2
        
        # Deduct the amount used
        total_value -= MINIMUM_AMOUNT
        print(f"Completed action on relay 2. Remaining credit: ₱{total_value:.2f}")
        update_button_status()
        return True
    else:
        print(f"Not enough credit. Need ₱{MINIMUM_AMOUNT-total_value:.2f} more.")
        return False

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
        elif char == '2' and keyboard_enabled:  # New key for second button
            print("Key '2' pressed - attempting to activate button 2")
            activate_relay2()
        elif char == 'q':
            print("Quit command received")
            running = False
            break

try:
    print("System initializing...")
    print("Coin detector active. Insert coins...")
    print(f"Minimum amount required: ₱{MINIMUM_AMOUNT:.2f}")
    
    # Start the keyboard monitoring thread AFTER initialization
    keyboard_thread = threading.Thread(target=keyboard_monitor)
    keyboard_thread.daemon = True
    keyboard_thread.start()
    
    last_state = GPIO.input(COIN_PIN)
    update_button_status()
    print("System ready! Press '1' to activate button 1, '2' to activate button 2, 'q' to quit")
    
    while running:
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
            else:
                print(f"Unknown coin: {pulse_count} pulses")
            pulse_count = 0
        
        # Check for physical button presses
        if GPIO.input(BUTTON1_PIN) == GPIO.LOW:  # Button 1 pressed (LOW because of pull-up)
            print("Physical button 1 pressed")
            activate_relay1()
            time.sleep(0.5)  # Debounce delay
            
        if GPIO.input(BUTTON2_PIN) == GPIO.LOW:  # Button 2 pressed (new)
            print("Physical button 2 pressed")
            activate_relay2()
            time.sleep(0.5)  # Debounce delay
            
        time.sleep(0.01)  # Reduce CPU usage

except KeyboardInterrupt:
    print("Program interrupted")
finally:
    running = False
    time.sleep(0.5)  # Give threads time to close
    GPIO.cleanup()
    print("Program ended. GPIO cleaned up.")