from subprocess import call
import numpy as np
import soundcard as sc
from pynput import mouse
import time
import datetime
import webbrowser


def startup():
    """
    Used for setting up mic, volume controller, and is starting point for calibration() test.
    :return: NONE
    """
    global default_mic, listener, avg_vol, idle_vol, op, notif, avg_vol_limit  # global parameters used by multiple functions
    default_mic = sc.default_microphone()  # stating default mic for recording
    listener = mouse.Listener(on_click=on_click, on_scroll=on_scroll)  # stating mouse input listener
    avg_vol, idle_vol = vol_setup()  # setting up volume to "converge" to, outputs (avg,idle)
    op = {'+': lambda x, y: x + y,
          '-': lambda x, y: x - y}  # for volume control through scroll
    notif = {(1, 1): 'AutoVol ON ; ScrollVOl ON',
             (1, 0): 'AutoVol ON ; ScrollVOl OFF',
             (0, 1): 'AutoVol OFF ; ScrollVOl ON',
             (0, 0): 'AutoVol OFF ; ScrollVOl OFF'}  # for notifications, auto is left side, scroll is right side
    if str(input('Calibrate? [y/n]: ')).lower() == 'y':  # ask for calibration
        calibration()
    else:
        print('Calibration skipped')
    avg_vol_limit = avg_vol * 2
    print(avg_vol, idle_vol)
    listener.start()  # start listening to mouse inputs


def vol_setup():
    """
    Using a log.txt file to get history of  calibrations
    Goal: after a few calibrations, get the ability so skip calibration for same environments
    return: average volume of all history of avg_vol gotten from calibration results before this use.
    """
    with open("vol.txt", 'r') as vol_file:
        vol_list = [eval(vol.split(' ')[0]) for vol in vol_file]  # Iterates history of calibration results
    return np.array([sum(vol) for vol in zip(*vol_list)], dtype=float) / len(vol_list)


def calibration():
    """
    calibrate using a pre-chosen link of 432Hz pure tone to get an avg_vol with the expected sound.
    User should calibrate volume manually until desired volume level.
    :return: NONE
    """
    global avg_vol, idle_vol
    try:  # If link still works, begin calibrating
        webbrowser.open("https://www.youtube.com/watch?v=TxHctJZflh8&t=172s",new=1)
    except:  # link stopped working
        print('test unavailable, youtube link stopped working')
        return  # end without calibration
    time.sleep(2)  # seconds, wait for link to open
    print('Starting calibration, choose volume level')
    total = 0
    with default_mic.recorder(samplerate=48000) as mic:
        start = time.time()
        stop = start
        while stop - start < 30:  # 30 seconds
            total += np.linalg.norm(mic.record(12000))  # accumulate size of mic capture
            stop = time.time()
        call(['pkill', 'vivaldi'])
        call(['pkill', 'chrome'])
        print('finished avg calibration')
        time.sleep(1)   # seconds, wait for link to close
        print('Starting idle calibration')
        start = time.time()
        stop = start
        total_idle = 0
        while stop-start < 10:
            total_idle += np.linalg.norm(mic.record(12000))
            stop = time.time()
    avg_vol = total / (30 * 5)  # 4 samples a second + 1 because its constant so higher than usual
    idle_vol = total_idle / (10 * 4)    # Same reason as above
    with open("vol.txt", 'a') as vol_file:
        vol_file.write('\n ({0},{1}) Date: {2}'.format(
            str(avg_vol), str(idle_vol), str(datetime.date.today())))  # write new calibration result in log.txt history
    print('Calibration successful')


def on_click(x, y, button, pressed):
    """
    Works when listener catches any mouse button clicked
    parameters x,y are not used but are required by library pynnput
    Idea is to test when the middle button is clicked and when its released, thus giving
    the function the ability to test how much time button was held for additional functionality
    :param button: Indicates  which button is clicked
    :param pressed: Indicates hold/release status of button
    :return: NONE
    """
    global auto_flag, notif, scroll_flag, start, stop
    if button == mouse.Button.middle:
        if pressed:  # hold
            start = time.time()
        else:  # release
            stop = time.time()
            if stop - start > 2:  # seconds
                auto_flag = int(not auto_flag)  # NOT gate
            else:
                scroll_flag = int(not scroll_flag)  # NOT gate
            call(['notify-send', '-t', '10', 'Volume Change',
                  notif[(auto_flag, scroll_flag)]])  # linux system notification


def on_scroll(x, y, dx, dy):
    """
    Using scroll_flag as a global flag for availability of function, if on, then mouse wheel
    can be used to control sound.
    :param x, y, dx: Not used but mandatory for library pynput
    :param dy: checks whether scroll was up or down
    :return: NONE
    """
    global scroll_flag
    if dy < 0 and scroll_flag:
        print('down')
        change_vol('-', 1)
    elif dy > 0 and scroll_flag:
        print('up')
        change_vol('+', 1)


def change_vol(direction, scroll_used_flag: int):
    """
    Used to change volume through linux terminal using subprocess.call command.
    :param direction: Used to determine direction to change volume.
    :param scroll_used_flag: Indicates if mouse wheel was used to activate change_vol func: equals 1/0
    :return: NONE
    """
    global avg_vol, scroll_flag, auto_flag, avg_vol_limit, idle_vol
    call(["amixer", "-D", "pulse", "sset", "Master", str(1 + scroll_used_flag * 4) + '%' + direction])
    if scroll_used_flag and idle_vol < avg_vol < avg_vol_limit:
        avg_vol = avg_vol * int(op[direction](100, 5)) / 100


"""

Begin program

"""


startup()

with default_mic.recorder(samplerate=48000) as mic:
    """
    auto_flag indicates AutoVol: 1 is ON ; 0 is OFF
    scroll_flag indicates ScrollVol: 1 is ON ; 0 is OFF
    Initialize program with both OFF
    """
    auto_flag = 0
    scroll_flag = 0
    while True: # Program runs until KeyboardInterrupt or manual exit
        while auto_flag:  # constant measure of mic volume, converging to avg_vol
            vol_size = np.linalg.norm(mic.record(12000))
            print(vol_size)
            if vol_size < avg_vol and vol_size > idle_vol:
                change_vol('+', 0)
            elif vol_size > avg_vol:
                change_vol('-', 0)