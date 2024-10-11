import customtkinter
import cv2
import json
import keyboard
import multiprocessing
import os
import sys
import time
from tkinter import filedialog

customtkinter.set_appearance_mode("System")  # Modes: "System" (standard), "Dark", "Light"
customtkinter.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"

file_path_Json = "PLACEHOLDER"
file_path_MP4 = "PLACEHOLDER"
global_hex_color = "94FAE3"
global_color_threshold = 52
generate_status = "Ready"
keybinds = False
key_start = "i"
key_pause = "o"
key_stop = "p"
enable_key_start = True
enable_key_pause = True
enable_key_stop = True
pause_flag = multiprocessing.Value('b', False)
stop_flag = multiprocessing.Value('b', False)

#Chart Register
def chart_register(pause_flag, stop_flag):
    keystrokes = []
    start_time = time.time()
    total_pause_time = 0.00
    pause_start_time = 0.00

    def save_keystrokes(keystrokes, filename):
        with open(filename, 'w') as file:
            json.dump(keystrokes, file, indent=4)
        print("Json file saved successfully")

    def on_key_event(event):
        nonlocal keystrokes, start_time, total_pause_time, pause_start_time
        if stop_flag.value:
            with stop_flag.get_lock():
                stop_flag.value = False
            filename = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
            if filename:
                save_keystrokes(keystrokes, filename)
                keyboard.unhook_all()
            return

        with pause_flag.get_lock():
            if pause_flag.value:
                if pause_start_time == 0.00:
                    pause_start_time = time.time()
                else:
                    total_pause_time = time.time() - pause_start_time
            else:
                pause_start_time = 0.00
                elapsed_time = (time.time() - start_time) - total_pause_time
                keystroke = {
                    'key': event.name,
                    'time': elapsed_time
                }       
                keystrokes.append(keystroke)
                print("Pressed Key:", event.name, elapsed_time)

    keyboard.on_press(on_key_event)
    while True:
        pass
    

#Chart Player
def chart_player(file_path_Json, pause_flag, stop_flag):

    def load_keystrokes(file_path_Json):
        with open(file_path_Json, 'r') as file:
            keystrokes = json.load(file)
        return keystrokes

    def replay_keystrokes(keystrokes, pause_flag, stop_flag):
        start_time = time.time()
        for keystroke in keystrokes:
            if stop_flag.value:
                with stop_flag.get_lock():
                    stop_flag.value = False
                return
            while pause_flag.value:
                time.sleep(0.1)
            current_time = time.time()
            time_to_wait = keystroke['time'] - (current_time - start_time)

            if time_to_wait > 0:
                time.sleep(time_to_wait)
            keyboard.press(keystroke['key'])
            keyboard.release(keystroke['key'])
    try:
        keystrokes = load_keystrokes(file_path_Json)
        replay_keystrokes(keystrokes, pause_flag, stop_flag)
    except:
        print(f"Error: Cannot open Json file")
    return

