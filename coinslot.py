import RPi.GPIO as GPIO
import time

# GPIO setup
COIN_PIN = 17  # GPIO pin connected to the coin acceptor pulse output
                # Change this to match your actual GPIO pin connection

# Set up GPIO mode
GPIO.setmode(GPIO.BCM)
GPIO.setup(COIN_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Variables
total_amount = 0
pulse_count = 0
last_pulse_time = time.time()
pulse_timeout = 1.0  # Time window to group pulses (1 second)
last_state = GPIO.input(COIN_PIN)
debounce_time = 0.05  # 50ms debounce time

print("Coin Counter Started")
print("Insert coins to see the count")

try:
    while True:
        # Read current state
        current_state = GPIO.input(COIN_PIN)
        current_time = time.time()
        
        # Check if state changed (pulse detected)
        if current_state != last_state:
            # Wait for debounce
            time.sleep(debounce_time)
            
            # Read again after debounce
            current_state = GPIO.input(COIN_PIN)
            
            # If still different from last_state, we have a valid change
            if current_state != last_state:
                # Depending on your coin acceptor, you might need to detect
                # falling edge (1->0) or rising edge (0->1)
                if last_state == 1 and current_state == 0:  # Falling edge
                    pulse_count += 1
                    last_pulse_time = current_time
                    print(f"Pulse detected! Current pulse count: {pulse_count}")
                
                # Update last state
                last_state = current_state
        
        # Check if we should process the pulses (timeout reached)
        if pulse_count > 0 and (current_time - last_pulse_time) > pulse_timeout:
            # Determine coin type based on pulse count
            if pulse_count == 1:
                coin_value = 1
                coin_type = "1 Peso"
            elif pulse_count == 5:
                coin_value = 5
                coin_type = "5 Pesos"
            elif pulse_count == 10:
                coin_value = 10
                coin_type = "10 Pesos"
            else:
                coin_value = 0
                coin_type = "Unknown coin"
                print(f"Warning: Received {pulse_count} pulses, which doesn't match any known coin.")
            
            # Update total amount if it's a recognized coin
            if coin_value > 0:
                total_amount += coin_value
                print(f"Coin detected: {coin_type}")
                print(f"Total amount: {total_amount} Pesos")
            
            # Reset pulse counter for next coin
            pulse_count = 0
        
        # Small delay to reduce CPU usage
        time.sleep(0.01)

except KeyboardInterrupt:
    print(f"Program ended. Total amount collected: {total_amount} Pesos")
    GPIO.cleanup()