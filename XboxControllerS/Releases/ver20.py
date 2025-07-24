import uinput
import evdev
import threading
import time
from collections import deque
from Xlib import display, X
import sys

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

device_events = (
    uinput.BTN_A, uinput.BTN_B, uinput.BTN_X, uinput.BTN_Y,
    uinput.BTN_TL, uinput.BTN_TR,
    uinput.BTN_TL2,  # Added for digital left trigger
    uinput.BTN_TR2,  # Added for digital right trigger
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
    kb = """
Keybindings:

- Cycle mouse sensitivity: V
- Cursor lock toggle: N
- Cursor centering toggle: Shift + Alt + P
- EMERGENCY switch (quit script): Shift + X + Q + S
- Toggle mouse smoothing: M
- Left stick click: Q
- Right stick click: Z
- Button A: Space
- Button B: B
- Button X: X
- Button Y: Y
- Left trigger: Middle mouse button (analog)
- Right trigger: Left mouse button (analog)
- BTN_MODE (Guide button): F
- Digital Left Trigger (BTN_TL2): 1
- Digital Right Trigger (BTN_TR2): 2
- D-pad: Arrow keys
- Show this help: H
    """
    print(kb)

def is_key_pressed(keyname):
    """Helper: check if a key name (e.g. 'KEY_LEFTSHIFT', 'KEY_LEFTALT') is currently pressed, via held_keys safely."""
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

    # Shift + Alt + P -> cursor centering toggle
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

    # Emergency switch: Shift + X + Q + S
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

    # Toggle mouse smoothing: M key only (no modifier)
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

    # Show keybinds: H key only (no modifier)
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

            # Handle hotkey checks here to avoid glitches
            hotkey_check(key, pressed)

            # Cycle mouse sensitivity moved to 'V' key instead of 'Z'
            if key == 'KEY_V' and pressed:
                with sensitivity_lock:
                    current_sensitivity_index = (current_sensitivity_index + 1) % len(sensitivity_levels)
                    current_sensitivity = sensitivity_levels[current_sensitivity_index]
                print(f"Mouse sensitivity set to: {current_sensitivity}")
                continue

            # Cursor lock toggle on 'N' key (edge)
            if key == 'KEY_N':
                if pressed and not n_was_down:
                    if cursor_locked.is_set():
                        ungrab_cursor()
                    else:
                        grab_cursor()
                n_was_down = pressed

            # Map Virtual Controller buttons to keys
            if key == 'KEY_Q':
                device.emit(uinput.BTN_THUMBL, pressed)
            elif key == 'KEY_Z':
                device.emit(uinput.BTN_THUMBR, pressed)
            elif key == 'KEY_C':
                pass  # no mapping currently
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
            elif key == 'KEY_1':
                device.emit(uinput.BTN_TL2, pressed)  # Digital Left Trigger
            elif key == 'KEY_2':
                device.emit(uinput.BTN_TR2, pressed)  # Digital Right Trigger
            elif key == 'KEY_F':
                device.emit(uinput.BTN_MODE, pressed)  # Guide button
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
            elif key in ['KEY_S', 'KEY_W', 'KEY_A', 'KEY_D']:
                if key == 'KEY_S':
                    left_y = 255 if pressed else 128
                    device.emit(uinput.ABS_Y, left_y, syn=False)
                elif key == 'KEY_W':
                    left_y = 0 if pressed else 128
                    device.emit(uinput.ABS_Y, left_y, syn=False)
                elif key == 'KEY_A':
                    left_x = 0 if pressed else 128
                    device.emit(uinput.ABS_X, left_x, syn=False)
                elif key == 'KEY_D':
                    left_x = 255 if pressed else 128
                    device.emit(uinput.ABS_X, left_x, syn=False)
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
            if event.code == evdev.ecodes.BTN_LEFT:
                right_trigger = 255 if event.value else 0
                device.emit(uinput.ABS_RZ, right_trigger)
            elif event.code == evdev.ecodes.BTN_MIDDLE:
                left_trigger = 255 if event.value else 0
                device.emit(uinput.ABS_Z, left_trigger)
            elif event.code == evdev.ecodes.BTN_RIGHT:
                # Right mouse button no longer mapped to BTN_MODE
                pass

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
print("Left mouse button mapped to Right Trigger.")
print("Middle mouse button mapped to Left Trigger.")
print("Press F for BTN_MODE (Guide button).")
print("Press 1 for digital Left Trigger (BTN_TL2).")
print("Press 2 for digital Right Trigger (BTN_TR2).")
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
