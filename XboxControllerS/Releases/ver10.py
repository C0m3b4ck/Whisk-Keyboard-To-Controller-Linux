import uinput
import evdev
import threading
import time
from collections import deque
from Xlib import display

# Initialize X11 display for cursor warping
disp = display.Display()
root = disp.screen().root

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
    print("ERROR: Could not find keyboard or mouse input devices")
    exit(1)

print(f"Using keyboard: {keyboard.name} at {keyboard.path}")
print(f"Using mouse: {mouse.name} at {mouse.path}")

device_events = (
    uinput.BTN_A, uinput.BTN_B, uinput.BTN_X, uinput.BTN_Y,
    uinput.BTN_TL, uinput.BTN_TR,
    uinput.BTN_START, uinput.BTN_SELECT,
    uinput.BTN_THUMBL,      # Left stick click (L3)
    uinput.BTN_THUMBR,      # Right stick click (R3)
    uinput.BTN_MODE,        # For Halo CE aim (mapped from right mouse button)
    uinput.ABS_X + (0, 255, 0, 0),  # Left stick X
    uinput.ABS_Y + (0, 255, 0, 0),  # Left stick Y
    uinput.ABS_RX + (0, 255, 0, 0), # Right stick X (mouse)
    uinput.ABS_RY + (0, 255, 0, 0), # Right stick Y (mouse)
    uinput.ABS_Z + (0, 255, 0, 0),  # Left trigger (mapped from middle mouse button)
    uinput.ABS_RZ + (0, 255, 0, 0), # Right trigger (mapped from left mouse button)
    uinput.BTN_DPAD_UP, uinput.BTN_DPAD_DOWN,
    uinput.BTN_DPAD_LEFT, uinput.BTN_DPAD_RIGHT,
)

device = uinput.Device(device_events, name="Virtual Xbox Controller")

left_x, left_y = 128, 128
right_x, right_y = 128, 128
left_trigger = 0
right_trigger = 0

def clamp(v):
    return max(0, min(255, v))

held_keys = set()

sensitivity_levels = [1,2,3,4,5,6,7,8,9,10]
current_sensitivity_index = sensitivity_levels.index(5) if 5 in sensitivity_levels else 0
current_sensitivity = sensitivity_levels[current_sensitivity_index]

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
        return sum(self.xs)/len(self.xs), sum(self.ys)/len(self.ys)

smoother = MovingAverage()

def check_hotkey_state():
    """Check if Shift+Alt+Pause are pressed. Returns True or False."""
    data = disp.query_keymap()

    keysyms = {
        "Shift_L": 0xffe1,
        "Alt_L": 0xffe9,
        "Pause": 0xff13,
    }
    keycodes = [disp.keysym_to_keycode(ks) for ks in keysyms.values()]

    def is_key_down(kc):
        byte_group = kc // 8
        bit = kc % 8
        return (data[byte_group] & (1 << bit)) != 0

    try:
        shift_down = is_key_down(keycodes[0])
        alt_down = is_key_down(keycodes[1])
        pause_down = is_key_down(keycodes[2])
        return shift_down and alt_down and pause_down
    except Exception:
        return False

