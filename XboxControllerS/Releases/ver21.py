import uinput
import evdev
import threading
import time
from collections import deque
from Xlib import display, X
import sys
import os

# Initialize X11 display for cursor warping and grabbing
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
    sys.exit(1)

print(f"Using keyboard: {keyboard.name} at {keyboard.path}")
print(f"Using mouse: {mouse.name} at {mouse.path}")

# Default mappings (hardcoded). Will be overridden if config file loaded.

DEFAULT_KEYMAP = {
    'BTN_A': 'KEY_SPACE',
    'BTN_B': 'KEY_B',
    'BTN_X': 'KEY_X',
    'BTN_Y': 'KEY_Y',
    'BTN_THUMBL': 'KEY_Q',
    'BTN_THUMBR': 'KEY_Z',
    'BTN_TL': 'KEY_E',
    'BTN_TR': 'KEY_R',
    'BTN_TL2': 'KEY_1',
    'BTN_TR2': 'KEY_2',
    'BTN_START': 'KEY_ENTER',
    'BTN_SELECT': 'KEY_BACKSPACE',
    'BTN_MODE': 'KEY_F',
    'BTN_DPAD_UP': 'KEY_UP',
    'BTN_DPAD_DOWN': 'KEY_DOWN',
    'BTN_DPAD_LEFT': 'KEY_LEFT',
    'BTN_DPAD_RIGHT': 'KEY_RIGHT',
    'ABS_LEFT_STICK_X_POS': 'KEY_D',
    'ABS_LEFT_STICK_X_NEG': 'KEY_A',
    'ABS_LEFT_STICK_Y_POS': 'KEY_S',
    'ABS_LEFT_STICK_Y_NEG': 'KEY_W',
    # Mouse buttons for triggers (special handling in mouse_thread)
    'RIGHT_TRIGGER_MOUSE': evdev.ecodes.BTN_LEFT,
    'LEFT_TRIGGER_MOUSE': evdev.ecodes.BTN_MIDDLE,
}

CONFIG_FILENAME = 'whisk_keymap.conf'

def load_keymap_from_file(filepath):
    keymap = {}
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' not in line:
                print(f"Skipping invalid line in keymap file: {line}")
                continue
            key, val = line.split('=', 1)
            key = key.strip()
            val = val.strip()
            keymap[key] = val
    return keymap

def parse_evdev_key(keyname):
    """Convert a key string like 'KEY_SPACE' into evdev.ecodes key code."""
    if keyname.startswith('KEY_'):
        return keyname  # Keep as string for matching with evdev events
    # For mouse buttons like BTN_LEFT, we return ecodes integer:
    if keyname.startswith('BTN_'):
        return getattr(evdev.ecodes, keyname, None)
    return None

