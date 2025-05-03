#!/usr/bin/env python3
"""
Raspberry Pi Napkin Vending Machine
Controls a vending machine that dispenses two types of napkins
(regular and with wings) using motors, buttons, and IR sensors.
Includes coin slot functionality:
- 1 pulse = 1 peso
- 5 pulses = 5 pesos
- 10 pulses = 10 pesos
"""

import RPi.GPIO as GPIO
import smbus
import time
import threading
from RPLCD.i2c import CharLCD

# Pin Definitions (BCM numbering)
BUTTON_WINGS = 2         # Button for selecting napkin with wings
BUTTON_REGULAR = 3       # Button for selecting regular napkin
MOTOR_WINGS = 4          # Relay for controlling motor for napkins with wings
MOTOR_REGULAR = 5        # Relay for controlling motor for regular napkins
IR_SENSOR_WINGS = 6      # IR sensor for detecting napkin with wings dispensed
IR_SENSOR_REGULAR = 7    # IR sensor for detecting regular napkin dispensed
COIN_SLOT = 8            # Single coin slot sensor for all coin types

# LCD Setup
I2C_ADDR = 0x27  # I2C device address
I2C_BUS = 1      # Typically 1 on newer Raspberry Pi models

# Global variables
credit = 0
dispensing = False
coin_open = False  # Track if the coin input mode is active

# Coin slot variables
coin_pulse_count = 0
last_coin_time = 0
last_coin_process_time = 0
COIN_DEBOUNCE_TIME = 0.05   # 50ms debounce for coin slot
COIN_TIMEOUT = 1.0         # 1000ms timeout for pulse sequence

# Lock for thread safety
pulse_lock = threading.Lock()

# Initialize LCD
try:
    lcd = CharLCD(i2c_expander='PCF8574', address=I2C_ADDR, port=I2C_BUS,
                  cols=16, rows=2, backlight_enabled=True)
except Exception as e:
    print(f"LCD initialization error: {e}")
    # If LCD fails, create a dummy LCD to prevent crashes
    class DummyLCD:
        def clear(self): pass
        def cursor_pos(self, pos): pass
        def write_string(self, text): 
            print(f"LCD: {text}")
    lcd = DummyLCD()

