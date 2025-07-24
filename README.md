# Whisk-Keyboard-To-Xbox-Controller-Linux
Keyboard keypresses translated into Xbox Controller movements. Useful when coupled with Xbox emulators, especially if you don't have a controller.

# Stable versions
ver18.py
**Versions not included here are either unstable or lacking in features**

# Keyboard Key -> Xbox Controller Button / Axis
Space	-> Button A (uinput.BTN_A)
B	-> Button B (uinput.BTN_B)
X	-> Button X (uinput.BTN_X)
Y	-> Button Y (uinput.BTN_Y)
Q	-> Left Stick Click (uinput.BTN_THUMBL)
Z	-> Right Stick Click (uinput.BTN_THUMBR)
E	-> Left Bumper (uinput.BTN_TL)
R	-> Right Bumper (uinput.BTN_TR)
Enter	-> Start Button (uinput.BTN_START)
Backspace	-> Select Button (uinput.BTN_SELECT)
Arrow Up -> D-Pad Up (uinput.BTN_DPAD_UP)
Arrow Down	-> D-Pad Down (uinput.BTN_DPAD_DOWN)
Arrow Left	-> D-Pad Left (uinput.BTN_DPAD_LEFT)
Arrow Right	-> D-Pad Right (uinput.BTN_DPAD_RIGHT)
Left Mouse Button	-> Right Trigger (uinput.ABS_RZ)
Middle Mouse Button	-> Left Trigger (uinput.ABS_Z)
Right Mouse Button -> BTN_MODE (Special button) (uinput.BTN_MODE)
W/S/A/D	-> Left Stick X and Y axes (uinput.ABS_X, uinput.ABS_Y) with:
