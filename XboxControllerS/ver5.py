import uinput
import evdev
import threading
import time
from collections import deque

# List all devices (debug)
print("Detected input devices:")
devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
for d in devices:
    print(f"{d.path}: {d.name}")

def find_keyboard():
    for d in devices:
        caps = d.capabilities()
        if evdev.ecodes.EV_KEY in caps:
            keys = caps[evdev.ecodes.EV_KEY]
            if evdev.ecodes.KEY_A in keys and evdev.ecodes.KEY_Z in keys:
                print(f"Selected keyboard: {d.name} at {d.path}")
                return d
    return None

def find_mouse():
    for d in devices:
        caps = d.capabilities()
        if evdev.ecodes.EV_REL in caps and evdev.ecodes.EV_KEY in caps:
            rels = caps[evdev.ecodes.EV_REL]
            keys = caps[evdev.ecodes.EV_KEY]
            if evdev.ecodes.REL_X in rels and evdev.ecodes.REL_Y in rels and evdev.ecodes.BTN_LEFT in keys:
                print(f"Selected mouse: {d.name} at {d.path}")
                return d
    return None

keyboard = find_keyboard()
mouse = find_mouse()

if not keyboard or not mouse:
    print("Could not find keyboard or mouse input devices")
    exit(1)

print(f"Using keyboard: {keyboard.name} at {keyboard.path}")
print(f"Using mouse: {mouse.name} at {mouse.path}")

device_events = (
    uinput.BTN_A, uinput.BTN_B, uinput.BTN_X, uinput.BTN_Y,
    uinput.BTN_TL, uinput.BTN_TR,
    uinput.BTN_START, uinput.BTN_SELECT,
    uinput.ABS_X + (0, 255, 0, 0),  # Left stick X
    uinput.ABS_Y + (0, 255, 0, 0),  # Left stick Y
    uinput.ABS_RX + (0, 255, 0, 0), # Right stick X (mouse)
    uinput.ABS_RY + (0, 255, 0, 0), # Right stick Y (mouse)
    uinput.ABS_Z + (0, 255, 0, 0),  # Left trigger (mouse left click)
    uinput.ABS_RZ + (0, 255, 0, 0), # Right trigger (mouse right click)
    uinput.BTN_DPAD_UP, uinput.BTN_DPAD_DOWN,
    uinput.BTN_DPAD_LEFT, uinput.BTN_DPAD_RIGHT,
)

device = uinput.Device(device_events, name="Virtual Xbox Controller")

left_x, left_y = 128, 128
right_x, right_y = 128, 128
left_trigger = 0
right_trigger = 0

# Clamp helper
def clamp(v):
    return max(0, min(255, v))

# Track currently held keys to avoid processing autorepeat repeats multiple times
held_keys = set()

# Sensitivity toggle states
mouse_sensitivity_high = 5
mouse_sensitivity_low = 2
current_sensitivity = mouse_sensitivity_high
sensitivity_toggle = False

# Moving average filter for mouse smoothing
class MovingAverage:
    def __init__(self, size=5):
        self.size = size
        self.xs = deque(maxlen=size)
        self.ys = deque(maxlen=size)

    def add(self, dx, dy):
        self.xs.append(dx)
        self.ys.append(dy)

    def average(self):
        if not self.xs or not self.ys:
            return 0, 0
        avg_x = sum(self.xs) / len(self.xs)
        avg_y = sum(self.ys) / len(self.ys)
        return avg_x, avg_y

smoother = MovingAverage()

def keyboard_thread():
    global left_x, left_y, sensitivity_toggle, current_sensitivity
    for event in keyboard.read_loop():
        if event.type == evdev.ecodes.EV_KEY:
            ev = evdev.categorize(event)
            key = ev.keycode if isinstance(ev.keycode, str) else ev.keycode
            pressed = ev.keystate == evdev.KeyEvent.key_down or ev.keystate == evdev.KeyEvent.key_hold

            # Debounce key autorepeat — only process when state changes
            if pressed:
                if key in held_keys:
                    continue
                held_keys.add(key)
            else:
                if key not in held_keys:
                    continue
                held_keys.remove(key)

            # Toggle mouse sensitivity on key 'KEY_Z'
            if key == 'KEY_Z' and pressed:
                sensitivity_toggle = not sensitivity_toggle
                current_sensitivity = mouse_sensitivity_low if sensitivity_toggle else mouse_sensitivity_high
                print(f"Mouse sensitivity toggled to {'low' if sensitivity_toggle else 'high'} ({current_sensitivity})")
                continue  # Don't map Z key to controller

            # Map keyboard keys to Xbox buttons
            if key == 'KEY_SPACE':        # A button mapped to Space
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
            elif key == 'KEY_S':          # Down
                left_y = 255 if pressed else 128
                device.emit(uinput.ABS_Y, left_y, syn=False)
                device.syn()
            elif key == 'KEY_W':          # Up
                left_y = 0 if pressed else 128
                device.emit(uinput.ABS_Y, left_y, syn=False)
                device.syn()
            elif key == 'KEY_A':          # Left
                left_x = 0 if pressed else 128
                device.emit(uinput.ABS_X, left_x, syn=False)
                device.syn()
            elif key == 'KEY_D':          # Right
                left_x = 255 if pressed else 128
                device.emit(uinput.ABS_X, left_x, syn=False)
                device.syn()

def mouse_thread():
    global right_x, right_y, left_trigger, right_trigger

    for event in mouse.read_loop():
        if event.type == evdev.ecodes.EV_REL:
            dx, dy = 0, 0
            if event.code == evdev.ecodes.REL_X:
                dx = event.value * current_sensitivity
            elif event.code == evdev.ecodes.REL_Y:
                dy = event.value * current_sensitivity

            smoother.add(dx, dy)
            avg_dx, avg_dy = smoother.average()

            right_x = clamp(right_x + int(avg_dx))
            right_y = clamp(right_y + int(avg_dy))

            device.emit(uinput.ABS_RX, right_x, syn=False)
            device.emit(uinput.ABS_RY, right_y, syn=False)
            device.syn()

            # Clear buffer after applying
            smoother.xs.clear()
            smoother.ys.clear()

        elif event.type == evdev.ecodes.EV_KEY:
            if event.code == evdev.ecodes.BTN_LEFT:
                left_trigger = 255 if event.value == 1 else 0
                device.emit(uinput.ABS_Z, left_trigger)
            elif event.code == evdev.ecodes.BTN_RIGHT:
                right_trigger = 255 if event.value == 1 else 0
                device.emit(uinput.ABS_RZ, right_trigger)

# Initialize sticks/triggers center
device.emit(uinput.ABS_X, 128)
device.emit(uinput.ABS_Y, 128)
device.emit(uinput.ABS_RX, 128)
device.emit(uinput.ABS_RY, 128)
device.emit(uinput.ABS_Z, 0)
device.emit(uinput.ABS_RZ, 0)
device.syn()

threading.Thread(target=keyboard_thread, daemon=True).start()
threading.Thread(target=mouse_thread, daemon=True).start()

print("Virtual Xbox controller running.")
print("Press Z to toggle mouse sensitivity.")
print("Ctrl+C to exit.")

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Exiting.")
