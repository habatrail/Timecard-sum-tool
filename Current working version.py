"""Time Card Sum Tool.

Type the four punches from a time card for each day and get daily and weekly
totals in hours:minutes and decimal hours. Only uses the Python standard
library (tkinter), so there is nothing to install.

Time entry accepts: 7   730   7:30   0730   7:30a   7:30p   19:30
AM/PM is worked out automatically: clock-in defaults to AM, and every later
punch is taken as the first matching time *after* the previous punch.
Add an "a" or "p" to any time to force it.
"""

import re

PUNCHES = ["Clock In", "Lunch Out", "Lunch In", "Clock Out"]
DAYS = 7
HALF_DAY = 12 * 60
FULL_DAY = 24 * 60


# --------------------------------------------------------------------------
# Pure logic (no GUI) – easy to test
# --------------------------------------------------------------------------

def parse_entry(text):
    """Parse a typed time.

    Returns None for blank, "error" for garbage, otherwise a tuple
    (minutes_into_half_day, forced_half) where forced_half is None (infer),
    0 (AM) or 1 (PM).
    """
    s = text.strip().lower().replace(" ", "").replace(".", "")
    if not s:
        return None
    m = re.fullmatch(r"(\d{1,2})(?::?(\d{2}))?(am|pm|a|p)?", s)
    if not m:
        return "error"
    hour = int(m.group(1))
    minute = int(m.group(2) or 0)
    suffix = m.group(3)
    if minute > 59:
        return "error"

    forced = None
    if suffix:
        if not 1 <= hour <= 12:
            return "error"
        forced = 0 if suffix.startswith("a") else 1
    elif hour > 12:          # 24-hour style, e.g. 19:30
        if hour > 23:
            return "error"
        forced = 1
        hour -= 12
    elif hour == 0:          # 0:30 means 12:30 AM
        forced = 0
    return ((hour % 12) * 60 + minute, forced)


def resolve_punches(entries):
    """Turn parsed entries into absolute minutes from midnight of the start day.

    Each punch after the first is placed at the earliest matching time that is
    not before the previous punch, so a 10:30 lunch after a 6:00 clock-in is
    10:30 AM and a 3:00 clock-out after lunch is 3:00 PM. Night shifts that
    cross midnight work the same way.
    """
    resolved = []
    prev = None
    for e in entries:
        if e is None or e == "error":
            resolved.append(e)
            continue
        base, forced = e
        if prev is None:
            t = base + (forced or 0) * HALF_DAY   # first punch: AM unless forced
        elif forced is None:
            t = base
            while t < prev:
                t += HALF_DAY
        else:
            t = base + forced * HALF_DAY
            while t < prev:
                t += FULL_DAY
        resolved.append(t)
        prev = t
    return resolved


def day_minutes(texts):
    """Compute worked minutes for one day from the four typed strings.

    Returns (minutes, times, message). minutes is None when the day can't be
    totalled; message says why. times are absolute minutes (or None/"error").
    """
    parsed = [parse_entry(t) for t in texts]
    times = resolve_punches(parsed)
    if "error" in parsed:
        return None, times, "Can't read a time"
    cin, lout, lin, cout = times
    if cin is None and cout is None and lout is None and lin is None:
        return 0, times, ""
    if cin is None or cout is None:
        return None, times, "Need clock in and out"
    if (lout is None) != (lin is None):
        return None, times, "Need both lunch times"
    if lout is None:
        total = cout - cin
    else:
        total = (lout - cin) + (cout - lin)
    return total, times, ""


def fmt_clock(t):
    """Absolute minutes -> '7:30 AM' (with '+1' if it lands on the next day)."""
    day, rem = divmod(t, FULL_DAY)
    h24, m = divmod(rem, 60)
    h12 = h24 % 12 or 12
    s = f"{h12}:{m:02d} {'AM' if h24 < 12 else 'PM'}"
    return s + ("  +1 day" if day else "")


def fmt_hm(minutes):
    h, m = divmod(minutes, 60)
    return f"{h}h {m:02d}m"


def fmt_dec(minutes):
    return f"{minutes / 60:.2f}"


# --------------------------------------------------------------------------
# GUI
# --------------------------------------------------------------------------

