import os
import subprocess
import time
import json
import traceback
from PIL import Image
from PIL import ImageGrab
from google import genai
from AppKit import NSScreen


# Initialize Gemini
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

def take_screenshot(path='screenshot.png'):
    screenshot = ImageGrab.grab()
    screenshot.save(path)
    return path


def ask_gemini_for_coordinates_with_screenshot(prompt, image_path):
    image = Image.open(image_path)
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[
            image,
            f"I want to click {prompt} within the given screenshot. Give a bounding box for the target as box_2d array and detailed information what you found there and why you selected this. Always respond as a json object with an attribute box_2d that contains an array [y_min, x_min, y_max, x_max]. ignore the terminal on the bottom half of the screen. Take the relative coordinates, which are always calculated on a base of 1000px width and 1000px height and then research the given item within the calculated bounding box. repeat this until you have a bounding box that actually fits and describe how many iterations you required to actually find the correct bounding box."
        ])
    return response.text


def click_center_of_box(detections_json):
    detections = json.loads(detections_json)

    screen_width = NSScreen.mainScreen().frame().size.width
    screen_height = NSScreen.mainScreen().frame().size.height

    print(f"Width: {screen_width}")
    print(f"Height: {screen_height}")

    y1, x1, y2, x2 = detections["box_2d"]

    # Calculate center in reference space
    center_x_rel = (x1 + x2) / 2
    center_y_rel = (y1 + y2) / 2

    # Scale to actual screen size
    center_x_abs = int(center_x_rel * screen_width / 1000)
    center_y_abs = int(center_y_rel * screen_height / 1000)

    x_abs = int(x1 * screen_width / 1000)
    y_abs = int(y1 * screen_height / 1000)

    # Click using cliclick
    command = ["cliclick", f"c:{center_x_abs},{center_y_abs}"]
    print(f"About to perform: {command}")
    subprocess.run(command)

def extract_json(response_text):
    print(f"DEBUG RESPONSE: {response_text}")
    lines = response_text.splitlines()
    script_lines = []
    recording = False
    for line in lines:
        if "```json" in line:
            recording = True
            continue
        elif "```" in line and recording:
            break
        if recording:
            script_lines.append(line)
    return "\n".join(script_lines)


def save_and_execute_script(script, filename="action.sh"):
    with open(filename, "w") as f:
        f.write(script)
    subprocess.run(["sh", filename])


def main_loop():
    while True:
        prompt = input("Enter your action (or 'exit' to quit): ")
        if prompt.lower() == "exit":
            break
        image_path = take_screenshot()
        print("Screenshot taken. Sending to Gemini...")
        try:
            response = ask_gemini_for_coordinates_with_screenshot(prompt, image_path)
            json_response = extract_json(response)
            click_center_of_box(json_response)

            #if script:
            #    if any("replace with" in line.lower() for line in script.splitlines()):
            #        print("Found placeholder comment. Asking Gemini to refine the script...")
            #        refined_response = ask_gemini_to_refine(prompt, image_path)
            #        refined_script = extract_script(refined_response)
            #        if refined_script:
            #            script = refined_script
            #    print(f"Executing script: {script}")
            #    save_and_execute_script(script)
            #else:
            #    print(f"No script found in response: {response}")
        except Exception as e:
            print(traceback.format_exc(e))
        time.sleep(1)


if __name__ == "__main__":
    main_loop()
