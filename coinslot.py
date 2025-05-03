import RPi.GPIO as GPIO
import time

# Clean up any previous GPIO setups
GPIO.cleanup()

# Configure GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# Pin definitions
COIN_PIN = 17  # Coin acceptor input pin
BUTTON_PIN = 27  # Button input pin (change as needed)
RELAY_PIN = 22  # Relay control pin (change as needed)
LED_PIN = 23  # Optional LED to indicate when button is active

# Setup GPIO pins
GPIO.setup(COIN_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Button with pull-up resistor
GPIO.setup(RELAY_PIN, GPIO.OUT)  # Relay control
GPIO.setup(LED_PIN, GPIO.OUT)  # Status LED

# Initialize outputs
GPIO.output(RELAY_PIN, GPIO.LOW)  # Relay starts OFF
GPIO.output(LED_PIN, GPIO.LOW)    # LED starts OFF

# Variables for coin detection
total_value = 0.0
pulse_count = 0
last_pulse_time = 0
MINIMUM_AMOUNT = 10.0  # Minimum amount required (10 pesos)

# Define peso values based on your H6 calibration
coin_values = {
    1: 1.00,    # H1: 1 peso coin (new)
    1: 1.00,    # H2: 1 peso coin (old)
    5: 5.00,    # H3: 5 peso coin (new)
    5: 5.00,    # H4: 5 peso coin (old)
    10: 10.00,   # H5: 10 peso coin (new)
    10: 10.00    # H6: 10 peso coin (old)
}

def update_button_status():
    """Update the button status LED based on available credit"""
    if total_value >= MINIMUM_AMOUNT:
        GPIO.output(LED_PIN, GPIO.HIGH)  # Turn ON LED to indicate button is active
        print(f"Button is now ACTIVE (₱{total_value:.2f} available)")
    else:
        GPIO.output(LED_PIN, GPIO.LOW)   # Turn OFF LED
        print(f"Button is INACTIVE (₱{total_value:.2f} available, need ₱{MINIMUM_AMOUNT-total_value:.2f} more)")

try:
    print("Coin detector active. Insert coins...")
    print(f"Minimum amount required: ₱{MINIMUM_AMOUNT:.2f}")
    last_state = GPIO.input(COIN_PIN)
    update_button_status()
    
    while True:
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
        
        # Check for button press (only if enough credit)
        if GPIO.input(BUTTON_PIN) == GPIO.LOW:  # Button pressed (LOW because of pull-up)
            if total_value >= MINIMUM_AMOUNT:
                print("Button pressed - Activating relay...")
                GPIO.output(RELAY_PIN, GPIO.HIGH)  # Turn ON relay
                time.sleep(1)  # Keep relay on for 1 second (adjust as needed)
                GPIO.output(RELAY_PIN, GPIO.LOW)   # Turn OFF relay
                
                # Deduct the amount used (optional, comment out if you want to keep the credit)
                total_value -= MINIMUM_AMOUNT
                print(f"Completed action. Remaining credit: ₱{total_value:.2f}")
                update_button_status()
            else:
                print(f"Not enough credit. Need ₱{MINIMUM_AMOUNT-total_value:.2f} more.")
                time.sleep(0.5)  # Debounce delay
            
        time.sleep(0.01)  # Reduce CPU usage

except KeyboardInterrupt:
    GPIO.cleanup()
    print("Program ended.")