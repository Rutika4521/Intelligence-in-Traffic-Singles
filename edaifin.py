import cv2
import tkinter as tk
from ultralytics import YOLO
from PIL import Image, ImageTk
from tkinter import ttk
import time
import threading


class SmartTrafficControl:
    def __init__(self, master):
        self.master = master
        self.master.title("Smart Traffic Control System")
        self.master.geometry("1280x720")
        self.master.configure(bg="#D6E0E0")

        # Variables
        self.is_detecting = False
        self.cap = None
        self.model = YOLO("C:\\Users\\Swaraj Patil\\Desktop\\best.pt")
        self.default_green_duration = 10
        self.vehicle_counts = {lane: 0 for lane in ['Lane 1', 'Lane 2', 'Lane 3', 'Lane 4']}
        self.current_light = 0  # Active lane index
        self.lanes = ['Lane 1', 'Lane 2', 'Lane 3', 'Lane 4']

        # UI Setup
        self.setup_ui()

    def setup_ui(self):
        # Header
        tk.Label(self.master, text="Smart Traffic Control System", bg="#333333", fg="white",
                 font=("Helvetica", 20, "bold")).pack(side="top", fill="x")

        # Main Frame
        self.main_frame = tk.Frame(self.master, bg="#D6E0E0")
        self.main_frame.pack(fill="both", expand=True)

        # Video Display
        self.video_frame = tk.Label(self.main_frame, bd=2, relief="solid")
        self.video_frame.pack(side="left", fill="both", expand=True, padx=10)

        # Control Panel
        control_panel = tk.Frame(self.main_frame, bg="#D6E0E0")
        control_panel.pack(side="right", fill="y", padx=10)

        # Status
        self.status_label = tk.Label(control_panel, text="Status: Idle", bg="#D6E0E0", font=("Helvetica", 12))
        self.status_label.pack(pady=5)

        # Timer and Vehicle Counts
        self.timer_label = tk.Label(control_panel, text="Green Light Timer: 0 sec", bg="#D6E0E0",
                                    font=("Helvetica", 14, "bold"))
        self.timer_label.pack(pady=10)

        self.vehicle_count_labels = {}
        for lane in self.lanes:
            label = tk.Label(control_panel, text=f"{lane} Vehicle Count: 0", bg="#D6E0E0", font=("Helvetica", 12))
            label.pack(pady=5)
            self.vehicle_count_labels[lane] = label

        # Default Green Light Slider
        self.add_slider(control_panel, "Default Green Light Duration (sec)", 5, 30, self.default_green_duration,
                        self.update_default_green_duration)

        # Start and Stop Buttons
        ttk.Button(control_panel, text="Start System", command=self.start_detection).pack(fill="x", pady=5)
        ttk.Button(control_panel, text="Stop System", command=self.stop_detection).pack(fill="x", pady=5)

        # Traffic Signal Canvas
        self.signal_canvas = tk.Canvas(control_panel, bg="#D6E0E0", height=200)
        self.signal_canvas.pack(pady=20)

        # Progress Bar for Timer
        self.progress_bar = ttk.Progressbar(control_panel, orient="horizontal", length=200, mode="determinate")
        self.progress_bar.pack(pady=10)

        # Create signals
        self.signals = {}
        self.create_signals()

    def add_slider(self, parent, label, min_val, max_val, default, command):
        tk.Label(parent, text=label, bg="#D6E0E0", font=("Helvetica", 12)).pack(anchor="w")
        slider = ttk.Scale(parent, from_=min_val, to=max_val, orient="horizontal", command=command)
        slider.set(default)
        slider.pack(fill="x", pady=5)
        return slider

    def create_signals(self):
        positions = [(40, 20, 100, 80), (110, 20, 170, 80), (180, 20, 240, 80), (250, 20, 310, 80)]
        for i, lane in enumerate(self.lanes):
            self.signals[lane] = self.signal_canvas.create_oval(*positions[i], fill="red", outline="black", width=2)

    def update_default_green_duration(self, value):
        self.default_green_duration = int(float(value))
        self.status_label.config(text=f"Default Green Light: {self.default_green_duration} sec")

    def start_detection(self):
        if not self.is_detecting:
            self.is_detecting = True
            self.cap = cv2.VideoCapture(0)
            threading.Thread(target=self.detect_traffic).start()
            threading.Thread(target=self.control_traffic_lights).start()
            self.status_label.config(text="Status: Running")

    def stop_detection(self):
        if self.is_detecting:
            self.is_detecting = False
            if self.cap:
                self.cap.release()
            self.status_label.config(text="Status: Stopped")

    def detect_traffic(self):
        while self.is_detecting:
            ret, frame = self.cap.read()
            if not ret:
                continue

            results = self.model(frame)
            vehicle_count = 0

            for result in results:
                for box in result.boxes.data.cpu().numpy():
                    _, _, _, _, _, class_id = box
                    label = self.model.names[int(class_id)]
                    if label in ['car', 'truck', 'bus', 'motorbike']:
                        vehicle_count += 1

            # Update vehicle count for the active lane
            current_lane = self.lanes[self.current_light]
            self.vehicle_counts[current_lane] = vehicle_count
            self.vehicle_count_labels[current_lane].config(text=f"{current_lane} Vehicle Count: {vehicle_count}")

            # Annotate frame
            annotated_frame = results[0].plot()
            img = Image.fromarray(cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB))
            imgtk = ImageTk.PhotoImage(image=img)
            self.video_frame.imgtk = imgtk
            self.video_frame.config(image=imgtk)

    def control_traffic_lights(self):
        while self.is_detecting:
            for i, lane in enumerate(self.lanes):
                self.current_light = i

                # Update signals for all lanes
                for signal_lane, signal in self.signals.items():
                    color = "green" if signal_lane == lane else "red"
                    self.signal_canvas.itemconfig(signal, fill=color)

                # Determine green light duration for the active lane
                vehicle_count = self.vehicle_counts[lane]
                green_duration = self.default_green_duration

                # Adjust green duration based on vehicle count and lane
                if lane == 'Lane 2':
                    green_duration += self.vehicle_counts['Lane 1'] // 2  # Lane 2 depends on Lane 1
                elif lane == 'Lane 3':
                    green_duration += self.vehicle_counts['Lane 2'] // 2  # Lane 3 depends on Lane 2
                elif lane == 'Lane 4':
                    green_duration += self.vehicle_counts['Lane 1'] // 2  # Lane 4 depends on Lane 1

                self.update_timer(green_duration)
                time.sleep(green_duration)

    def update_timer(self, duration):
        self.progress_bar["maximum"] = duration
        for remaining in range(duration, 0, -1):
            if not self.is_detecting:
                break
            self.timer_label.config(text=f"Green Light Timer: {remaining} sec")
            self.progress_bar["value"] = duration - remaining
            time.sleep(1)


if __name__ == "__main__":
    root = tk.Tk()
    app = SmartTrafficControl(root)
    root.mainloop()
