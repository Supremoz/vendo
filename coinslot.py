import RPi.GPIO as GPIO
import time

# First, make sure to cleanup in case of previous incomplete runs
GPIO.cleanup()

# GPIO setup
COIN_PIN = 17  # Change this to match your wiring

# Set up GPIO mode
GPIO.setmode(GPIO.BCM)
GPIO.setup(COIN_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Variables
total_amount = 0
pulse_count = 0
last_state = GPIO.input(COIN_PIN)
last_pulse_time = time.time()
pulse_timeout = 2.0  # 2 seconds timeout

# Coin values
COIN_VALUES = {
    1: 1,    # 1 pulse = 1 peso
    5: 5,    # 5 pulses = 5 pesos
    10: 10   # 10 pulses = 10 pesos
}

print("Coin Counter Started")
print("Insert coins to see the count")

try:
    while True:
        # Read current state
        current_state = GPIO.input(COIN_PIN)
        current_time = time.time()
        
        # Detect state change (polling method instead of interrupts)
        if current_state != last_state:
            # Simple debounce
            time.sleep(0.05)
            # Read again after debounce
            current_state = GPIO.input(COIN_PIN)
            
            # If it's a valid change (falling edge: 1->0)
            if last_state == 1 and current_state == 0:
                pulse_count += 1
                last_pulse_time = current_time
                print(f"Pulse detected! Count: {pulse_count}")
            
            # Update last state
            last_state = current_state
        
        # Check if we should process the pulses (timeout reached)
        if pulse_count > 0 and (current_time - last_pulse_time) > pulse_timeout:
            # Process the coin
            if pulse_count in COIN_VALUES:
                coin_value = COIN_VALUES[pulse_count]
                total_amount += coin_value
                print(f"Recognized coin: {pulse_count} pulses = {coin_value} Pesos")
            else:
                print(f"Unknown coin pattern: {pulse_count} pulses")
            
            # Reset for next coin
            pulse_count = 0
            
            # Display total
            print(f"Total amount: {total_amount} Pesos")
        
        # Small delay to reduce CPU usage
        time.sleep(0.01)

except KeyboardInterrupt:
    print(f"Program ended. Total amount: {total_amount} Pesos")
    GPIO.cleanup()