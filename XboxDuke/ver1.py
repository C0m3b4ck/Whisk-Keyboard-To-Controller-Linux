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

# Default keymap for Original Xbox Duke controller
DEFAULT_KEYMAP = {
    'BTN_A': 'KEY_SPACE',
    'BTN_B': 'KEY_B',
    'BTN_X': 'KEY_X',
    'BTN_Y': 'KEY_Y',
    'BTN_BLACK': 'KEY_1',      # Black button mapped to BTN_TL2 (digital left trigger)
    'BTN_WHITE': 'KEY_2',      # White button mapped to BTN_TR2 (digital right trigger)
    'BTN_START': 'KEY_ENTER',
    'BTN_BACK': 'KEY_BACKSPACE',
    # No Guide button on Duke
    'BTN_DPAD_UP': 'KEY_UP',
    'BTN_DPAD_DOWN': 'KEY_DOWN',
    'BTN_DPAD_LEFT': 'KEY_LEFT',
    'BTN_DPAD_RIGHT': 'KEY_RIGHT',
    'ABS_LEFT_STICK_X_POS': 'KEY_D',
    'ABS_LEFT_STICK_X_NEG': 'KEY_A',
    'ABS_LEFT_STICK_Y_POS': 'KEY_S',
    'ABS_LEFT_STICK_Y_NEG': 'KEY_W',
}

CONFIG_FILENAME = 'whisk_keymap_duke.conf'

def load_keymap_from_file(filepath):
    keymap = {}
    try:
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
    except Exception as e:
        print(f"Error reading keymap config '{filepath}': {e}")
    return keymap

print(f"Looking for config file '{CONFIG_FILENAME}' in current directory: {os.getcwd()}")

loaded_keymap = {}
if os.path.isfile(CONFIG_FILENAME):
    raw_map = load_keymap_from_file(CONFIG_FILENAME)
    def get_key(k, default=None):
        return raw_map.get(k, default)
    # Axis keys parsing if provided as comma separated, fallback to defaults
    xs = get_key('ABS_LEFT_STICK_X', None)
    if xs and ',' in xs:
        pos_key, neg_key = [k.strip() for k in xs.split(',', 1)]
    else:
        pos_key = get_key('ABS_LEFT_STICK_X_POS', DEFAULT_KEYMAP['ABS_LEFT_STICK_X_POS'])
        neg_key = get_key('ABS_LEFT_STICK_X_NEG', DEFAULT_KEYMAP['ABS_LEFT_STICK_X_NEG'])
    ys = get_key('ABS_LEFT_STICK_Y', None)
    if ys and ',' in ys:
        posy_key, negy_key = [k.strip() for k in ys.split(',', 1)]
    else:
        posy_key = get_key('ABS_LEFT_STICK_Y_POS', DEFAULT_KEYMAP['ABS_LEFT_STICK_Y_POS'])
        negy_key = get_key('ABS_LEFT_STICK_Y_NEG', DEFAULT_KEYMAP['ABS_LEFT_STICK_Y_NEG'])

    loaded_keymap = {
        'BTN_A': get_key('BTN_A', DEFAULT_KEYMAP['BTN_A']),
        'BTN_B': get_key('BTN_B', DEFAULT_KEYMAP['BTN_B']),
        'BTN_X': get_key('BTN_X', DEFAULT_KEYMAP['BTN_X']),
        'BTN_Y': get_key('BTN_Y', DEFAULT_KEYMAP['BTN_Y']),
        'BTN_BLACK': get_key('BTN_BLACK', DEFAULT_KEYMAP['BTN_BLACK']),
        'BTN_WHITE': get_key('BTN_WHITE', DEFAULT_KEYMAP['BTN_WHITE']),
        'BTN_START': get_key('BTN_START', DEFAULT_KEYMAP['BTN_START']),
        'BTN_BACK': get_key('BTN_BACK', DEFAULT_KEYMAP['BTN_BACK']),
        'BTN_DPAD_UP': get_key('BTN_DPAD_UP', DEFAULT_KEYMAP['BTN_DPAD_UP']),
        'BTN_DPAD_DOWN': get_key('BTN_DPAD_DOWN', DEFAULT_KEYMAP['BTN_DPAD_DOWN']),
        'BTN_DPAD_LEFT': get_key('BTN_DPAD_LEFT', DEFAULT_KEYMAP['BTN_DPAD_LEFT']),
        'BTN_DPAD_RIGHT': get_key('BTN_DPAD_RIGHT', DEFAULT_KEYMAP['BTN_DPAD_RIGHT']),
        'ABS_LEFT_STICK_X_POS': pos_key,
        'ABS_LEFT_STICK_X_NEG': neg_key,
        'ABS_LEFT_STICK_Y_POS': posy_key,
        'ABS_LEFT_STICK_Y_NEG': negy_key,
    }
    print(f"Loaded keymap from '{CONFIG_FILENAME}': {loaded_keymap}")