print(f"Looking for config file '{CONFIG_FILENAME}' in current directory: {os.getcwd()}")
loaded_keymap = {}
if os.path.isfile(CONFIG_FILENAME):
    try:
        raw_map = load_keymap_from_file(CONFIG_FILENAME)
        # Parse and map keys, also handle dual keys for axis if provided
        # Use keys from config or fallback to default
        loaded_keymap = {}

        # First parse normal buttons
        def get_key(k, default=None):
            return raw_map.get(k, default)

        # Map all keys similarly, including axis with dual keys
        # For axis keys, split comma separated keys
        # Left Stick X
        xs = get_key('ABS_LEFT_STICK_X', None)
        if xs and ',' in xs:
            pos_key, neg_key = [k.strip() for k in xs.split(',',1)]
        else:
            pos_key = get_key('ABS_LEFT_STICK_X_POS', DEFAULT_KEYMAP['ABS_LEFT_STICK_X_POS'])
            neg_key = get_key('ABS_LEFT_STICK_X_NEG', DEFAULT_KEYMAP['ABS_LEFT_STICK_X_NEG'])
        # Left Stick Y
        ys = get_key('ABS_LEFT_STICK_Y', None)
        if ys and ',' in ys:
            posy_key, negy_key = [k.strip() for k in ys.split(',',1)]
        else:
            posy_key = get_key('ABS_LEFT_STICK_Y_POS', DEFAULT_KEYMAP['ABS_LEFT_STICK_Y_POS'])
            negy_key = get_key('ABS_LEFT_STICK_Y_NEG', DEFAULT_KEYMAP['ABS_LEFT_STICK_Y_NEG'])

        loaded_keymap = {
            'BTN_A': get_key('BTN_A', DEFAULT_KEYMAP['BTN_A']),
            'BTN_B': get_key('BTN_B', DEFAULT_KEYMAP['BTN_B']),
            'BTN_X': get_key('BTN_X', DEFAULT_KEYMAP['BTN_X']),
            'BTN_Y': get_key('BTN_Y', DEFAULT_KEYMAP['BTN_Y']),
            'BTN_THUMBL': get_key('BTN_THUMBL', DEFAULT_KEYMAP['BTN_THUMBL']),
            'BTN_THUMBR': get_key('BTN_THUMBR', DEFAULT_KEYMAP['BTN_THUMBR']),
            'BTN_TL': get_key('BTN_TL', DEFAULT_KEYMAP['BTN_TL']),
            'BTN_TR': get_key('BTN_TR', DEFAULT_KEYMAP['BTN_TR']),
            'BTN_TL2': get_key('BTN_TL2', DEFAULT_KEYMAP['BTN_TL2']),
            'BTN_TR2': get_key('BTN_TR2', DEFAULT_KEYMAP['BTN_TR2']),
            'BTN_START': get_key('BTN_START', DEFAULT_KEYMAP['BTN_START']),
            'BTN_SELECT': get_key('BTN_SELECT', DEFAULT_KEYMAP['BTN_SELECT']),
            'BTN_MODE': get_key('BTN_MODE', DEFAULT_KEYMAP['BTN_MODE']),
            'BTN_DPAD_UP': get_key('BTN_DPAD_UP', DEFAULT_KEYMAP['BTN_DPAD_UP']),
            'BTN_DPAD_DOWN': get_key('BTN_DPAD_DOWN', DEFAULT_KEYMAP['BTN_DPAD_DOWN']),
            'BTN_DPAD_LEFT': get_key('BTN_DPAD_LEFT', DEFAULT_KEYMAP['BTN_DPAD_LEFT']),
            'BTN_DPAD_RIGHT': get_key('BTN_DPAD_RIGHT', DEFAULT_KEYMAP['BTN_DPAD_RIGHT']),
            'ABS_LEFT_STICK_X_POS': pos_key,
            'ABS_LEFT_STICK_X_NEG': neg_key,
            'ABS_LEFT_STICK_Y_POS': posy_key,
            'ABS_LEFT_STICK_Y_NEG': negy_key,
            'RIGHT_TRIGGER_MOUSE': evdev.ecodes.BTN_LEFT,
            'LEFT_TRIGGER_MOUSE': evdev.ecodes.BTN_MIDDLE,
        }
        print(f"Loaded keymap from '{CONFIG_FILENAME}': {loaded_keymap}")
    except Exception as e:
        print(f"Failed to load keymap config '{CONFIG_FILENAME}', using defaults. Error: {e}")
        loaded_keymap = DEFAULT_KEYMAP.copy()
else:
    print(f"Config file '{CONFIG_FILENAME}' not found, using default keymap.")
    loaded_keymap = DEFAULT_KEYMAP.copy()

