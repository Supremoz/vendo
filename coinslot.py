import RPi.GPIO as GPIO
import time

# GPIO setup
COIN_PINS = [17, 27]  # Example: GPIO17 and GPIO27 for two coin acceptors

# Coin values for each acceptor (by pulses)
COIN_VALUES = [
    {1: 1, 5: 5, 10: 10},    # Coin acceptor 1
    {2: 2, 4: 5, 8: 10}      # Coin acceptor 2 (example pulse mapping)
]

# Set up GPIO mode
GPIO.setmode(GPIO.BCM)
for pin in COIN_PINS:
    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Variables
total_amount = 0
pulse_counts = [0] * len(COIN_PINS)
last_states = [GPIO.input(pin) for pin in COIN_PINS]
last_pulse_times = [time.time()] * len(COIN_PINS)
pulse_timeout = 2.0  # seconds

print("Multi Coin Counter Started")
print("Insert coins to see the count")

try:
    while True:
        current_time = time.time()
        for idx, pin in enumerate(COIN_PINS):
            current_state = GPIO.input(pin)
            # Detect state change (falling edge)
            if current_state != last_states[idx]:
                time.sleep(0.05)  # debounce
                current_state = GPIO.input(pin)
                if last_states[idx] == 1 and current_state == 0:
                    pulse_counts[idx] += 1
                    last_pulse_times[idx] = current_time
                    print(f"Acceptor {idx+1}: Pulse detected! Count: {pulse_counts[idx]}")
                last_states[idx] = current_state

            # Process pulses if timeout reached
            if pulse_counts[idx] > 0 and (current_time - last_pulse_times[idx]) > pulse_timeout:
                if pulse_counts[idx] in COIN_VALUES[idx]:
                    coin_value = COIN_VALUES[idx][pulse_counts[idx]]
                    total_amount += coin_value
                    print(f"Acceptor {idx+1}: {pulse_counts[idx]} pulses = {coin_value} Pesos")
                else:
                    print(f"Acceptor {idx+1}: Unknown coin pattern: {pulse_counts[idx]} pulses")
                pulse_counts[idx] = 0
                print(f"Total amount: {total_amount} Pesos")
        time.sleep(0.01)

except KeyboardInterrupt:
    print(f"Program ended. Total amount: {total_amount} Pesos")
    GPIO.cleanup()