def setup():
    """Initialize GPIO and setup pins"""
    # Set GPIO mode
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    
    # Setup pin modes
    GPIO.setup(BUTTON_WINGS, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(BUTTON_REGULAR, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(MOTOR_WINGS, GPIO.OUT)
    GPIO.setup(MOTOR_REGULAR, GPIO.OUT)
    GPIO.setup(IR_SENSOR_WINGS, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(IR_SENSOR_REGULAR, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(COIN_SLOT, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    
    # Set up interrupt handler for coin slot
    GPIO.add_event_detect(COIN_SLOT, GPIO.FALLING, callback=coin_slot_callback, bouncetime=50)
    
    # Initialize outputs to OFF (relays are active LOW)
    GPIO.output(MOTOR_WINGS, GPIO.HIGH)
    GPIO.output(MOTOR_REGULAR, GPIO.HIGH)
    
    # Initialize LCD display
    lcd.clear()
    lcd.cursor_pos = (0, 0)
    lcd.write_string("Napkin Vending")
    lcd.cursor_pos = (1, 0)
    lcd.write_string("Machine Ready")
    time.sleep(2)
    
    update_lcd()
    
    # Print instructions to console
    print("Napkin Vending Machine Ready")
    print("Insert coins (pulses represent coin value)")
    print("1 pulse = 1 peso")
    print("5 pulses = 5 pesos")
    print("10 pulses = 10 pesos")
    print("Or type a number to add credits manually")
    print("Enter 'nap-1' to dispense napkin with wings")
    print("Enter 'nap-2' to dispense regular napkin")
    print("10 credits are required to dispense a napkin")

def update_lcd():
    """Update LCD display with current status"""
    lcd.clear()
    lcd.cursor_pos = (0, 0)
    lcd.write_string(f"Credit: {credit} Pesos")
    
    lcd.cursor_pos = (1, 0)
    if credit >= 10:
        lcd.write_string("nap-1:W nap-2:R")
    else:
        lcd.write_string("Insert coins...")

def dispense_wings():
    """Function to dispense napkin with wings"""
    global dispensing, credit
    
    if dispensing or credit < 10:
        return
    
    dispensing = True
    credit -= 10
    update_lcd()
    
    lcd.clear()
    lcd.cursor_pos = (0, 0)
    lcd.write_string("Dispensing...")
    lcd.cursor_pos = (1, 0)
    lcd.write_string("nap-1: Wings")
    
    # Start motor
    GPIO.output(MOTOR_WINGS, GPIO.LOW)  # Activate relay (active LOW)
    
    # Wait for napkin to be detected or timeout
    start_time = time.time()
    timeout = 10  # 10 seconds timeout
    napkin_detected = False
    
    while time.time() - start_time < timeout and not napkin_detected:
        if GPIO.input(IR_SENSOR_WINGS) == GPIO.LOW:  # Object detected
            napkin_detected = True
            time.sleep(0.5)  # Let motor complete rotation
        time.sleep(0.1)
    
    # Stop motor
    GPIO.output(MOTOR_WINGS, GPIO.HIGH)  # Deactivate relay
    
    if napkin_detected:
        lcd.clear()
        lcd.cursor_pos = (0, 0)
        lcd.write_string("Thank you!")
        time.sleep(2)
    else:
        lcd.clear()
        lcd.cursor_pos = (0, 0)
        lcd.write_string("Error: Timeout")
        time.sleep(2)
        # Refund credit if napkin not dispensed
        credit += 10
    
    dispensing = False
    update_lcd()

def dispense_regular():
    """Function to dispense regular napkin"""
    global dispensing, credit
    
    if dispensing or credit < 10:
        return
    
    dispensing = True
    credit -= 10
    update_lcd()
    
    lcd.clear()
    lcd.cursor_pos = (0, 0)
    lcd.write_string("Dispensing...")
    lcd.cursor_pos = (1, 0)
    lcd.write_string("nap-2: Regular")
    
    # Start motor
    GPIO.output(MOTOR_REGULAR, GPIO.LOW)  # Activate relay (active LOW)
    
    # Wait for napkin to be detected or timeout
    start_time = time.time()
    timeout = 10  # 10 seconds timeout
    napkin_detected = False
    
    while time.time() - start_time < timeout and not napkin_detected:
        if GPIO.input(IR_SENSOR_REGULAR) == GPIO.LOW:  # Object detected
            napkin_detected = True
            time.sleep(0.5)  # Let motor complete rotation
        time.sleep(0.1)
    
    # Stop motor
    GPIO.output(MOTOR_REGULAR, GPIO.HIGH)  # Deactivate relay
    
    if napkin_detected:
        lcd.clear()
        lcd.cursor_pos = (0, 0)
        lcd.write_string("Thank you!")
        time.sleep(2)
    else:
        lcd.clear()
        lcd.cursor_pos = (0, 0)
        lcd.write_string("Error: Timeout")
        time.sleep(2)
        # Refund credit if napkin not dispensed
        credit += 10
    
    dispensing = False
    update_lcd()

def coin_slot_callback(channel):
    """Interrupt callback for coin slot pulses"""
    global coin_pulse_count, last_coin_time, last_coin_process_time
    
    current_time = time.time()
    # Increment coin pulse count if debounce time has passed
    if current_time - last_coin_time > COIN_DEBOUNCE_TIME:
        with pulse_lock:
            coin_pulse_count += 1
            last_coin_time = current_time
            last_coin_process_time = current_time  # Reset the timeout timer

def handle_coin_slot():
    """Process coin slot pulses and update credit"""
    global coin_pulse_count, credit
    
    current_time = time.time()
    
    # If we have pulses and the timeout has occurred, process them
    if coin_pulse_count > 0 and (current_time - last_coin_time > COIN_TIMEOUT):
        with pulse_lock:
            # Determine coin value based on pulse count
            coin_value = 0
            coin_type = ""
            
            if coin_pulse_count == 1:
                coin_value = 1
                coin_type = "1 peso"
            elif 4 <= coin_pulse_count <= 6:  # Allow for slight variations
                coin_value = 5
                coin_type = "5 pesos"
            elif 9 <= coin_pulse_count <= 11:  # Allow for slight variations
                coin_value = 10
                coin_type = "10 pesos"
            else:
                # Invalid pulse count
                print(f"Invalid coin pulse count: {coin_pulse_count}")
                coin_pulse_count = 0
                return
            
            # Add credit and update display
            credit += coin_value
            print(f"{coin_type} coin detected ({coin_pulse_count} pulses)")
            update_lcd()
            
            # Reset pulse count
            coin_pulse_count = 0

def process_command(command):
    """Process commands from console input"""
    global credit, coin_open
    
    command = command.strip()
    
    # Check for coin-open command
    if command.lower() == "coin-open":
        coin_open = not coin_open
        if coin_open:
            print("Coin slot opened. Type a number to add credits.")
        else:
            print("Coin slot closed.")
        return
    
    # Check for debug command to simulate coin insertions
    if command.startswith("coin"):
        coin_value_str = command[4:].strip()
        
        try:
            value = int(coin_value_str)
            if value in [1, 5, 10]:
                print(f"Simulating {value} peso coin insertion with pulses")
                
                # Simulate the correct number of pulses
                pulses_to_simulate = 0
                
                if value == 1:
                    pulses_to_simulate = 1
                elif value == 5:
                    pulses_to_simulate = 5
                elif value == 10:
                    pulses_to_simulate = 10
                
                # Add the pulses
                global coin_pulse_count, last_coin_time
                with pulse_lock:
                    coin_pulse_count += pulses_to_simulate
                    last_coin_time = time.time()
            else:
                print("Invalid coin value. Use 1, 5, or 10.")
        except ValueError:
            print("Invalid command format. Use 'coin1', 'coin5', or 'coin10'.")
        return
    
    # Handle numeric input for manual credits
    if command.isdigit():
        value = int(command)
        credit += value
        update_lcd()
        print(f"Added {value} pesos. Current credit: {credit}")
        return
    
    # Handle napkin selection commands
    if command.lower() == "nap-1" and credit >= 10 and not dispensing:
        dispense_wings()
    elif command.lower() == "nap-2" and credit >= 10 and not dispensing:
        dispense_regular()
    else:
        print("Invalid input. Use number to add credit or 'nap-1'/'nap-2' to select napkin type.")

def input_thread_function():
    """Thread function to handle user input"""
    while True:
        try:
            command = input()
            process_command(command)
        except EOFError:
            break
        except Exception as e:
            print(f"Input error: {e}")

def main():
    """Main function"""
    try:
        # Setup hardware
        setup()
        
        # Start input thread
        input_thread = threading.Thread(target=input_thread_function, daemon=True)
        input_thread.start()
        
        # Main loop
        while True:
            # Check physical buttons
            if GPIO.input(BUTTON_WINGS) == GPIO.LOW and credit >= 10 and not dispensing:
                dispense_wings()
                time.sleep(0.3)  # Debounce
            
            if GPIO.input(BUTTON_REGULAR) == GPIO.LOW and credit >= 10 and not dispensing:
                dispense_regular()
                time.sleep(0.3)  # Debounce
            
            # Process any coin slot pulses
            handle_coin_slot()
            
            # Small delay to prevent CPU hogging
            time.sleep(0.05)
            
    except KeyboardInterrupt:
        print("\nExiting program")
    finally:
        # Clean up GPIO
        GPIO.cleanup()

if __name__ == "__main__":
    main()