else:
    print(f"Config file '{CONFIG_FILENAME}' not found, using default keymap.")
    loaded_keymap = DEFAULT_KEYMAP.copy()

def parse_keycode(keyname):
    # Returns evdev key code integer or string key for matching ev.keycode
    if keyname.startswith('KEY_'):
        return keyname
    try:
        return getattr(evdev.ecodes, keyname)
    except AttributeError:
        return None

# uinput device events for Xbox Duke controller (no analog triggers)
device_events = (
    uinput.BTN_A, uinput.BTN_B, uinput.BTN_X, uinput.BTN_Y,
    uinput.BTN_TL2,  # Black button as digital left trigger
    uinput.BTN_TR2,  # White button as digital right trigger
    uinput.BTN_START, uinput.BTN_SELECT,  # Back mapped to Select
    # No Guide button (BTN_MODE)
    uinput.BTN_DPAD_UP, uinput.BTN_DPAD_DOWN, uinput.BTN_DPAD_LEFT, uinput.BTN_DPAD_RIGHT,
    uinput.ABS_X + (0, 255, 0, 0),
    uinput.ABS_Y + (0, 255, 0, 0),
)

device = uinput.Device(device_events, name="Virtual Xbox Duke Controller")

left_x, left_y = 128, 128
right_x, right_y = 128, 128  # Right stick controlled by mouse, but Duke has no right stick; will emulate anyway
exiting = threading.Event()

held_keys = set()
held_keys_lock = threading.Lock()

sensitivity_levels = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
current_sensitivity_index = sensitivity_levels.index(5) if 5 in sensitivity_levels else 0
current_sensitivity = sensitivity_levels[current_sensitivity_index]
sensitivity_lock = threading.Lock()

class MovingAverage:
    def __init__(self, size=20):  # smooth at 20 samples
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
cursor_centering_enabled.set()  # initially ON

cursor_locked = threading.Event()

mouse_smoothing_enabled = threading.Event()
mouse_smoothing_enabled.set()  # smoothing ON initially

def clamp(v):
    return max(0, min(255, v))

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
Keybindings (loaded from {'whisk_keymap_duke.conf' if os.path.isfile(CONFIG_FILENAME) else 'default hardcoded'}):

- Cycle mouse sensitivity (right stick): V
- Cursor lock toggle: N
- Cursor centering toggle: Shift + Alt + P
- Emergency quit: Shift + X + Q + S
- Toggle mouse smoothing: M

Buttons mapped:
- Button A: {loaded_keymap['BTN_A']}
- Button B: {loaded_keymap['BTN_B']}
- Button X: {loaded_keymap['BTN_X']}
- Button Y: {loaded_keymap['BTN_Y']}
- Black button (digital left trigger): {loaded_keymap['BTN_BLACK']}
- White button (digital right trigger): {loaded_keymap['BTN_WHITE']}
- Start: {loaded_keymap['BTN_START']}
- Back: {loaded_keymap['BTN_BACK']}
- D-pad Up: {loaded_keymap['BTN_DPAD_UP']}
- D-pad Down: {loaded_keymap['BTN_DPAD_DOWN']}
- D-pad Left: {loaded_keymap['BTN_DPAD_LEFT']}
- D-pad Right: {loaded_keymap['BTN_DPAD_RIGHT']}

