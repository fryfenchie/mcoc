import time
import psutil
import pyautogui
import subprocess
import threading
from AppKit import NSWorkspace
import Quartz
import Vision
from PIL import ImageGrab

from mechanism_module import (
    get_window_info, bring_app_to_front_via_applescript, get_content_area,
    capture_content_area, perform_ocr_in_window, click_in_window,
    get_color_at, color_within_tolerance, check_color_thread,
    color_event, is_color_matched
)

# Global variable to keep track of the current state
current_state = None


def determine_screen_state(text_positions):
    for text, x, y in text_positions:
        if text == "NEXT SERIES" and (x, y) == (477, 280):
            return "Next Series"
        elif text == "CONTINUE" and (x, y) == (582, 279):
            return "Select Opponent"
        elif text == "ACCEPT" and (x, y) == (572, 279):
            return "Set Line Up"
        elif text == "NEXT FIGHT!" and (x, y) == (318, 178):
            return "Next Fight - Click Continue"
        elif text == "FINAL FIGHT!" and (x, y) == (317, 218):
            return "Final Fight - Click Continue"
        elif text == "NEXT FIGHT!":
            return "Next Fight - Click Next Fight"
        elif text == "FINAL FIGHT!":
            return "Final Fight - Click Final Fight"
        elif text == "FIGHT!" and (x, y) == (238, 55):
            return "Home"
        elif text == "FIGHT!" and (x, y) == (326, 37):
            return "Inside Fight - Swipe to Multiverse"
        elif text == "MULTIVERSE ARENA":
            return "Click Multiverse"
        elif text == "QUICK FILL":
            return "Quick Fill"
        elif text == "FIND MATCH":
            return "Find Match"
        elif text == "COMPLETED ARENAS" and (x, y) == (357, 40):
            return "Arena Menu"
        elif text == "NEXT SERIES":
            return "Next Series"
        elif text == "TAP ANYWHERE TO CONTINUE":
            return "Tap Anywhere"

    return "Unknown"

def perform_task_based_on_state(state, text_positions, pid):
    global current_state
    if state != current_state:
        print(f"State changed from {current_state} to {state}")
        current_state = state

    if state == "Home":
        print("Detected Home screen. Looking for the FIGHT! button...")
        for text, x, y in text_positions:
            if text == "FIGHT!" and (x, y) == (238, 55):
                click_in_window(pid, x, y)
                return
        print("FIGHT! button not found on Home screen.")
    elif state == "Next Fight - Click Continue":
        print("Detected Next Fight screen at specified location. Clicking CONTINUE button...")
        for text, x, y in text_positions:
            if text == "CONTINUE":
                click_in_window(pid, x, y)
                return
        print("CONTINUE button not found on Next Fight screen.")
    elif state == "Final Fight - Click Continue":
        print("Detected Final Fight screen at specified location. Clicking CONTINUE button...")
        for text, x, y in text_positions:
            if text == "CONTINUE":
                click_in_window(pid, x, y)
                return
        print("CONTINUE button not found on Final Fight screen.")
    elif state == "Next Fight - Click Next Fight":
        print("Detected Next Fight screen at any location. Clicking NEXT FIGHT! button...")
        for text, x, y in text_positions:
            if text == "NEXT FIGHT!":
                click_in_window(pid, x, y)
                return
        print("NEXT FIGHT! button not found on Next Fight screen.")
    elif state == "Final Fight - Click Final Fight":
        print("Detected Final Fight screen at any location. Clicking FINAL FIGHT! button...")
        for text, x, y in text_positions:
            if text == "FINAL FIGHT!":
                click_in_window(pid, x, y)
                return
        print("FINAL FIGHT! button not found on Final Fight screen.")
    elif state == "Select Opponent":
        print("Detected Select Opponent screen. Clicking CONTINUE button...")
        for text, x, y in text_positions:
            if text == "CONTINUE" and (x, y) == (582, 279):
                click_in_window(pid, x, y)
                return
        print("CONTINUE button not found on Select Opponent screen.")
    elif state == "Set Line Up":
        print("Detected Set Line Up screen. Clicking ACCEPT button...")
        for text, x, y in text_positions:
            if text == "ACCEPT" and (x, y) == (572, 279):
                click_in_window(pid, x, y)
                return
        print("ACCEPT button not found on Set Line Up screen.")
    elif state == "Inside Fight - Swipe to Multiverse":
        print("Detected Inside Fight screen. Ignoring any CONTINUE buttons, performing swipe action to find MULTIVERSE...")

        found_multiverse = False
        while not found_multiverse:
            # Get the content area to adjust swipe coordinates
            content_area = get_content_area(pid)
            if content_area:
                a, b, content_width, content_height = content_area

                # Adjust the swipe coordinates to be within bounds
                swipe_start_x = a + min(487, content_width - 1)
                swipe_start_y = b + min(180, content_height - 1)
                swipe_end_x = a + max(83, 0)
                swipe_end_y = b + max(181, 0)
                pyautogui.moveTo(swipe_start_x, swipe_start_y)
                pyautogui.dragTo(swipe_end_x, swipe_end_y, duration=0.25, button='left')
                time.sleep(1)
                print(f"Swiped from ({swipe_start_x}, {swipe_start_y}) to ({swipe_end_x}, {swipe_end_y}).")

                # Re-perform OCR to detect new text positions
                text_positions = perform_ocr_in_window(pid)
                for text, x, y in text_positions:
                    if text == "MULTIVERSE ARENA":
                        click_in_window(pid, x, y)
                        found_multiverse = True
                        print("MULTIVERSE button found and clicked.")
                        break
            else:
                print("Failed to get content area for swiping.")
                break
        if not found_multiverse:
            print("MULTIVERSE button not found after swipe action.")

    elif state == "Click Multiverse":
        print("Detected MULTIVERSE button. Clicking MULTIVERSE...")
        for text, x, y in text_positions:
            if text == "MULTIVERSE":
                click_in_window(pid, x, y)
                return
        print("MULTIVERSE button not found.")

    elif state == "Quick Fill":
        print("Detected QUICK FILL button. Clicking QUICK FILL...")
        for text, x, y in text_positions:
            if text == "QUICK FILL":
                click_in_window(pid, x, y)
                return
        print("QUICK FILL button not found.")

    elif state == "Find Match":
        print("Detected FIND MATCH button. Clicking FIND MATCH...")
        for text, x, y in text_positions:
            if text == "FIND MATCH":
                click_in_window(pid, x, y)
                return
        print("FIND MATCH button not found.")

    elif state == "Arena Menu":
        print("Detected Arena Menu screen. Clicking the first CONTINUE or ENTER button...")
        for text, x, y in sorted(text_positions, key=lambda pos: pos[1]):  # Sort by x-coordinate
            if text in ["CONTINUE", "ENTER"]:
                click_in_window(pid, x, y)
                return
        print("No CONTINUE or ENTER button found on Arena Menu screen.")

    elif state == "Next Series":
        print("Detected NEXT SERIES button. Clicking NEXT SERIES...")
        for text, x, y in text_positions:
            if text == "NEXT SERIES":
                click_in_window(pid, x, y)
                return
        print("NEXT SERIES button not found.")

    elif state == "Tap Anywhere":
        print("Detected TAP ANYWHERE ON THE SCREEN. Clicking anywhere...")
        for text, x, y in text_positions:
            if text == "TAP ANYWHERE TO CONTINUE":
                click_in_window(pid, x, y)
                return
        print("TAP ANYWHERE ON THE SCREEN not found.")

    elif state == "Unknown":
        print("Unknown screen state. No tasks performed.")


        
