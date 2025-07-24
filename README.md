# Whisk-Keyboard-To-Xbox-Controller-Linux
Keyboard keypresses translated into Xbox Controller movements. Useful when coupled with Xbox emulators, especially if you don't have a controller. Intended for Linux, currently emulates Xbox Controller S.
<br>***Currently supporting:***
<br>Xbox S Controller

# Stable versions
<br>ver18.py - lacks a few keys, rest is hard-coded
<br>ver21.py - allows for loading custom keymap from whisk_keymap.conf, if not found - loads the hard-coded keys
<br>**Versions not included here are either unstable or lacking in features**

# Default Keyboard/Mouse Input	Virtual Xbox Controller Button / Axis	Notes
<br>**Default Key Mappings: Keyboard / Mouse → Virtual Xbox Controller**
<br>
<br>**Space**	-> **Button A** (uinput.BTN_A)	
<br>**B**	-> **Button B** (uinput.BTN_B)	
<br>**X**	-> **Button X** (uinput.BTN_X)	
<br>**Y** -> **Button Y** (uinput.BTN_Y)	
<br>**Q** -> **Left Stick Click** (uinput.BTN_THUMBL)	
<br>**Z**	-> **Right Stick Click** (uinput.BTN_THUMBR)	
<br>**E**	-> **Left Bumper** (uinput.BTN_TL)	
<br>**R**	-> **Right Bumper** (uinput.BTN_TR)	
<br>**Enter**	-> **Start Button** (uinput.BTN_START)	
<br>**Backspace**	-> **Select Button** (uinput.BTN_SELECT)	
<br>**Arrow Up**	-> **D-Pad Up** (uinput.BTN_DPAD_UP)	
<br>**Arrow Down**	-> **D-Pad Down** (uinput.BTN_DPAD_DOWN)	
<br>**Arrow Left**	-> **D-Pad Left** (uinput.BTN_DPAD_LEFT)	
<br>**Arrow Right**	-> **D-Pad Right** (uinput.BTN_DPAD_RIGHT)	
<br>**Left Mouse Button**	-> **Right Trigger** (uinput.ABS_RZ)	Analog trigger (0-255)
<br>**Middle Mouse Button**	-> **Left Trigger** (uinput.ABS_Z)	Analog trigger (0-255)
<br>**F**	-> **Guide Button** (uinput.BTN_MODE)	(Formerly mapped to Right Mouse Button)
<br>**1**	-> **Digital Left Trigger** (uinput.BTN_TL2)	May vary by system/uinput support
<br>**2** -> **Digital Right Trigger** (uinput.BTN_TR2)	May vary by system/uinput support
<br>**W/S/A/D** -> 	**Left Stick X and Y axes**. Uses uinput.ABS_X and uinput.ABS_Y.
<br>	- W = Y-axis: 0 (up)	
<br>	- S = Y-axis: 255 (down)	
<br>	- A = X-axis: 0 (left)	
<br>	- D = X-axis: 255 (right)	
<br>	When key released, axis returns to neutral 128	
<br>**Mouse Movement** (REL_X/REL_Y) -> **Right Stick X and Y axes**. Uses uinput.ABS_RX and uinput.ABS_RY. Sensitivity and smoothing are applied.

# Script Hotkeys and Special Script Functions
<br>**These key combinations control the behavior of the script itself, rather than directly mapping to controller buttons**
<br>
<br>**V**	-> **Cycle mouse sensitivity**
<br>**N**	-> **Toggle cursor lock (grab/ungrab X11 pointer)**
<br>**Shift + Alt + P**	-> **Toggle cursor centering**
<br>**Shift + X + Q + S**	-> **EMERGENCY SWITCH-OFF (quits script cleanly)**
<br>**M**	-> **Toggle mouse smoothing**
<br>**H**	-> **Show keybinding help**
<br>**Ctrl + C** -> **Exit script (standard terminal interrupt)**

# Build
<br>Requirements:
<br>**Python** (tested on 3.13)
<br>Instructions:
1. Make your venv:
<br>**python3 -m venv yourvenv**
2. Activate the venv:
<br>**source yourvenv/bin/activate**
3. Make sure you have *requirements.txt* in an accessible directory - you can get it in a Build folder (like XboxControllerS/Build). <br>Then run:
<br>**pip install -r requirements.txt**
4. Keep the venv as long as you want to use my script. To activate it another time, run:
<br>**source yourvenv/bin/activate**

*For more, check out* **instructions.txt** in any Build folder </a>


# Notes
<br>Made and tested on latest Ubuntu version at the time of coding in Python venv. Used with Xemu, with success!
<br>This was intended for playing Halo: Combat Evolved on Xemu, that is why the default buttons are currently tailored to that game. I couldn't find anything like this on Github, so here it is.

# Roadmap
* Add other Xbox controllers
***Done from roadmap***
* Added key customization from config file
* Added more keys (Xbox Controller S)