#Chart Creator
def chart_cretor(file_path_MP4, global_hex_color, global_color_threshold):
    hex_color = global_hex_color
    output_json = 'output.json'
    color_threshold = global_color_threshold
    pixelKeys = {
        (458, 638): ('q'),
        (625, 638): ('w'),
        (792, 638): ('e'),
        (960, 638): ('r'),
        (1127, 638): ('t'),
        (1294, 638): ('y'),
        (1462, 638): ('u'),
        (458, 773): ('a'),
        (625, 773): ('s'),
        (792, 773): ('d'),
        (960, 773): ('f'),
        (1127, 773): ('g'),
        (1294, 773): ('h'),
        (1462, 773): ('j'),
        (458, 907): ('z'),
        (625, 907): ('x'),
        (792, 907): ('c'),
        (960, 907): ('v'),
        (1127, 907): ('b'),
        (1294, 907): ('n'),
        (1462, 907): ('m')
    }
    
    def hex_to_bgr(hex_color):
        return tuple(int(hex_color[i:i+2], 16) for i in (4, 2, 0))

    def red_distance(r1, r2):
        res = r2
        if r2 < 200:
            if r1 > r2:
                res = r1 - r2
            else:
                res = r2 - r1
        return res

    def analyze_frame(frame, pixelKeys, threshold, current_time, hex_color):
        changes = []
        for (x, y), (key) in pixelKeys.items():
            target_color = hex_to_bgr(hex_color)
            pixel_color = frame[y, x]
            target_red = target_color[2]
            pixel_red = pixel_color[2]
            if red_distance(target_red, pixel_red) <= threshold:
                changes.append(key)
                print(f"Pixels of key: {key}, Time: {current_time}")
        return changes

    def analyze_video(video_path, pixelKeys, output_json_path, threshold, hex_color):
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print("Error: Cannot open video file")
            return

        changes_log = []
        last_changes = {}
        frame_number = 0

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            current_time = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000
            changes = analyze_frame(frame, pixelKeys, threshold, current_time, hex_color)
            fps = cap.get(cv2.CAP_PROP_FPS)
            fps_skip = fps / 15

            for change in changes:
                if change not in last_changes or (frame_number - last_changes[change]) > fps_skip:
                    changes_log.append({"key": change, "time": current_time})
                    last_changes[change] = frame_number

            frame_number += 1

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        cap.release()
        cv2.destroyAllWindows()

        with open(output_json_path, 'w') as outfile:
            json.dump(changes_log, outfile, indent=4)

        print(f"Analysis complete. Changes saved to {output_json_path}")

    analyze_video(file_path_MP4, pixelKeys, output_json, color_threshold, hex_color)
    return

