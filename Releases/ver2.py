import uinput
import evdev
import threading
import time

# Print all input devices detected by evdev for debugging
print("Listing all input devices found by evdev:")
devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
for device in devices:
    print(f"{device.path}: {device.name} ({device.phys})")

# More robust device finder that returns device if keyword found (case insensitive) in name
def find_device(keyword):
    devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
    for dev in devices:
        # Debug print to see checked device names
        print(f"Checking device: {dev.name}")
        if keyword.lower() in dev.name.lower():
            return dev
    return None

# Try common keywords and fallback options based on actual device names seen above
keyboard = find_device("keyboard") or find_device("Keyboard") or find_device("AT Translated") or find_device("Dell")
mouse = find_device("mouse") or find_device("Mouse") or find_device("Logitech") or find_device("USB Optical")

if not keyboard or not mouse:
    print("Could not find keyboard or mouse input devices")
    exit(1)

print(f"Using keyboard device: {keyboard.name} at {keyboard.path}")
print(f"Using mouse device: {mouse.name} at {mouse.path}")

# Create uinput device with Xbox controller buttons + axes
device_events = (
    uinput.BTN_A,
    uinput.BTN_B,
    uinput.BTN_X,
    uinput.BTN_Y,
    uinput.BTN_TL,  # LB
    uinput.BTN_TR,  # RB
    uinput.BTN_START,
    uinput.BTN_SELECT,
    uinput.ABS_X + (0, 255, 0, 0),    # Left stick X
    uinput.ABS_Y + (0, 255, 0, 0),    # Left stick Y
    uinput.ABS_RX + (0, 255, 0, 0),   # Right stick X (mouse X)
    uinput.ABS_RY + (0, 255, 0, 0),   # Right stick Y (mouse Y)
    uinput.ABS_Z + (0, 255, 0, 0),    # Left trigger (mouse left click)
    uinput.ABS_RZ + (0, 255, 0, 0),   # Right trigger (mouse right click)
    # D-pad buttons
    uinput.BTN_DPAD_UP,
    uinput.BTN_DPAD_DOWN,
    uinput.BTN_DPAD_LEFT,
    uinput.BTN_DPAD_RIGHT,
)

device = uinput.Device(device_events, name="Virtual Xbox Controller")

# Center values for sticks and triggers
left_x = 128
left_y = 128
right_x = 128
right_y = 128
left_trigger = 0
right_trigger = 0

# Helper to clamp values between 0 and 255
def clamp(value):
    return max(0, min(255, value))

# Keyboard input thread
def keyboard_thread():
    global left_x, left_y
    for event in keyboard.read_loop():
        if event.type == evdev.ecodes.EV_KEY:
            ev = evdev.categorize(event)
            key = ev.keycode if isinstance(ev.keycode, str) else ev.keycode[0]
            pressed = ev.keystate == evdev.KeyEvent.key_down

            # Map keyboard keys to Xbox buttons
            if key == 'KEY_SPACE':        # A button mapped to Space key now
                device.emit(uinput.BTN_A, pressed)
            elif key == 'KEY_B':
                device.emit(uinput.BTN_B, pressed)
            elif key == 'KEY_X':
                device.emit(uinput.BTN_X, pressed)
            elif key == 'KEY_Y':
                device.emit(uinput.BTN_Y, pressed)
            elif key == 'KEY_E':          # LB
                device.emit(uinput.BTN_TL, pressed)
            elif key == 'KEY_R':          # RB
                device.emit(uinput.BTN_TR, pressed)
            elif key == 'KEY_ENTER':      # Start
                device.emit(uinput.BTN_START, pressed)
            elif key == 'KEY_BACKSPACE':  # Back
                device.emit(uinput.BTN_SELECT, pressed)
            elif key == 'KEY_UP':
                device.emit(uinput.BTN_DPAD_UP, pressed)
            elif key == 'KEY_DOWN':
                device.emit(uinput.BTN_DPAD_DOWN, pressed)
            elif key == 'KEY_LEFT':
                device.emit(uinput.BTN_DPAD_LEFT, pressed)
            elif key == 'KEY_RIGHT':
                device.emit(uinput.BTN_DPAD_RIGHT, pressed)

            # Left thumbstick controls
            elif key == 'KEY_S':          # Left stick down
                left_y = 255 if pressed else 128
                device.emit(uinput.ABS_Y, left_y, syn=False)
                device.syn()
            elif key == 'KEY_W':          # Left stick up
                left_y = 0 if pressed else 128
                device.emit(uinput.ABS_Y, left_y, syn=False)
                device.syn()
            elif key == 'KEY_A':          # Left stick left (going backward)
                left_x = 0 if pressed else 128
                device.emit(uinput.ABS_X, left_x, syn=False)
                device.syn()
            elif key == 'KEY_D':          # Left stick right
                left_x = 255 if pressed else 128
                device.emit(uinput.ABS_X, left_x, syn=False)
                device.syn()

# Mouse input thread
def mouse_thread():
    global right_x, right_y, left_trigger, right_trigger

    sensitivity = 5

    for event in mouse.read_loop():
        if event.type == evdev.ecodes.EV_REL:
            if event.code == evdev.ecodes.REL_X:
                right_x = clamp(right_x + event.value * sensitivity)
                device.emit(uinput.ABS_RX, right_x, syn=False)
            elif event.code == evdev.ecodes.REL_Y:
                right_y = clamp(right_y + event.value * sensitivity)
                device.emit(uinput.ABS_RY, right_y, syn=False)
            device.syn()

        elif event.type == evdev.ecodes.EV_KEY:
            if event.code == evdev.ecodes.BTN_LEFT:
                left_trigger = 255 if event.value == 1 else 0
                device.emit(uinput.ABS_Z, left_trigger)
            elif event.code == evdev.ecodes.BTN_RIGHT:
                right_trigger = 255 if event.value == 1 else 0
                device.emit(uinput.ABS_RZ, right_trigger)

# Initialize center positions for sticks and triggers
device.emit(uinput.ABS_X, 128)
device.emit(uinput.ABS_Y, 128)
device.emit(uinput.ABS_RX, 128)
device.emit(uinput.ABS_RY, 128)
device.emit(uinput.ABS_Z, 0)
device.emit(uinput.ABS_RZ, 0)
device.syn()

# Start input threads
threading.Thread(target=keyboard_thread, daemon=True).start()
threading.Thread(target=mouse_thread, daemon=True).start()

print("Virtual Xbox controller running - mouse moves right thumbstick and triggers (left/right click), keyboard for buttons.")
print("Press Ctrl+C to exit.")

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Exiting.")
