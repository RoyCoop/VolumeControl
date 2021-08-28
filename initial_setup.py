import subprocess
import sys


def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])


lib_list = ['numpy', 'soundcard', 'pynput']

for lib in lib_list:
    install(lib)
