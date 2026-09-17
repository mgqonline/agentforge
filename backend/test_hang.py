import faulthandler
import signal
import sys
faulthandler.enable()
faulthandler.register(signal.SIGALRM, all_threads=True)
signal.alarm(5)
try:
    import main
except Exception as e:
    print(e)
