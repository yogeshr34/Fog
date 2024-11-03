from machine import Pin, ADC
import network
import socket
import time
# Voltage Sensor Configuration
voltage_adc_pin = ADC(Pin(34))  # Adjust GPIO pin as needed
voltage_adc_pin.atten(ADC.ATTN_11DB)  # Set attenuation to read up to 3.3V
# Voltage Divider Resistor Values
R1 = 30000.0  # Resistor R1 in ohms (30k)
R2 = 7500.0   # Resistor R2 in ohms (7.5k)
V_REF = 3.3   # Reference voltage for ADC (3.3V for ESP32)
ADC_MAX_VALUE = 4095  # 12-bit ADC
# Current Sensor Configuration (ACS712)
current_adc_pin = ADC(Pin(33))  # Adjust GPIO pin as needed
current_adc_pin.atten(ADC.ATTN_11DB)
SENSITIVITY = 185  # Sensitivity in mV per A for ACS712-5A (use 100 for 20A, 66 for 30A)
V_ZERO = V_REF / 2  # Adjusted later during calibration if necessary
# Web Server Configuration
ssid = 'ESP32-AP'
password = '12345678'
def calibrate_zero():
    # Calibrate zero current for ACS712
    total = 0
    samples = 100
    for _ in range(samples):
        total += current_adc_pin.read()
        time.sleep(0.01)
    zero_adc_value = total / samples
    return (zero_adc_value / ADC_MAX_VALUE) * V_REF
# Set the midpoint voltage based on calibration
V_ZERO = calibrate_zero()
def read_voltage():
    # Read and calculate voltage
    adc_value = voltage_adc_pin.read()
    adc_voltage = (adc_value * V_REF) / ADC_MAX_VALUE
    in_voltage = adc_voltage / (R2 / (R1 + R2))
    return in_voltage
def read_current():
    # Read and calculate current
    adc_value = current_adc_pin.read()
    voltage = (adc_value / ADC_MAX_VALUE) * V_REF
    current = (voltage - V_ZERO) * 1000 / SENSITIVITY  # Convert mV to A
    return current
# Initialize Access Point
ap = network.WLAN(network.AP_IF)
ap.config(essid=ssid, password=password)
ap.active(True)
# Wait for connection
while not ap.active():
    pass
print('Access Point established with IP:', ap.ifconfig()[0])

# Set up Web Server
def web_page():
    voltage = read_voltage()
    current = read_current()

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>ESP32 Sensor Readings</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{ font-family: Arial; text-align: center; }}
            h2 {{ color: #333; }}
            p {{ font-size: 1.2em; }}
        </style>
        <script>
            setInterval(function() {{
                location.reload();
            }}, 2000);  // Refresh every 2 seconds
        </script>
    </head>
    <body>
        <h2>ESP32 Voltage and Current Sensor</h2>
        <p><strong>Voltage:</strong> {voltage:.2f} V</p>
        <p><strong>Current:</strong> {current:.2f} A</p>
    </body>
    </html>
    """
    return html

# Start Server
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(('', 80))
s.listen(5)

print("Web server started. Connect to the AP and visit:", ap.ifconfig()[0])

while True:
    conn, addr = s.accept()
    print("Got a connection from", addr)
    request = conn.recv(1024)
    response = web_page()
    conn.send('HTTP/1.1 200 OK\nContent-Type: text/html\nConnection: close\n\n')
    conn.sendall(response)
    conn.close()
