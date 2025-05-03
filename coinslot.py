import RPi.GPIO as GPIO
import time

# Clean up any previous GPIO setups
GPIO.cleanup()

# Configure GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

COIN_PIN = 17  # Adjust this to match your connection
GPIO.setup(COIN_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

total_value = 0.0
pulse_count = 0
last_pulse_time = 0

# Define coin values (adjust these based on your calibration)
# Number of pulses : coin value
coin_values = {
    1: 0.25,  # Quarter or whatever denomination you program
    2: 0.50,
    3: 1.00
}

try:
    print("Coin detector active. Insert coins...")
    last_state = GPIO.input(COIN_PIN)
    
    while True:
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
                        print(f"Coin detected: ${coin_value:.2f}, Total: ${total_value:.2f}")
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
                print(f"Coin detected: ${coin_value:.2f}, Total: ${total_value:.2f}")
            else:
                print(f"Unknown coin: {pulse_count} pulses")
            pulse_count = 0
            
        time.sleep(0.01)  # Reduce CPU usage

except KeyboardInterrupt:
    GPIO.cleanup()
    print("Program ended.")