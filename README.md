# Whisk-Keyboard-To-Xbox-Controller-Linux
Keyboard keypresses translated into Xbox Controller movements. Useful when coupled with Xbox emulators, especially if you don't have a controller.

# Stable versions
<br>ver18.py
<br>**Versions not included here are either unstable or lacking in features**

# Keyboard Key -> Xbox Controller Button / Axis
<br>**Space**	-> **Button A** (uinput.BTN_A)
<br>**B**	-> **Button B** (uinput.BTN_B)
<br>**X**	-> **Button X** (uinput.BTN_X)
<br>**Y**	-> **Button Y** (uinput.BTN_Y)
<br>**Q**	-> **Left Stick Click** (uinput.BTN_THUMBL)
<br>**Z**	-> **Right Stick Click** (uinput.BTN_THUMBR)
<br>**E**	-> **Left Bumper** (uinput.BTN_TL)
<br>**R**	-> **Right Bumper** (uinput.BTN_TR)
<br>**Enter**	-> **Start Button** (uinput.BTN_START)
<br>**Backspace**	-> **Select Button** (uinput.BTN_SELECT)
<br>**Arrow Up** -> **D-Pad Up** (uinput.BTN_DPAD_UP)
<br>**Arrow Down** -> **D-Pad Down** (uinput.BTN_DPAD_DOWN)
<br>**Arrow Left**	-> **D-Pad Left** (uinput.BTN_DPAD_LEFT)
<br>**Arrow Right**	-> **D-Pad Right** (uinput.BTN_DPAD_RIGHT)
<br>**Left Mouse Button**	-> **Right Trigger** (uinput.ABS_RZ)
<br>**Middle Mouse Button**	-> **Left Trigger** (uinput.ABS_Z)
<br>**Right Mouse Button** -> **BTN_MODE** (Special button) (uinput.BTN_MODE)
<br>**W/S/A/D**	-> **Left Stick X and Y axes** (uinput.ABS_X, uinput.ABS_Y) with:                        
<br>                        - **W = Y** = 0 (up)
<br>                        - **S = Y** = 255 (down)
<br>                        - **A = X** = 0 (left)
<br>                        - **D = X** = 255 (right)
<br>                        When key released, axis returns to neutral 128

# Build
<br>Requirements:
<br>**Python** (tested on 3.13)
<br>Instructions:
1. Make your venv:
<br>**python3 -m venv yourvenv**
2. Activate the venv:
<br>**source yourvenv/bin/activate**
3. Make sure you have *requirements.txt* in an accessible directory - you can get it <a href="https://github.com/C0m3b4ck/Whisk-Keyboard-To-Xbox-Controller-Linux/blob/main/Build/requirements.txt"> here! </a> Then run:
<br>**pip install -r requirements.txt**
4. Keep the venv as long as you want to use my script. To activate it another time, run:
<br>**source yourvenv/bin/activate**

*For more, check out* <a href="https://github.com/C0m3b4ck/Whisk-Keyboard-To-Xbox-Controller-Linux/blob/main/Build/"> Build folder </a>


# Notes
Made this intended for playing Halo: Combat Evolved on Xemu, that is why the buttons are currently tailored to that game.

# Roadmap
* Add key customization from config file
* Add more keys (will happen as I progress in the game and need them)

