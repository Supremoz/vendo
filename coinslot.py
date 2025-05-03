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
COIN_PIN = 17  # Coin acceptor input pin
BUTTON_PIN = 27  # Button input pin
RELAY_PIN = 22  # Relay control pin
LED_PIN = 23  # LED to indicate when button is active

# Setup GPIO pins
GPIO.setup(COIN_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(RELAY_PIN, GPIO.OUT)
GPIO.setup(LED_PIN, GPIO.OUT)

# Initialize outputs
GPIO.output(RELAY_PIN, GPIO.LOW)  # Relay starts OFF
GPIO.output(LED_PIN, GPIO.LOW)    # LED starts OFF

# Variables for coin detection
total_value = 0.0
pulse_count = 0
last_pulse_time = 0
MINIMUM_AMOUNT = 10.0  # Minimum amount required (10 pesos)

# Define peso values based on calibration
coin_values = {
    1: 1.00,    # H1: 1 peso coin (new)
    1: 1.00,    # H2: 1 peso coin (old)
    5: 5.00,    # H3: 5 peso coin (new)
    5: 5.00,    # H4: 5 peso coin (old)
    10: 10.00,  # H5: 10 peso coin (new)
    10: 10.00   # H6: 10 peso coin (old)
}

# Flag to control program execution
running = True

def update_button_status():
    """Update the button status LED based on available credit"""
    if total_value >= MINIMUM_AMOUNT:
        GPIO.output(LED_PIN, GPIO.HIGH)  # Turn ON LED to indicate button is active
        print(f"Button is now ACTIVE (₱{total_value:.2f} available)")
    else:
        GPIO.output(LED_PIN, GPIO.LOW)   # Turn OFF LED
        print(f"Button is INACTIVE (₱{total_value:.2f} available, need ₱{MINIMUM_AMOUNT-total_value:.2f} more)")

def activate_relay():
    """Function to activate the relay"""
    global total_value
    
    if total_value >= MINIMUM_AMOUNT:
        print("Activating relay...")
        GPIO.output(RELAY_PIN, GPIO.HIGH)  # Turn ON relay
        time.sleep(1)  # Keep relay on for 1 second (adjust as needed)
        GPIO.output(RELAY_PIN, GPIO.LOW)   # Turn OFF relay
        
        # Deduct the amount used
        total_value -= MINIMUM_AMOUNT
        print(f"Completed action. Remaining credit: ₱{total_value:.2f}")
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
    global running
    
    print("Keyboard monitor active. Press '1' to activate the button, 'q' to quit.")
    
    while running:
        char = getch()
        if char == '1':
            print("Key '1' pressed - attempting to activate button")
            activate_relay()
        elif char == 'q':
            print("Quit command received")
            running = False
            break

# Start the keyboard monitoring thread
keyboard_thread = threading.Thread(target=keyboard_monitor)
keyboard_thread.daemon = True
keyboard_thread.start()

try:
    print("Coin detector active. Insert coins...")
    print(f"Minimum amount required: ₱{MINIMUM_AMOUNT:.2f}")
    print("Press '1' to activate button, 'q' to quit")
    last_state = GPIO.input(COIN_PIN)
    update_button_status()
    
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
        
        # Check for physical button press
        if GPIO.input(BUTTON_PIN) == GPIO.LOW:  # Button pressed (LOW because of pull-up)
            print("Physical button pressed")
            activate_relay()
            time.sleep(0.5)  # Debounce delay
            
        time.sleep(0.01)  # Reduce CPU usage

except KeyboardInterrupt:
    print("Program interrupted")
finally:
    running = False
    time.sleep(0.5)  # Give threads time to close
    GPIO.cleanup()
    print("Program ended. GPIO cleaned up.")