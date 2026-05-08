import tkinter as tk
from tkinter import messagebox
from datetime import datetime, timedelta

def parse_time(h, m, ampm):
    h = h.strip()
    m = m.strip()
    if not h: return None
    if not m: m = "00"
    try:
        # Using a dummy date to handle time objects with date math
        full_str = f"2026-01-01 {h}:{m} {ampm}"
        return datetime.strptime(full_str, "%Y-%m-%d %I:%M %p")
    except ValueError:
        return "error"

class DayColumn:
    def __init__(self, parent, day_num, col_index):
        self.day_num = day_num
        self.container = tk.Frame(parent, padx=8, pady=5, relief="groove", borderwidth=1)
        self.container.grid(row=0, column=col_index, sticky="nsew")

        tk.Label(self.container, text=f"Day {day_num}", font=("Arial", 10, "bold")).pack(pady=(0, 5))
        
        self.hour_entries = []
        self.min_entries = []
        self.toggles = []
        
        defaults = ["AM", "PM", "PM", "PM"]
        labels = ["Clock In", "Lunch Out", "Lunch In", "Final Out"]

        for i in range(4):
            tk.Label(self.container, text=labels[i], font=("Arial", 8), fg="#555").pack()
            row_frame = tk.Frame(self.container)
            row_frame.pack(pady=2)
            
            h_ent = tk.Entry(row_frame, width=3, justify='center')
            h_ent.pack(side='left')
            self.hour_entries.append(h_ent)
            
            tk.Label(row_frame, text=":").pack(side='left')
            
            m_ent = tk.Entry(row_frame, width=3, justify='center')
            m_ent.pack(side='left')
            self.min_entries.append(m_ent)

            btn = tk.Button(row_frame, text=defaults[i], width=3, font=("Arial", 7),
                            command=lambda b=i: self.toggle_ampm(b), takefocus=0)
            btn.pack(side='left', padx=2)
            self.toggles.append(btn)

        tk.Button(self.container, text="Calc Day", command=self.update_column_display, 
                  font=("Arial", 8), bg="#f0f0f0").pack(pady=5)
        
        self.lbl_total = tk.Label(self.container, text="0h 0m", fg="blue", font=("Arial", 9, "bold"))
        self.lbl_total.pack()
        self.day_minutes = 0

    def toggle_ampm(self, index):
        current = self.toggles[index].cget("text")
        self.toggles[index].config(text="PM" if current == "AM" else "AM")

    def update_column_display(self):
        result = self.get_minutes()
        if result == "error":
            messagebox.showerror("Input Error", f"Day {self.day_num}: Invalid time or impossible sequence.")
            return
        
        h, m = divmod(result, 60)
        self.lbl_total.config(text=f"{h}h {m}m")
        calculate_grand_total()

    def get_minutes(self):
        h_vals = [e.get().strip() for e in self.hour_entries]
        m_vals = [e.get().strip() for e in self.min_entries]
        amps = [b.cget("text") for b in self.toggles]

        if not h_vals[0] or not h_vals[3]:
            self.day_minutes = 0
            return 0

        times = [parse_time(h_vals[i], m_vals[i], amps[i]) for i in range(4)]
        if "error" in times: return "error"

        # Correct for Midnight Cross (Clock in 10pm, Clock out 6am)
        if times[3] <= times[0]:
            times[3] += timedelta(days=1)

        # Logic A: No Lunch (Lunch boxes are empty)
        if not h_vals[1] and not h_vals[2]:
            total_seconds = (times[3] - times[0]).total_seconds()
            self.day_minutes = int(round(total_seconds / 60))
        
        # Logic B: With Lunch
        else:
            # Shift lunch times if they cross midnight
            if times[1] < times[0]: times[1] += timedelta(days=1)
            if times[2] < times[1]: times[2] += timedelta(days=1)
            if times[3] < times[2]: times[3] += timedelta(days=1)

            morn = (times[1] - times[0]).total_seconds()
            aft = (times[3] - times[2]).total_seconds()
            
            if morn < 0 or aft < 0: return "error"
            self.day_minutes = int(round((morn + aft) / 60))

        return self.day_minutes

def calculate_grand_total():
    total_week_mins = sum(col.day_minutes for col in day_columns)
    hours, mins = divmod(total_week_mins, 60)
    lbl_week_total.config(text=f"Weekly Total: {total_week_mins} min ({hours}h {mins}m)")

# Main Setup
root = tk.Tk()
root.title("Hardened Time Card Tool")

grid_frame = tk.Frame(root, pady=10, padx=10)
grid_frame.pack()

day_columns = []
for i in range(1, 8):
    day_columns.append(DayColumn(grid_frame, i, i-1))

footer = tk.Frame(root, pady=15)
footer.pack()

tk.Button(footer, text="Refresh All", command=calculate_grand_total, 
          bg="#2E7D32", fg="white", font=("Arial", 10, "bold"), padx=20).pack(pady=5)

lbl_week_total = tk.Label(footer, text="Weekly Total: 0 min (0h 0m)", font=("Arial", 12, "bold"))
lbl_week_total.pack()

# This is the vital line that was likely missing or cut off:
root.mainloop()