def keyboard_thread():
    global left_x, left_y, current_sensitivity, current_sensitivity_index
    for event in keyboard.read_loop():
        if event.type == evdev.ecodes.EV_KEY:
            ev = evdev.categorize(event)
            key = ev.keycode if isinstance(ev.keycode, str) else ev.keycode
            pressed = ev.keystate in (evdev.KeyEvent.key_down, evdev.KeyEvent.key_hold)

            if pressed:
                if key in held_keys: continue
                held_keys.add(key)
            else:
                if key not in held_keys: continue
                held_keys.remove(key)

            if key == 'KEY_Z' and pressed:
                current_sensitivity_index = (current_sensitivity_index + 1) % len(sensitivity_levels)
                current_sensitivity = sensitivity_levels[current_sensitivity_index]
                print(f"Mouse sensitivity set to: {current_sensitivity}")
                continue

            if key == 'KEY_Q':
                device.emit(uinput.BTN_THUMBL, pressed)
            elif key == 'KEY_C':
                device.emit(uinput.BTN_THUMBR, pressed)
            elif key == 'KEY_SPACE':
                device.emit(uinput.BTN_A, pressed)
            elif key == 'KEY_B':
                device.emit(uinput.BTN_B, pressed)
            elif key == 'KEY_X':
                device.emit(uinput.BTN_X, pressed)
            elif key == 'KEY_Y':
                device.emit(uinput.BTN_Y, pressed)
            elif key == 'KEY_E':
                device.emit(uinput.BTN_TL, pressed)
            elif key == 'KEY_R':
                device.emit(uinput.BTN_TR, pressed)
            elif key == 'KEY_ENTER':
                device.emit(uinput.BTN_START, pressed)
            elif key == 'KEY_BACKSPACE':
                device.emit(uinput.BTN_SELECT, pressed)
            elif key == 'KEY_UP':
                device.emit(uinput.BTN_DPAD_UP, pressed)
            elif key == 'KEY_DOWN':
                device.emit(uinput.BTN_DPAD_DOWN, pressed)
            elif key == 'KEY_LEFT':
                device.emit(uinput.BTN_DPAD_LEFT, pressed)
            elif key == 'KEY_RIGHT':
                device.emit(uinput.BTN_DPAD_RIGHT, pressed)
            elif key == 'KEY_S':
                left_y = 255 if pressed else 128
                device.emit(uinput.ABS_Y, left_y, syn=False)
                device.syn()
            elif key == 'KEY_W':
                left_y = 0 if pressed else 128
                device.emit(uinput.ABS_Y, left_y, syn=False)
                device.syn()
            elif key == 'KEY_A':
                left_x = 0 if pressed else 128
                device.emit(uinput.ABS_X, left_x, syn=False)
                device.syn()
            elif key == 'KEY_D':
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

            smoother.xs.clear()
            smoother.ys.clear()

        elif event.type == evdev.ecodes.EV_KEY:
            if event.code == evdev.ecodes.BTN_LEFT:
                right_trigger = 255 if event.value else 0
                device.emit(uinput.ABS_RZ, right_trigger)
            elif event.code == evdev.ecodes.BTN_MIDDLE:
                left_trigger = 255 if event.value else 0
                device.emit(uinput.ABS_Z, left_trigger)
            elif event.code == evdev.ecodes.BTN_RIGHT:
                device.emit(uinput.BTN_MODE, 255 if event.value else 0)

def cursor_centerer_thread():
    while True:
        if not check_hotkey_state():
            screen = disp.screen()
            center_x = screen.width_in_pixels // 2
            center_y = screen.height_in_pixels // 2
            root.warp_pointer(center_x, center_y)
            disp.sync()
        time.sleep(0.01)

# Initialize sticks/triggers neutral
device.emit(uinput.ABS_X, 128)
device.emit(uinput.ABS_Y, 128)
device.emit(uinput.ABS_RX, 128)
device.emit(uinput.ABS_RY, 128)
device.emit(uinput.ABS_Z, 0)
device.emit(uinput.ABS_RZ, 0)
device.syn()

t1 = threading.Thread(target=keyboard_thread, daemon=True)
t2 = threading.Thread(target=mouse_thread, daemon=True)
t3 = threading.Thread(target=cursor_centerer_thread, daemon=True)

t1.start()
t2.start()
t3.start()

print("Virtual Xbox controller running.")
print(f"Current mouse sensitivity: {current_sensitivity}. Press Z to cycle.")
print("Press Q/C for left/right stick click.")
print("Left mouse button mapped to Right Trigger.")
print("Middle mouse button mapped to Left Trigger.")
print("Right mouse button mapped to BTN_MODE (Halo CE aim workaround).")
print("Holding Shift+Alt+Pause disables mouse cursor center warp.")
print("Ctrl+C to exit.")

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Exiting.")