#Interface
class bonus_time(customtkinter.CTk):
    #Buttons
    def start_action(self):
        global file_path_Json
        global enable_key_start
        if self.tabview.get() == "Record":
            self.record_start_button.configure(state=customtkinter.DISABLED)
            self.play_start_button.configure(state=customtkinter.DISABLED)
            self.play_pause_button.configure(state=customtkinter.DISABLED)
            self.play_stop_button.configure(state=customtkinter.DISABLED)
            enable_key_start = False
            self.chart_register_process = multiprocessing.Process(target=chart_register, args=(pause_flag, stop_flag))
            self.chart_register_process.start()
            self.check_register_process()
        elif self.tabview.get() == "Play":
            self.play_start_button.configure(state=customtkinter.DISABLED)
            self.record_start_button.configure(state=customtkinter.DISABLED)
            self.record_pause_button.configure(state=customtkinter.DISABLED)
            self.record_stop_button.configure(state=customtkinter.DISABLED)
            enable_key_start = False
            self.chart_player_process = multiprocessing.Process(target=chart_player, args=(file_path_Json, pause_flag, stop_flag))
            self.chart_player_process.start()
            self.check_player_process()

    def pause_action(self):
        global pause_flag
        if self.tabview.get() == "Record":
            with pause_flag.get_lock():
                pause_flag.value = not pause_flag.value
        elif self.tabview.get() == "Play":
            with pause_flag.get_lock():
                pause_flag.value = not pause_flag.value

    def stop_action(self):
        global stop_flag
        global enable_key_start
        if self.tabview.get() == "Record":
            self.record_start_button.configure(state=customtkinter.NORMAL)
            self.play_start_button.configure(state=customtkinter.NORMAL)
            self.play_pause_button.configure(state=customtkinter.NORMAL)
            self.play_stop_button.configure(state=customtkinter.NORMAL)
            enable_key_start = True
            with stop_flag.get_lock():
                stop_flag.value = True
        elif self.tabview.get() == "Play":
            self.play_start_button.configure(state=customtkinter.NORMAL)
            self.record_start_button.configure(state=customtkinter.NORMAL)
            self.record_pause_button.configure(state=customtkinter.NORMAL)
            self.record_stop_button.configure(state=customtkinter.NORMAL)
            enable_key_start = True
            with stop_flag.get_lock():
                stop_flag.value = True

    def check_register_process(self):
        if self.chart_register_process.is_alive():
            self.after(100, self.check_register_process)
        else:
            self.on_chart_register_process_complete()

    def on_chart_register_process_complete(self):
        self.record_start_button.configure(state=customtkinter.NORMAL)
        self.play_start_button.configure(state=customtkinter.NORMAL)
        self.play_pause_button.configure(state=customtkinter.NORMAL)
        self.play_stop_button.configure(state=customtkinter.NORMAL)

    def check_player_process(self):
        if self.chart_player_process.is_alive():
            self.after(100, self.check_player_process)
        else:
            self.on_chart_player_process_complete()

    def on_chart_player_process_complete(self):
        self.play_start_button.configure(state=customtkinter.NORMAL)
        self.record_start_button.configure(state=customtkinter.NORMAL)
        self.record_pause_button.configure(state=customtkinter.NORMAL)
        self.record_stop_button.configure(state=customtkinter.NORMAL)

    def choose_json_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Json files", "*.json")])
        if file_path:
            file_name = os.path.basename(file_path)
            global file_path_Json
            file_path_Json = file_path
            self.json_label.configure(text=file_name)

    #Chart Creator
    def choose_mp4_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("MP4 files", "*.mp4")])
        if file_path:
            file_name = os.path.basename(file_path)
            global file_path_MP4
            file_path_MP4 = file_path
            self.mp4_label.configure(text=f"File Name: {file_name}")

    def update_slider_value(self, value):
        self.threshold_label.configure(text=f"Threshold: {int(value)}")
        global global_color_threshold
        global_color_threshold = int(value)

    def start_chart_creator(self):
        global generate_status
        generate_status = "Generating..."
        self.generate_label.configure(text=f"Status: {generate_status}")
        self.mp4_button.configure(state=customtkinter.DISABLED)
        self.generate_button.configure(state=customtkinter.DISABLED)
        self.threshold_slider.configure(state=customtkinter.DISABLED)
        self.chart_creator_process = multiprocessing.Process(target=chart_cretor, args=(file_path_MP4, global_hex_color, global_color_threshold))
        self.chart_creator_process.start()
        self.check_chart_process()

    def check_chart_process(self):
        if self.chart_creator_process.is_alive():
            self.after(100, self.check_chart_process)
        else:
            self.on_chart_process_complete()

    def on_chart_process_complete(self):
        global generate_status
        generate_status = "Ready"
        self.generate_label.configure(text=f"Status: {generate_status}")
        self.mp4_button.configure(state=customtkinter.NORMAL)
        self.generate_button.configure(state=customtkinter.NORMAL)
        self.threshold_slider.configure(state=customtkinter.NORMAL)

    #Start Key
    def start_setting_start_key(self):
        self.keybinds_set_start_button.configure(text="Press a key...")
        self.bind("<Key>", self.on_start_key_press)

    def on_start_key_press(self, event):
        self.key = event.keysym
        global key_start
        key_start = str(self.key)
        self.keybinds_set_start_button.configure(text=f"Start Key: {key_start.upper()}")
        self.unbind("<Key>")
        self.bind_keys()

    #Pasue Key
    def start_setting_pause_key(self):
        self.keybinds_set_pause_button.configure(text="Press a key...")
        self.bind("<Key>", self.on_pause_key_press)

    def on_pause_key_press(self, event):
        self.key = event.keysym
        global key_pause
        key_pause = str(self.key)
        self.keybinds_set_pause_button.configure(text=f"Pause Key: {key_pause.upper()}")
        self.unbind("<Key>")
        self.bind_keys()

    #Stop Key
    def start_setting_stop_key(self):
        self.keybinds_set_stop_button.configure(text="Press a key...")
        self.bind("<Key>", self.on_stop_key_press)

    def on_stop_key_press(self, event):
        self.key = event.keysym
        global key_stop
        key_stop = str(self.key)
        self.keybinds_set_stop_button.configure(text=f"Stop Key: {key_stop.upper()}")
        self.unbind("<Key>")
        self.bind_keys()
    
    #Update Keybinds
    def update_keybinds_state(self):
        global keybinds
        state = customtkinter.NORMAL if self.keybinds_switch.get() else customtkinter.DISABLED
        if self.keybinds_switch.get():
            keybinds = True
        else:
            keybinds = False
        self.keybinds_set_start_button.configure(state=state)
        self.keybinds_set_pause_button.configure(state=state)
        self.keybinds_set_stop_button.configure(state=state)
        self.bind_keys()

    def bind_keys(self):
        try:
            keyboard.clear_all_hotkeys()
        except:
            print("No previously saved hotkeys")
        keyboard.add_hotkey(key_start, self.start_action_if_enabled)
        keyboard.add_hotkey(key_pause, self.pause_action_if_enabled)
        keyboard.add_hotkey(key_stop, self.stop_action_if_enabled)

    def start_action_if_enabled(self):
        if keybinds and enable_key_start:
            self.start_action()

    def pause_action_if_enabled(self):
        if keybinds and enable_key_pause:
            self.pause_action()

    def stop_action_if_enabled(self):
        if keybinds and enable_key_stop:
            self.stop_action()

    #Others
    def change_appearance_mode_event(self, new_appearance_mode: str):
        customtkinter.set_appearance_mode(new_appearance_mode)

    def __init__(self):
        super().__init__()
        #Configure Window
        self.title("Entity378's Lyre Player 1.0")
        file_path = os.path.abspath(sys.argv[0])
        self.iconbitmap(False, file_path)


        #Configure Grid Layout (1x1)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.resizable(False, False)

        #Create Sidebar Frame (Main Frame)
        self.sidebar_frame = customtkinter.CTkFrame(self, width=140, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=4, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)
        self.logo_label = customtkinter.CTkLabel(self.sidebar_frame, text="Entity378's Lyre Player 1.0", font=customtkinter.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))
        self.appearance_mode_label = customtkinter.CTkLabel(self.sidebar_frame, text="Appearance Mode:", anchor="w")
        self.appearance_mode_label.grid(row=5, column=0, padx=20, pady=(10, 0))
        self.appearance_mode_optionemenu = customtkinter.CTkOptionMenu(self.sidebar_frame, values=["Light", "Dark", "System"], command=self.change_appearance_mode_event)
        self.appearance_mode_optionemenu.grid(row=6, column=0, padx=20, pady=(10, 10))

        #Create Tabview
        self.tabview = customtkinter.CTkTabview(self.sidebar_frame, width=250)
        self.tabview.grid(row=1, column=0, padx=(20, 20), pady=(20, 20), sticky="nsew")
        self.tabview.add("Record")
        self.tabview.add("Play")
        self.tabview.add("Generate Music Sheet")
        self.tabview.tab("Record").grid_columnconfigure(0, weight=1)
        self.tabview.tab("Play").grid_columnconfigure(0, weight=1)
        self.tabview.tab("Generate Music Sheet").grid_columnconfigure(0, weight=1)

        #Play 
        self.play_start_button = customtkinter.CTkButton(self.tabview.tab("Play"), text="Start", command=self.start_action)
        self.play_start_button.grid(row=2, column=0, padx=20, pady=(20, 10))

        self.play_pause_button = customtkinter.CTkButton(self.tabview.tab("Play"), text="Pause", command=self.pause_action)
        self.play_pause_button.grid(row=3, column=0, padx=20, pady=(20, 10))

        self.play_stop_button = customtkinter.CTkButton(self.tabview.tab("Play"), text="Stop", command=self.stop_action)
        self.play_stop_button.grid(row=4, column=0, padx=20, pady=(20, 10))

        #Record
        self.json_label = customtkinter.CTkLabel(self.tabview.tab("Play"), text="No files selected")
        self.json_label.grid(row=0, column=0, padx=20, pady=(20, 10))
        
        self.json_button = customtkinter.CTkButton(self.tabview.tab("Play"), text="Select Json file", command=self.choose_json_file)
        self.json_button.grid(row=1, column=0, padx=20, pady=(20, 10))

        self.record_start_button = customtkinter.CTkButton(self.tabview.tab("Record"), text="Start", command=self.start_action)
        self.record_start_button.grid(row=2, column=0, padx=20, pady=(20, 10))

        self.record_pause_button = customtkinter.CTkButton(self.tabview.tab("Record"), text="Pause", command=self.pause_action)
        self.record_pause_button.grid(row=3, column=0, padx=20, pady=(20, 10))

        self.record_stop_button = customtkinter.CTkButton(self.tabview.tab("Record"), text="Stop", command=self.stop_action)
        self.record_stop_button.grid(row=4, column=0, padx=20, pady=(20, 10))

        #Generate
        self.mp4_label = customtkinter.CTkLabel(self.tabview.tab("Generate Music Sheet"), text="No files selected")
        self.mp4_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.mp4_button = customtkinter.CTkButton(self.tabview.tab("Generate Music Sheet"), text="Select file.mp4", command=self.choose_mp4_file)
        self.mp4_button.grid(row=1, column=0, padx=20, pady=(20, 10))

        self.threshold_slider = customtkinter.CTkSlider(self.tabview.tab("Generate Music Sheet"), from_=0, to=255, number_of_steps=255, command=self.update_slider_value)
        self.threshold_slider.grid(row=3, column=0, padx=20, pady=(0, 10), sticky="ew")
        self.threshold_slider.set(global_color_threshold)
        
        self.threshold_label = customtkinter.CTkLabel(self.tabview.tab("Generate Music Sheet"), text=f"Threshold: {global_color_threshold}")
        self.threshold_label.grid(row=2, column=0, padx=20, pady=(20, 10))

        self.generate_button = customtkinter.CTkButton(self.tabview.tab("Generate Music Sheet"), text="Generate", command=self.start_chart_creator)
        self.generate_button.grid(row=4, column=0, padx=20, pady=(20, 10))

        self.generate_label = customtkinter.CTkLabel(self.tabview.tab("Generate Music Sheet"), text=f"Status: {generate_status}")
        self.generate_label.grid(row=5, column=0, padx=20, pady=(20, 10))

        #Others
        self.radiobutton_frame = customtkinter.CTkFrame(self.sidebar_frame, width=250)
        self.radiobutton_frame.grid(row=2, column=0, padx=(20, 20), pady=(20, 20), sticky="nsew")

        self.keybinds_switch = customtkinter.CTkSwitch(self.radiobutton_frame, text="Enable-keybinds", command=self.update_keybinds_state)
        self.keybinds_switch.grid(row=0, column=0, padx=60, pady=(10, 10))

        self.keybinds_set_start_button = customtkinter.CTkButton(self.radiobutton_frame, text=f"Start Key: {key_start.upper()}", command=self.start_setting_start_key)
        self.keybinds_set_start_button.grid(row=1, column=0, padx=30, pady=(20, 10))
        self.keybinds_set_start_button.configure(state=customtkinter.DISABLED)

        self.keybinds_set_pause_button = customtkinter.CTkButton(self.radiobutton_frame, text=f"Pause Key: {key_pause.upper()}", command=self.start_setting_pause_key)
        self.keybinds_set_pause_button.grid(row=2, column=0, padx=30, pady=(20, 10))
        self.keybinds_set_pause_button.configure(state=customtkinter.DISABLED)

        self.keybinds_set_stop_button = customtkinter.CTkButton(self.radiobutton_frame, text=f"Stop Key: {key_stop.upper()}", command=self.start_setting_stop_key)
        self.keybinds_set_stop_button.grid(row=3, column=0, padx=30, pady=(20, 10))
        self.keybinds_set_stop_button.configure(state=customtkinter.DISABLED)

if __name__ == "__main__":
    bonus_time = bonus_time()
    bonus_time.mainloop()