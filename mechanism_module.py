import time
import psutil
import pyautogui
import subprocess
import threading
from AppKit import NSWorkspace
import Quartz
import Vision
from PIL import ImageGrab

# Define all functions here...

def get_window_info(pid):
    try:
        app_name = None
        for proc in psutil.process_iter(['pid', 'name']):
            if proc.info['pid'] == pid:
                app_name = proc.info['name']
                break

        if not app_name:
            return f"No application found with PID {pid}"

        for app in NSWorkspace.sharedWorkspace().runningApplications():
            if app.localizedName() == app_name:
                options = Quartz.kCGWindowListOptionOnScreenOnly
                window_list = Quartz.CGWindowListCopyWindowInfo(options, Quartz.kCGNullWindowID)
                for window in window_list:
                    if window['kCGWindowOwnerPID'] == pid:
                        bounds = window['kCGWindowBounds']
                        window_x = int(bounds['X'])
                        window_y = int(bounds['Y'])
                        width = int(bounds['Width'])
                        height = int(bounds['Height'])
                        return window_x, window_y, width, height
        return f"No window found for application with PID {pid}"
    except Exception as e:
        return str(e)

def bring_app_to_front_via_applescript(app_name):
    try:
        applescript = f'tell application "{app_name}" to activate'
        subprocess.run(['osascript', '-e', applescript])
        print(f"Application '{app_name}' brought to the front.")
    except Exception as e:
        print(f"Error bringing app to front: {str(e)}")

def get_content_area(pid):
    window_info = get_window_info(pid)

    if isinstance(window_info, tuple):
        window_x, window_y, window_width, window_height = window_info

        if window_height > window_width:
            title_bar_height = 38
            border_width = 6
            content_width = 318
            content_height = 689
        else:
            title_bar_height = 38
            border_width = 6
            content_width = 689
            content_height = 318

        a = window_x + border_width
        b = window_y + title_bar_height

        return a, b, content_width, content_height
    else:
        print(window_info)
        return None

def capture_content_area(a, b, content_width, content_height):
    display_id = Quartz.CGMainDisplayID()
    image = Quartz.CGWindowListCreateImage(
        Quartz.CGRectMake(a, b, content_width, content_height),
        Quartz.kCGWindowListOptionOnScreenOnly,
        Quartz.kCGNullWindowID,
        Quartz.kCGWindowImageDefault
    )
    return image

def perform_ocr_in_window(pid):
    content_area = get_content_area(pid)

    if content_area:
        a, b, content_width, content_height = content_area

        image = capture_content_area(a, b, content_width, content_height)

        if image:
            request = Vision.VNRecognizeTextRequest.alloc().init()
            handler = Vision.VNImageRequestHandler.alloc().initWithCGImage_options_(image, None)
            try:
                handler.performRequests_error_([request], None)
                observations = request.results()
                text_positions = []
                for observation in observations:
                    text = observation.topCandidates_(1)[0].string()
                    bounding_box = observation.boundingBox()
                    x = int(bounding_box.origin.x * content_width)
                    y = int((1 - bounding_box.origin.y - bounding_box.size.height) * content_height)
                    text_positions.append((text, x, y))
                    print(f"Detected text: '{text}' at ({x}, {y}) within the content area")
                return text_positions
            except Exception as e:
                print(f"Error performing OCR: {str(e)}")
        else:
            print("Failed to capture content area.")
    return None

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

def get_color_at(x, y):
    # Capture the screen at the specified coordinates using Pillow
    image = ImageGrab.grab(bbox=(x, y, x+1, y+1))
    pixel = image.load()

    # Extract the color values (ignore the alpha channel if present)
    red, green, blue = pixel[0, 0][:3]

    return red, green, blue

def color_within_tolerance(color1, color2, tolerance=35):  # Increased tolerance from 10 to 20
    return all(abs(c1 - c2) <= tolerance for c1, c2 in zip(color1, color2))

def check_color_and_print(global_x, global_y, target_color, pid):
    content_area = get_content_area(pid)
    if content_area:
        a, b, content_width, content_height = content_area
        rel_x, rel_y = global_x, global_y

        # Ensure the relative coordinates are within the window bounds
        if 0 <= rel_x < content_width and 0 <= rel_y < content_height:
            # Convert relative coordinates to global coordinates
            global_x = a + rel_x
            global_y = b + rel_y

            color = get_color_at(global_x, global_y)
            print(f"Checking color at global coordinates ({global_x}, {global_y}): R={color[0]}, G={color[1]}, B={color[2]}")
            print(f"Target color: R={target_color[0]}, G={target_color[1]}, B={target_color[2]}")
            if color_within_tolerance(color, target_color):
                print(f"Found: Target color {target_color} within tolerance at relative coordinates ({rel_x}, {rel_y}) within the app's window")
            else:
                print(f"Color at relative coordinates ({rel_x}, {rel_y}): R={color[0]}, G={color[1]}, B={color[2]} - Not matched")
        else:
            print(f"Coordinates ({rel_x}, {rel_y}) are outside the app's window bounds")
    else:
        print(f"Failed to get content area for PID {pid}")

