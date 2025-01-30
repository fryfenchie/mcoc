from mechanism_module import *
from screen_state_module import *
import threading
import signal
import sys
import pynput.mouse

# Create a global event to signal termination
stop_event = threading.Event()

# Configuration - VERIFY THESE VALUES
PID = 41559                    # Update with actual process ID
TARGET_COLOR = (159, 188, 159)  # Updated to match first detected color
RELATIVE_COORD = (341, 17)   # Keep this unless position changed

# Variables to keep track of scroll button clicks
scroll_click_count = 0
scroll_click_threshold = 1

# Define a handler for the stop signal
def signal_handler(sig, frame):
    print("Termination signal received. Shutting down...")
    stop_event.set()
    sys.exit(0)


# Function to check the scroll button clicks
def on_click(x, y, button, pressed):
    global scroll_click_count
    if button == pynput.mouse.Button.middle:
        if pressed:
            scroll_click_count += 1
            print(f"Scroll button clicked {scroll_click_count} times.")
            if scroll_click_count >= scroll_click_threshold:
                print("Scroll button clicked 3 times. Stopping the script...")
                stop_event.set()
                sys.exit(0)
        else:
            print("Scroll button released.")
            # Reset the count if the button is released
            scroll_click_count = 0

def listen_for_scroll_button():
    with pynput.mouse.Listener(on_click=on_click) as listener:
        listener.join()

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    scroll_listener_thread = threading.Thread(target=listen_for_scroll_button)
    scroll_listener_thread.daemon = True
    scroll_listener_thread.start()

    try:
        main_loop(PID, TARGET_COLOR, RELATIVE_COORD, stop_event)
    except Exception as e:
        print(f"Critical error: {e}")
        stop_event.set()
        sys.exit(1)
