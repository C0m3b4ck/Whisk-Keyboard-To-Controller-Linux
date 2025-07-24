import uinput
import evdev
import threading
import time

# List devices for debug
devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
print("Detected input devices:")
for d in devices:
    print(f"{d.path}: {d.name}")

# Improved device detection by capabilities

def find_keyboard():
    for dev in devices:
        caps = dev.capabilities()
        if evdev.ecodes.EV_KEY in caps:
            keys = caps[evdev.ecodes.EV_KEY]
            if evdev.ecodes.KEY_A in keys and evdev.ecodes.KEY_Z in keys:
                print(f"Selected keyboard: {dev.name} at {dev.path}")
                return dev
    return None

def find_mouse():
    for dev in devices:
        caps = dev.capabilities()
        if evdev.ecodes.EV_REL in caps and evdev.ecodes.EV_KEY in caps:
            rels = caps[evdev.ecodes.EV_REL]
            keys = caps[evdev.ecodes.EV_KEY]
            if evdev.ecodes.REL_X in rels and evdev.ecodes.REL_Y in rels and evdev.ecodes.BTN_LEFT in keys:
                print(f"Selected mouse: {dev.name} at {dev.path}")
                return dev
    return None

keyboard = find_keyboard()
mouse = find_mouse()

if not keyboard or not mouse:
    print("Could not find keyboard or mouse input devices")
    exit(1)

print(f"Using keyboard device: {keyboard.name} at {keyboard.path}")
print(f"Using mouse device: {mouse.name} at {mouse.path}")

# Create virtual device
device_events = (
    uinput.BTN_A,
    uinput.BTN_B,
    uinput.BTN_X,
    uinput.BTN_Y,
    uinput.BTN_TL,
    uinput.BTN_TR,
    uinput.BTN_START,
    uinput.BTN_SELECT,
    uinput.ABS_X + (0, 255, 0, 0),
    uinput.ABS_Y + (0, 255, 0, 0),
    uinput.ABS_RX + (0, 255, 0, 0),
    uinput.ABS_RY + (0, 255, 0, 0),
    uinput.ABS_Z + (0, 255, 0, 0),
    uinput.ABS_RZ + (0, 255, 0, 0),
    uinput.BTN_DPAD_UP,
    uinput.BTN_DPAD_DOWN,
    uinput.BTN_DPAD_LEFT,
    uinput.BTN_DPAD_RIGHT,
)

device = uinput.Device(device_events, name="Virtual Xbox Controller")

# Initial stick & trigger states
left_x, left_y = 128, 128
right_x, right_y = 128, 128
left_trigger, right_trigger = 0, 0

# For debouncing keys (hold vs autorepeat)
held_keys = set()

# Helper clamp
def clamp(v):
    return max(0, min(255, v))

# Keyboard input thread
def keyboard_thread():
    global left_x, left_y
    for event in keyboard.read_loop():
        if event.type == evdev.ecodes.EV_KEY:
            ev = evdev.categorize(event)
            key = ev.keycode if isinstance(ev.keycode, str) else ev.keycode[0]
            pressed = ev.keystate == evdev.KeyEvent.key_down or ev.keystate == evdev.KeyEvent.key_hold

            # Skip repeats if key already held down (for buttons that need it)
            if pressed:
                if key in held_keys:
                    continue
                else:
                    held_keys.add(key)
            else:
                if key in held_keys:
                    held_keys.remove(key)
                else:
                    continue

            # Map keyboard keys to Xbox buttons
            if key == 'KEY_SPACE':        # A
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
            elif key == 'KEY_S':          # down
                left_y = 255 if pressed else 128
                device.emit(uinput.ABS_Y, left_y, syn=False)
                device.syn()
            elif key == 'KEY_W':          # up
                left_y = 0 if pressed else 128
                device.emit(uinput.ABS_Y, left_y, syn=False)
                device.syn()
            elif key == 'KEY_A':          # left
                left_x = 0 if pressed else 128
                device.emit(uinput.ABS_X, left_x, syn=False)
                device.syn()
            elif key == 'KEY_D':          # right
                left_x = 255 if pressed else 128
                device.emit(uinput.ABS_X, left_x, syn=False)
                device.syn()

# Mouse input thread with smoothing
class MovingAverage:
    def __init__(self, size=3):
        self.size = size
        self.queue_x = []
        self.queue_y = []

    def add(self, x, y):
        self.queue_x.append(x)
        self.queue_y.append(y)
        if len(self.queue_x) > self.size:
            self.queue_x.pop(0)
            self.queue_y.pop(0)

    def average(self):
        return int(sum(self.queue_x) / len(self.queue_x)) if self.queue_x else 0, \
               int(sum(self.queue_y) / len(self.queue_y)) if self.queue_y else 0

def mouse_thread():
    global right_x, right_y, left_trigger, right_trigger
    sensitivity = 4
    smooth = MovingAverage(5)

    for event in mouse.read_loop():
        if event.type == evdev.ecodes.EV_REL:
            if event.code == evdev.ecodes.REL_X:
                smooth.add(event.value * sensitivity, 0)
            elif event.code == evdev.ecodes.REL_Y:
                smooth.add(0, event.value * sensitivity)

            avg_x, avg_y = smooth.average()
            right_x = clamp(right_x + avg_x)
            right_y = clamp(right_y + avg_y)
            device.emit(uinput.ABS_RX, right_x, syn=False)
            device.emit(uinput.ABS_RY, right_y, syn=False)
            device.syn()

            # Clear buffer after applying movement
            smooth.queue_x.clear()
            smooth.queue_y.clear()

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

# Run threads
threading.Thread(target=keyboard_thread, daemon=True).start()
threading.Thread(target=mouse_thread, daemon=True).start()

print("Virtual Xbox controller running - mouse controls right stick and triggers, keyboard maps buttons.")
print("Press Ctrl+C to exit.")

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Exiting.")
