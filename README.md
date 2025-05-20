# Vending Machine Project

This project implements a vending machine system using a Raspberry Pi. The system handles coin detection, inventory management, relay activation, and communication with Firebase. It also manages an LCD display and user input.

## Project Files

- **coinslot.py**: Contains the main logic for the vending machine. It handles:
  - Coin detection
  - Inventory management
  - Relay activation
  - Communication with Firebase
  - LCD display management
  - User input handling

- **vendo.service**: A systemd service configuration file that allows the vending machine script to run automatically on startup. It includes:
  - Service type
  - Command to execute the script
  - Dependencies

## Setup Instructions

1. **Install Required Packages**:
   Ensure that you have the necessary packages installed on your Raspberry Pi. You may need to install libraries for GPIO, Firebase communication, and the LCD display.

2. **Copy the Script**:
   Place the `coinslot.py` script in the `/home/pi/Desktop/vendo/` directory.

3. **Create the Systemd Service**:
   Create the `vendo.service` file in the `/etc/systemd/system/` directory with the following content:

   ```
   [Unit]
   Description=Vending Machine Service
   After=network.target

   [Service]
   ExecStart=/usr/bin/python3 /home/pi/Desktop/vendo/coinslot.py
   WorkingDirectory=/home/pi/Desktop/vendo
   StandardOutput=inherit
   StandardError=inherit
   Restart=always
   User=pi

   [Install]
   WantedBy=multi-user.target
   ```

4. **Enable the Service**:
   Run the following commands to enable the service to start on boot:

   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable vendo.service
   ```

5. **Start the Service**:
   You can start the service immediately with:

   ```bash
   sudo systemctl start vendo.service
   ```

6. **Check the Service Status**:
   To check if the service is running correctly, use:

   ```bash
   sudo systemctl status vendo.service
   ```

## Notes

- Ensure that the Raspberry Pi has access to the internet for Firebase communication.
- Make sure to handle any dependencies required by the `coinslot.py` script.
- Adjust the paths in the service file if your setup differs from the default.