# Shared event to control the thread behavior
color_event = threading.Event()

# Function to check if the color matches at the given coordinates
def is_color_matched(pid, target_color, relative_coordinate):
    content_area = get_content_area(pid)
    if content_area:
        a, b, content_width, content_height = content_area
        rel_x, rel_y = relative_coordinate
        if 0 <= rel_x < content_width and 0 <= rel_y < content_height:
            global_x, global_y = a + rel_x, b + rel_y
            color = get_color_at(global_x, global_y)
            print(f"[Debug] Color check at ({global_x}, {global_y}) | Detected: {color} | Target: {target_color}")
            return color_within_tolerance(color, target_color)
        print(f"[Warning] Coordinates {relative_coordinate} out of bounds")
    return False

def check_subthread_color(pid):
    # Define the special colors and their corresponding relative coordinates
    special_colors = [
        ((51, 117, 35), (198, 296)),  # Special 1
        ((141, 107, 43), (164, 300)),  # Special 2
        ((132, 24, 16), (134, 297))   # Special 3
    ]
    click_position = (90, 278)  # Position to click if any special is found

    while True:
        content_area = get_content_area(pid)
        if content_area:
            a, b, content_width, content_height = content_area

            for color, rel_coords in special_colors:
                rel_x, rel_y = rel_coords
                if 0 <= rel_x < content_width and 0 <= rel_y < content_height:
                    global_x = a + rel_x
                    global_y = b + rel_y

                    detected_color = get_color_at(global_x, global_y)
                    if color_within_tolerance(detected_color, color):
                        print(f"Special detected! Mouse at ({rel_x}, {rel_y}) within the app's window: "
                              f"R={detected_color[0]}, G={detected_color[1]}, B={detected_color[2]}")

                        # Perform click at the specified position
                        global_click_x = a + click_position[0]
                        global_click_y = b + click_position[1]
                        pyautogui.moveTo(global_click_x, global_click_y)
                        pyautogui.click()
                        print(f"Mouse clicked at ({global_click_x}, {global_click_y}).")
                        break  # Exit the loop after a click
        else:
            print("Content area not found for PID.")

        time.sleep(3)  # Short delay before checking again

def fight(pid):
    subthread = threading.Thread(target=check_subthread_color, args=(pid,))
    subthread.daemon = True  # Allow thread to exit when the program exits
    subthread.start()

    # Click position
    click_position = (467, 144)

    # Start and end points for the drag action
    start_position = (487, 180)
    end_position = (83, 181)

    while color_event.is_set():
        print("Fight thread is running while color is detected.")

        # Get content area to ensure correct position adjustments
        content_area = get_content_area(pid)
        if content_area:
            a, b, content_width, content_height = content_area

            while color_event.is_set():
                # Convert relative coordinates to global coordinates for the click position
                global_click_x = a + click_position[0]
                global_click_y = b + click_position[1]

                # Click three times with interval of 0.3 seconds
                for _ in range(3):
                    pyautogui.click(global_click_x, global_click_y)
                    print(f"Clicked at ({global_click_x}, {global_click_y}).")
                    time.sleep(0.3)  # 0.3 second interval between clicks

                # Drag forward from start to end
                global_start_x = a + start_position[0]
                global_start_y = b + start_position[1]
                global_end_x = a + end_position[0]
                global_end_y = b + end_position[1]

                pyautogui.moveTo(global_start_x, global_start_y)
                pyautogui.dragTo(global_end_x, global_end_y, duration=0.05, button='left')
                print(f"Dragged from ({global_start_x}, {global_start_y}) to ({global_end_x}, {global_end_y}).")

                # Drag backward from end to start
                pyautogui.moveTo(global_end_x, global_end_y)
                pyautogui.dragTo(global_start_x, global_start_y, duration=0.25, button='left')
                print(f"Dragged from ({global_end_x}, {global_end_y}) to ({global_start_x}, {global_start_y}).")

                time.sleep(0.2)  # 0.3 second interval between sequences
                #for _ in range(1):
                   # pyautogui.click(global_click_x, global_click_y)
                   # print(f"Clicked at ({global_click_x}, {global_click_y}).")
                   # time.sleep(0.3)  # 0.3 second interval between clicks

    print("Fight thread stopped as color is no longer detected.")

def check_color_thread(pid, target_color, relative_coordinate):
    fight_thread = None
    while True:
        matched = is_color_matched(pid, target_color, relative_coordinate)
        if matched:
            if not color_event.is_set():
                print("[Status] Combat color detected! Starting automation...")
                color_event.set()
                fight_thread = threading.Thread(target=fight, args=(pid,))
                fight_thread.daemon = True
                fight_thread.start()
        else:
            if color_event.is_set():
                print("[Status] Combat color disappeared. Stopping automation...")
                color_event.clear()
        time.sleep(1)