def main():
    import tkinter as tk
    from tkinter import messagebox

    BG = "#f4f5f7"
    CARD = "#ffffff"
    TEXT = "#1f2328"
    MUTED = "#6b7280"
    LINE = "#e3e5e8"
    ACCENT = "#2563eb"
    ERROR = "#c62828"
    FIELD = "#f9fafb"
    FONT = "Segoe UI"

    root = tk.Tk()
    root.title("Time Card Sum Tool")
    root.configure(bg=BG)
    root.resizable(False, False)

    # ---- header ----
    header = tk.Frame(root, bg=BG, padx=24, pady=18)
    header.pack(fill="x")
    tk.Label(header, text="Time Card", bg=BG, fg=TEXT,
             font=(FONT, 18, "bold")).pack(anchor="w")
    tk.Label(header, bg=BG, fg=MUTED, font=(FONT, 9), justify="left",
             text="Type times like 7, 730, 7:30 or 7:30p. AM/PM is worked out "
                  "from the order of punches; add a or p to force it."
             ).pack(anchor="w", pady=(2, 0))

    # ---- table card ----
    card = tk.Frame(root, bg=CARD, highlightbackground=LINE,
                    highlightthickness=1, padx=16, pady=10)
    card.pack(padx=24, fill="x")

    cols = ["Day"] + PUNCHES + ["Total", "Hours"]
    for c, name in enumerate(cols):
        tk.Label(card, text=name.upper(), bg=CARD, fg=MUTED,
                 font=(FONT, 8, "bold"), anchor="w"
                 ).grid(row=0, column=c, sticky="w", padx=8, pady=(0, 6))

    rows = []          # list of (entries, hints, total_lbl, dec_lbl, status_lbl)
    all_entries = []
    all_vars = []      # must keep StringVars alive, or their traces vanish

    def recalc(*_):
        week = 0
        for entries, hints, total_lbl, dec_lbl, status_lbl in rows:
            texts = [e.get() for e in entries]
            minutes, times, msg = day_minutes(texts)
            for e, h, t in zip(entries, hints, times):
                if t == "error":
                    h.config(text="?", fg=ERROR)
                    e.config(highlightbackground=ERROR, highlightcolor=ERROR)
                else:
                    h.config(text=fmt_clock(t) if t is not None else "", fg=MUTED)
                    e.config(highlightbackground=LINE, highlightcolor=ACCENT)
            if minutes is None:
                total_lbl.config(text="—", fg=MUTED)
                dec_lbl.config(text="")
                status_lbl.config(text=msg)
            else:
                week += minutes
                has_data = any(t.strip() for t in texts)
                total_lbl.config(text=fmt_hm(minutes) if has_data else "—",
                                 fg=TEXT if has_data else MUTED)
                dec_lbl.config(text=fmt_dec(minutes) if has_data else "")
                status_lbl.config(text="")
        week_hm.config(text=fmt_hm(week))
        week_dec.config(text=f"{fmt_dec(week)} hours  ·  {week} min")

    def focus_next(event):
        event.widget.tk_focusNext().focus_set()
        return "break"

    for d in range(DAYS):
        r = 1 + d * 2
        bg_row = CARD
        tk.Label(card, text=f"Day {d + 1}", bg=bg_row, fg=TEXT,
                 font=(FONT, 10, "bold"), anchor="w", width=6
                 ).grid(row=r, column=0, sticky="w", padx=8)
        entries, hints = [], []
        for p in range(len(PUNCHES)):
            var = tk.StringVar()
            var.trace_add("write", recalc)
            all_vars.append(var)
            e = tk.Entry(card, textvariable=var, width=9, justify="center",
                         font=(FONT, 11), relief="flat", bg=FIELD, fg=TEXT,
                         insertbackground=TEXT, highlightthickness=1,
                         highlightbackground=LINE, highlightcolor=ACCENT)
            e.grid(row=r, column=1 + p, padx=8, pady=(6, 0), ipady=4)
            e.bind("<Return>", focus_next)
            e.bind("<KP_Enter>", focus_next)   # numpad Enter
            e.bind("<FocusIn>", lambda ev: ev.widget.select_range(0, "end"))
            h = tk.Label(card, text="", bg=bg_row, fg=MUTED, font=(FONT, 8))
            h.grid(row=r + 1, column=1 + p, pady=(0, 4))
            entries.append(e)
            hints.append(h)
            all_entries.append(e)
        total_lbl = tk.Label(card, text="—", bg=bg_row, fg=MUTED,
                             font=(FONT, 11, "bold"), width=8, anchor="w")
        total_lbl.grid(row=r, column=5, padx=8, sticky="w")
        dec_lbl = tk.Label(card, text="", bg=bg_row, fg=MUTED,
                           font=(FONT, 10), width=6, anchor="w")
        dec_lbl.grid(row=r, column=6, padx=8, sticky="w")
        status_lbl = tk.Label(card, text="", bg=bg_row, fg=ERROR, font=(FONT, 8))
        status_lbl.grid(row=r + 1, column=5, columnspan=2, sticky="w", padx=8)
        rows.append((entries, hints, total_lbl, dec_lbl, status_lbl))

    # ---- footer ----
    footer = tk.Frame(root, bg=BG, padx=24, pady=18)
    footer.pack(fill="x")
    left = tk.Frame(footer, bg=BG)
    left.pack(side="left")
    tk.Label(left, text="WEEK TOTAL", bg=BG, fg=MUTED,
             font=(FONT, 8, "bold")).pack(anchor="w")
    week_hm = tk.Label(left, text="0h 00m", bg=BG, fg=TEXT,
                       font=(FONT, 22, "bold"))
    week_hm.pack(anchor="w")
    week_dec = tk.Label(left, text="0.00 hours  ·  0 min", bg=BG, fg=MUTED,
                        font=(FONT, 10))
    week_dec.pack(anchor="w")

    def clear_all():
        if any(e.get().strip() for e in all_entries):
            if not messagebox.askyesno("Clear all", "Clear every time on the card?"):
                return
        for e in all_entries:
            e.delete(0, "end")     # triggers recalc via the StringVar trace
        all_entries[0].focus_set()

    tk.Button(footer, text="Clear all", command=clear_all, bg=CARD, fg=TEXT,
              activebackground=LINE, relief="flat", font=(FONT, 10),
              highlightthickness=1, highlightbackground=LINE,
              padx=16, pady=6, cursor="hand2").pack(side="right", anchor="s")

    recalc()
    all_entries[0].focus_set()
    root.mainloop()


if __name__ == "__main__":
    main()