Left stick axes:
- X positive (right): {loaded_keymap['ABS_LEFT_STICK_X_POS']}
- X negative (left): {loaded_keymap['ABS_LEFT_STICK_X_NEG']}
- Y positive (down): {loaded_keymap['ABS_LEFT_STICK_Y_POS']}
- Y negative (up): {loaded_keymap['ABS_LEFT_STICK_Y_NEG']}

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

    # Toggle cursor centering Shift+Alt+P
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

    # Emergency quit Shift+X+Q+S
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

    # Toggle mouse smoothing M
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

    # Show help H
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
                    if key not in held_keys:
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

            # Map button presses/releases to virtual device
            if key == loaded_keymap['BTN_A']:
                device.emit(uinput.BTN_A, pressed)
            elif key == loaded_keymap['BTN_B']:
                device.emit(uinput.BTN_B, pressed)
            elif key == loaded_keymap['BTN_X']:
                device.emit(uinput.BTN_X, pressed)
            elif key == loaded_keymap['BTN_Y']:
                device.emit(uinput.BTN_Y, pressed)
            elif key == loaded_keymap['BTN_BLACK']:
                device.emit(uinput.BTN_TL2, pressed)
            elif key == loaded_keymap['BTN_WHITE']:
                device.emit(uinput.BTN_TR2, pressed)
            elif key == loaded_keymap['BTN_START']:
                device.emit(uinput.BTN_START, pressed)
            elif key == loaded_keymap['BTN_BACK']:
                device.emit(uinput.BTN_SELECT, pressed)
            elif key == loaded_keymap['BTN_DPAD_UP']:
                device.emit(uinput.BTN_DPAD_UP, pressed)
            elif key == loaded_keymap['BTN_DPAD_DOWN']:
                device.emit(uinput.BTN_DPAD_DOWN, pressed)
            elif key == loaded_keymap['BTN_DPAD_LEFT']:
                device.emit(uinput.BTN_DPAD_LEFT, pressed)
            elif key == loaded_keymap['BTN_DPAD_RIGHT']:
                device.emit(uinput.BTN_DPAD_RIGHT, pressed)

            # Left stick axes (two keys per axis)
            if key == loaded_keymap['ABS_LEFT_STICK_X_POS']:
                left_x = 255 if pressed else 128
                device.emit(uinput.ABS_X, left_x, syn=False)
            elif key == loaded_keymap['ABS_LEFT_STICK_X_NEG']:
                left_x = 0 if pressed else 128
                device.emit(uinput.ABS_X, left_x, syn=False)

            if key == loaded_keymap['ABS_LEFT_STICK_Y_POS']:
                left_y = 255 if pressed else 128
                device.emit(uinput.ABS_Y, left_y, syn=False)
            elif key == loaded_keymap['ABS_LEFT_STICK_Y_NEG']:
                left_y = 0 if pressed else 128
                device.emit(uinput.ABS_Y, left_y, syn=False)

            device.syn()

def mouse_thread():
    # Duke had no right stick or analog triggers, but we can emulate right stick via mouse movements
    global right_x, right_y

    for event in mouse.read_loop():
        if exiting.is_set():
            break
        if event.type == evdev.ecodes.EV_REL:
            dx = dy = 0
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
device.syn()

threads = [
    threading.Thread(target=keyboard_thread, daemon=True),
    threading.Thread(target=mouse_thread, daemon=True),
    threading.Thread(target=cursor_centerer_thread, daemon=True)
]

for t in threads:
    t.start()

print("Virtual Xbox Duke controller running.")
print(f"Current right stick mouse sensitivity: {current_sensitivity}. Press V to cycle.")
print("Press N to toggle cursor lock ON/OFF.")
print("Press Shift+Alt+P to toggle cursor centering ON/OFF.")
print("Press Shift+X+Q+S to emergency quit.")
print("Press M to toggle mouse smoothing ON/OFF.")
print(f"Press {loaded_keymap['BTN_BLACK']} for Black button (digital left trigger).")
print(f"Press {loaded_keymap['BTN_WHITE']} for White button (digital right trigger).")
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

