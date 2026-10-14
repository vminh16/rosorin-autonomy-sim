"""Dark full-screen backdrop for the demo recording; exits when the stop file appears."""
import os
import sys
import tkinter as tk
stop = sys.argv[1]
root = tk.Tk(); root.title('demo-backdrop')
root.geometry('1920x1080+0+0'); root.configure(bg='#15181d')
tk.Label(root, text='ROSOrin Pro  ·  Gazebo · SLAM · Nav2', fg='#3a414c', bg='#15181d',
         font=('DejaVu Sans', 28, 'bold')).place(x=1150, y=400)
def poll():
    if os.path.exists(stop):
        root.destroy(); return
    root.after(300, poll)
poll(); root.mainloop()