def click_in_window(pid, rel_x, rel_y):
    content_area = get_content_area(pid)

    if content_area:
        a, b, content_width, content_height = content_area

        app_name = None
        for proc in psutil.process_iter(['pid', 'name']):
            if proc.info['pid'] == pid:
                app_name = proc.info['name']
                break

        if app_name:
            bring_app_to_front_via_applescript(app_name)

            # Check if the application is in the foreground
            if not is_app_foreground(app_name):
                print(f"Application {app_name} is not in the foreground. Stopping the script...")
                stop_event.set()
                sys.exit(0)

            if 0 <= rel_x < content_width and 0 <= rel_y < content_height:
                global_x = a + rel_x
                global_y = b + rel_y

                print(f"Moving mouse to ({global_x}, {global_y}) and clicking...")

                pyautogui.moveTo(global_x, global_y)
                pyautogui.click()

                time.sleep(1)

                print(f"Clicked at global coordinates ({global_x}, {global_y}) inside content area starting at ({a}, {b}).")
            else:
                print(f"Relative coordinates ({rel_x}, {rel_y}) are outside the content area bounds.")
        else:
            print(f"Could not find app name for PID {pid}.")
    else:
        print("Failed to get content area.")

def is_app_foreground(app_name):
    # Implement a function to check if the app is in the foreground
    # This example is for macOS, using AppleScript to get the frontmost application name
    import subprocess
    script = 'tell application "System Events" to get the name of the first process whose frontmost is true'
    result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
    return result.stdout.strip() == app_name

# Main loop to perform tasks based on screen state
# ... (previous imports and functions remain the same)

def main_loop(pid, target_color, relative_coordinate, stop_event):
    color_thread = threading.Thread(target=check_color_thread, args=(pid, target_color, relative_coordinate))
    color_thread.daemon = True
    color_thread.start()

    while not stop_event.is_set():
        if color_event.is_set():
            print("[Status] Combat active - skipping OCR checks")
            time.sleep(2)
            continue

        text_positions = perform_ocr_in_window(pid)
        if text_positions:
            screen_state = determine_screen_state(text_positions)
            print(f"[State Update] Current screen: {screen_state}")
            perform_task_based_on_state(screen_state, text_positions, pid)
        else:
            print("[Warning] No text positions found via OCR")
        
        time.sleep(2)

    print("Main loop stopped.")