# Construct device_events with known uinput codes (same as before):
device_events = (
    uinput.BTN_A, uinput.BTN_B, uinput.BTN_X, uinput.BTN_Y,
    uinput.BTN_TL, uinput.BTN_TR,
    uinput.BTN_TL2,
    uinput.BTN_TR2,
    uinput.BTN_START, uinput.BTN_SELECT,
    uinput.BTN_THUMBL,
    uinput.BTN_THUMBR,
    uinput.BTN_MODE,
    uinput.ABS_X + (0, 255, 0, 0),
    uinput.ABS_Y + (0, 255, 0, 0),
    uinput.ABS_RX + (0, 255, 0, 0),
    uinput.ABS_RY + (0, 255, 0, 0),
    uinput.ABS_Z + (0, 255, 0, 0),
    uinput.ABS_RZ + (0, 255, 0, 0),
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
held_keys_lock = threading.Lock()

sensitivity_levels = [1,2,3,4,5,6,7,8,9,10]
current_sensitivity_index = sensitivity_levels.index(5) if 5 in sensitivity_levels else 0
current_sensitivity = sensitivity_levels[current_sensitivity_index]
sensitivity_lock = threading.Lock()

class MovingAverage:
    def __init__(self, size=20):  # increased size for smoothing
        self.size = size
        self.xs = deque(maxlen=size)
        self.ys = deque(maxlen=size)
    def add(self, dx, dy):
        self.xs.append(dx)
        self.ys.append(dy)
    def average(self):
        if not self.xs or not self.ys:
            return 0, 0
        return sum(self.xs) / len(self.xs), sum(self.ys) / len(self.ys)
    def clear(self):
        self.xs.clear()
        self.ys.clear()

smoother = MovingAverage()

cursor_centering_enabled = threading.Event()
cursor_centering_enabled.set()  # initially on

cursor_locked = threading.Event()  # cursor grab state

mouse_smoothing_enabled = threading.Event()
mouse_smoothing_enabled.set()  # smoothing initially enabled

exiting = threading.Event()

def grab_cursor():
    result = root.grab_pointer(True,
                               X.PointerMotionMask | X.ButtonPressMask | X.ButtonReleaseMask,
                               X.GrabModeAsync, X.GrabModeAsync,
                               X.NONE, X.NONE, X.CurrentTime)
    disp.sync()
    if result == X.GrabSuccess:
        print("Cursor locked (grabbed).")
        cursor_locked.set()
    else:
        print("Failed to grab (lock) cursor.")

def ungrab_cursor():
    disp.ungrab_pointer(X.CurrentTime)
    disp.sync()
    print("Cursor unlocked (ungrabbed).")
    cursor_locked.clear()

def print_keybinds():
    kb = f"""
Keybindings (loaded from {'whisk_keymap.conf' if os.path.isfile(CONFIG_FILENAME) else 'default hardcoded'}):

- Cycle mouse sensitivity: V
- Cursor lock toggle: N
- Cursor centering toggle: Shift + Alt + P
- EMERGENCY switch (quit script): Shift + X + Q + S
- Toggle mouse smoothing: M

- Left stick click: {loaded_keymap['BTN_THUMBL']}
- Right stick click: {loaded_keymap['BTN_THUMBR']}
- Button A: {loaded_keymap['BTN_A']}
- Button B: {loaded_keymap['BTN_B']}
- Button X: {loaded_keymap['BTN_X']}
- Button Y: {loaded_keymap['BTN_Y']}
- Left trigger (analog): Middle mouse button
- Right trigger (analog): Left mouse button
- BTN_MODE (Guide button): {loaded_keymap['BTN_MODE']}
- Digital Left Trigger (BTN_TL2): {loaded_keymap['BTN_TL2']}
- Digital Right Trigger (BTN_TR2): {loaded_keymap['BTN_TR2']}
- D-pad Up: {loaded_keymap['BTN_DPAD_UP']}
- D-pad Down: {loaded_keymap['BTN_DPAD_DOWN']}
- D-pad Left: {loaded_keymap['BTN_DPAD_LEFT']}
- D-pad Right: {loaded_keymap['BTN_DPAD_RIGHT']}

- Left stick X axis positive: {loaded_keymap['ABS_LEFT_STICK_X_POS']} (right)
- Left stick X axis negative: {loaded_keymap['ABS_LEFT_STICK_X_NEG']} (left)
- Left stick Y axis positive: {loaded_keymap['ABS_LEFT_STICK_Y_POS']} (down)
- Left stick Y axis negative: {loaded_keymap['ABS_LEFT_STICK_Y_NEG']} (up)

- Show this help: H
"""
    print(kb)

def is_key_pressed(keyname):
    with held_keys_lock:
        return keyname in held_keys

def hotkey_check(event_key, pressed):
    global current_sensitivity, current_sensitivity_index

    if not hasattr(hotkey_check, "m_down"):
        hotkey_check.m_down = False
    if not hasattr(hotkey_check, "h_down"):
        hotkey_check.h_down = False
    if not hasattr(hotkey_check, "p_down"):
        hotkey_check.p_down = False
    if not hasattr(hotkey_check, "emergency_down"):
        hotkey_check.emergency_down = False

    if event_key == 'KEY_P':
        shift_pressed = is_key_pressed('KEY_LEFTSHIFT') or is_key_pressed('KEY_RIGHTSHIFT')
        alt_pressed = is_key_pressed('KEY_LEFTALT') or is_key_pressed('KEY_RIGHTALT')
        if pressed and shift_pressed and alt_pressed and not hotkey_check.p_down:
            if cursor_centering_enabled.is_set():
                cursor_centering_enabled.clear()
                print("Cursor centering toggled OFF")
            else:
                cursor_centering_enabled.set()
                print("Cursor centering toggled ON")
            hotkey_check.p_down = True
        elif not pressed:
            hotkey_check.p_down = False

    emergency_keys = {'KEY_LEFTSHIFT', 'KEY_RIGHTSHIFT', 'KEY_X', 'KEY_Q', 'KEY_S'}
    if event_key in emergency_keys:
        shift_pressed = is_key_pressed('KEY_LEFTSHIFT') or is_key_pressed('KEY_RIGHTSHIFT')
        all_pressed = (shift_pressed and
                       is_key_pressed('KEY_X') and
                       is_key_pressed('KEY_Q') and
                       is_key_pressed('KEY_S'))
        if pressed and all_pressed and not hotkey_check.emergency_down:
            print("Emergency switch-off activated: exiting script cleanly...")
            try:
                if cursor_locked.is_set():
                    ungrab_cursor()
            except Exception:
                pass
            exiting.set()
            sys.exit(0)
        elif not pressed:
            hotkey_check.emergency_down = False

    if event_key == 'KEY_M':
        if pressed and not hotkey_check.m_down:
            if mouse_smoothing_enabled.is_set():
                mouse_smoothing_enabled.clear()
                smoother.clear()
                print("Mouse smoothing toggled OFF")
            else:
                mouse_smoothing_enabled.set()
                print("Mouse smoothing toggled ON")
            hotkey_check.m_down = True
        elif not pressed:
            hotkey_check.m_down = False

    if event_key == 'KEY_H':
        if pressed and not hotkey_check.h_down:
            print_keybinds()
            hotkey_check.h_down = True
        elif not pressed:
            hotkey_check.h_down = False

def keyboard_thread():
    global left_x, left_y, current_sensitivity_index, current_sensitivity

    n_was_down = False

    for event in keyboard.read_loop():
        if exiting.is_set():
            break
        if event.type == evdev.ecodes.EV_KEY:
            ev = evdev.categorize(event)
            key = ev.keycode if isinstance(ev.keycode, str) else ev.keycode
            pressed = ev.keystate in (evdev.KeyEvent.key_down, evdev.KeyEvent.key_hold)

            with held_keys_lock:
                if pressed:
                    if key in held_keys:
                        pass
                    else:
                        held_keys.add(key)
                else:
                    if key in held_keys:
                        held_keys.remove(key)
                    else:
                        continue

            hotkey_check(key, pressed)

            if key == 'KEY_V' and pressed:
                with sensitivity_lock:
                    current_sensitivity_index = (current_sensitivity_index + 1) % len(sensitivity_levels)
                    current_sensitivity = sensitivity_levels[current_sensitivity_index]
                print(f"Mouse sensitivity set to: {current_sensitivity}")
                continue

            if key == 'KEY_N':
                if pressed and not n_was_down:
                    if cursor_locked.is_set():
                        ungrab_cursor()
                    else:
                        grab_cursor()
                n_was_down = pressed

            # Map buttons from loaded_keymap
            if key == loaded_keymap['BTN_THUMBL']:
                device.emit(uinput.BTN_THUMBL, pressed)
            elif key == loaded_keymap['BTN_THUMBR']:
                device.emit(uinput.BTN_THUMBR, pressed)
            elif key == loaded_keymap['BTN_A']:
                device.emit(uinput.BTN_A, pressed)
            elif key == loaded_keymap['BTN_B']:
                device.emit(uinput.BTN_B, pressed)
            elif key == loaded_keymap['BTN_X']:
                device.emit(uinput.BTN_X, pressed)
            elif key == loaded_keymap['BTN_Y']:
                device.emit(uinput.BTN_Y, pressed)
            elif key == loaded_keymap['BTN_TL']:
                device.emit(uinput.BTN_TL, pressed)
            elif key == loaded_keymap['BTN_TR']:
                device.emit(uinput.BTN_TR, pressed)
            elif key == loaded_keymap['BTN_TL2']:
                device.emit(uinput.BTN_TL2, pressed)
            elif key == loaded_keymap['BTN_TR2']:
                device.emit(uinput.BTN_TR2, pressed)
            elif key == loaded_keymap['BTN_MODE']:
                device.emit(uinput.BTN_MODE, pressed)
            elif key == loaded_keymap['BTN_START']:
                device.emit(uinput.BTN_START, pressed)
            elif key == loaded_keymap['BTN_SELECT']:
                device.emit(uinput.BTN_SELECT, pressed)
            elif key == loaded_keymap['BTN_DPAD_UP']:
                device.emit(uinput.BTN_DPAD_UP, pressed)
            elif key == loaded_keymap['BTN_DPAD_DOWN']:
                device.emit(uinput.BTN_DPAD_DOWN, pressed)
            elif key == loaded_keymap['BTN_DPAD_LEFT']:
                device.emit(uinput.BTN_DPAD_LEFT, pressed)
            elif key == loaded_keymap['BTN_DPAD_RIGHT']:
                device.emit(uinput.BTN_DPAD_RIGHT, pressed)

            # Left stick axes handling (two keys per axis)
            # For X axis
            if key == loaded_keymap['ABS_LEFT_STICK_X_POS']:
                left_x = 255 if pressed else 128
                device.emit(uinput.ABS_X, left_x, syn=False)
            elif key == loaded_keymap['ABS_LEFT_STICK_X_NEG']:
                left_x = 0 if pressed else 128
                device.emit(uinput.ABS_X, left_x, syn=False)

            # For Y axis
            elif key == loaded_keymap['ABS_LEFT_STICK_Y_POS']:
                left_y = 255 if pressed else 128
                device.emit(uinput.ABS_Y, left_y, syn=False)
            elif key == loaded_keymap['ABS_LEFT_STICK_Y_NEG']:
                left_y = 0 if pressed else 128
                device.emit(uinput.ABS_Y, left_y, syn=False)
            device.syn()

def mouse_thread():
    global right_x, right_y, left_trigger, right_trigger

    for event in mouse.read_loop():
        if exiting.is_set():
            break
        if event.type == evdev.ecodes.EV_REL:
            dx, dy = 0, 0
            if event.code == evdev.ecodes.REL_X:
                with sensitivity_lock:
                    dx = event.value * current_sensitivity
            elif event.code == evdev.ecodes.REL_Y:
                with sensitivity_lock:
                    dy = event.value * current_sensitivity

            if mouse_smoothing_enabled.is_set():
                smoother.add(dx, dy)
                avg_dx, avg_dy = smoother.average()
            else:
                avg_dx, avg_dy = dx, dy
                smoother.clear()

            right_x = clamp(right_x + int(avg_dx))
            right_y = clamp(right_y + int(avg_dy))

            device.emit(uinput.ABS_RX, right_x, syn=False)
            device.emit(uinput.ABS_RY, right_y, syn=False)
            device.syn()

        elif event.type == evdev.ecodes.EV_KEY:
            # Map mouse buttons to analog triggers per config
            if event.code == loaded_keymap['RIGHT_TRIGGER_MOUSE']:
                right_trigger = 255 if event.value else 0
                device.emit(uinput.ABS_RZ, right_trigger)
            elif event.code == loaded_keymap['LEFT_TRIGGER_MOUSE']:
                left_trigger = 255 if event.value else 0
                device.emit(uinput.ABS_Z, left_trigger)

def cursor_centerer_thread():
    screen = disp.screen()
    center_x = screen.width_in_pixels // 2
    center_y = screen.height_in_pixels // 2

    while not exiting.is_set():
        if cursor_centering_enabled.is_set():
            data = root.query_pointer()
            cur_x, cur_y = data.root_x, data.root_y
            if abs(cur_x - center_x) > 5 or abs(cur_y - center_y) > 5:
                root.warp_pointer(center_x, center_y)
                disp.sync()
        time.sleep(0.02)  # 50 Hz

# Initialize neutral states
device.emit(uinput.ABS_X, 128)
device.emit(uinput.ABS_Y, 128)
device.emit(uinput.ABS_RX, 128)
device.emit(uinput.ABS_RY, 128)
device.emit(uinput.ABS_Z, 0)
device.emit(uinput.ABS_RZ, 0)
device.syn()

# Start threads
threads = []
threads.append(threading.Thread(target=keyboard_thread, daemon=True))
threads.append(threading.Thread(target=mouse_thread, daemon=True))
threads.append(threading.Thread(target=cursor_centerer_thread, daemon=True))

for t in threads:
    t.start()

print("Virtual Xbox controller running.")
print(f"Current mouse sensitivity: {current_sensitivity}. Press V to cycle.")
print("Press Q/Z for left/right stick click.")
print("Left mouse button mapped to Right Trigger (analog).")
print("Middle mouse button mapped to Left Trigger (analog).")
print(f"Press {loaded_keymap['BTN_MODE']} for BTN_MODE (Guide button).")
print(f"Press {loaded_keymap['BTN_TL2']} for digital Left Trigger (BTN_TL2).")
print(f"Press {loaded_keymap['BTN_TR2']} for digital Right Trigger (BTN_TR2).")
print("Press Shift+Alt+P to toggle cursor centering ON/OFF.")
print("Press N to toggle cursor lock ON/OFF.")
print("Press Shift+X+Q+S for EMERGENCY switch (quit script).")
print("Press M to toggle mouse smoothing ON/OFF.")
print("Press H to show keybindings.")
print("Ctrl+C to exit.")

try:
    while not exiting.is_set():
        time.sleep(1)
except KeyboardInterrupt:
    print("Exiting on Ctrl+C...")
finally:
    if cursor_locked.is_set():
        ungrab_cursor()
    exiting.set()
    time.sleep(0.3)
    print("Exited cleanly.")
