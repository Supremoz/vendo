import RPi.GPIO as GPIO
import time

# GPIO setup - CHANGE THIS to match your wiring
COIN_PIN = 17  # GPIO pin connected to the coin acceptor

# Coin values
COIN_VALUES = {
    1: 1,    # 1 pulse = 1 peso
    5: 5,    # 5 pulses = 5 pesos
    10: 10   # 10 pulses = 10 pesos
}

# Set up GPIO mode
GPIO.setmode(GPIO.BCM)
GPIO.setup(COIN_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Variables
total_amount = 0
pulse_count = 0
pulse_sequence = []
last_pulse_time = 0
pulse_timeout = 2.0  # 2 seconds timeout

# Setup interrupt callback function
def coin_pulse_detected(channel):
    global pulse_count, last_pulse_time
    
    # Simple debounce
    current_time = time.time()
    if (current_time - last_pulse_time) < 0.05:  # 50ms debounce
        return
        
    pulse_count += 1
    last_pulse_time = current_time
    print(f"Pulse detected! Count: {pulse_count}")

# Register the interrupt event
GPIO.add_event_detect(COIN_PIN, GPIO.FALLING, callback=coin_pulse_detected)

print("Coin Counter Started")
print("Insert coins to see the count")

try:
    while True:
        # Check if we have pulses and enough time has passed
        current_time = time.time()
        
        if pulse_count > 0 and (current_time - last_pulse_time) > pulse_timeout:
            # Process the coin
            if pulse_count in COIN_VALUES:
                coin_value = COIN_VALUES[pulse_count]
                total_amount += coin_value
                print(f"Recognized coin: {pulse_count} pulses = {coin_value} Pesos")
            else:
                print(f"Unknown coin pattern: {pulse_count} pulses")
                
            # Record this sequence for debugging
            pulse_sequence.append(pulse_count)
            
            # Reset for next coin
            pulse_count = 0
            
            # Display totals
            print(f"Total amount: {total_amount} Pesos")
            print(f"Pulse history: {pulse_sequence}")
            
        time.sleep(0.1)  # Sleep to reduce CPU usage

except KeyboardInterrupt:
    print(f"Program ended. Total amount: {total_amount} Pesos")
    print(f"Pulse sequence history: {pulse_sequence}")
    GPIO.cleanup()