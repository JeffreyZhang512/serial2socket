# ------------------------------------------------------------------------------
#     Copyright (c) 2023
#     Author: Zhang, Jeffrey <jeffreyzh512@outlook.com>
# ------------------------------------------------------------------------------

from serial_agent_utils import debug_print, debug_sprint, get_current_folder, dialog
from serial_agent_resource import *
from serial_agent_emulator import *
from tkinter import *
from tkinter import messagebox
from tkinter import ttk
from PIL import Image, ImageTk, ImageEnhance
from time import *
import tkinter.font as tkFont
import re
import sys
import threading
import numpy
import serial
import time
import json
import socket
import select

SERIAL_PORT_NOT_CONNECTED = 0
SERIAL_PORT_CONNECTED = 1

TCP_SERVER_NOT_STARTED = 0
TCP_SERVER_LISTENING = 1
TCP_SERVER_CONNECTED = 2

TCP_SERVER_LISTENING_PORT_DEFAULT = 27025

TCP_CLIENT_NOT_CONNECTED = 0
TCP_CLIENT_CONNECTING = 1
TCP_CLIENT_CONNECTED = 2

serial_port_state = ["not connected", "connected"]
tcp_server_state = ["not started", "listening", "connected"]
tcp_client_state = ["not connected", "connecting", "connected"]

# For log
LOG_SEVERITY_INFO = 0
LOG_SEVERITY_WARNING = 1
LOG_SEVERITY_ERROR = 2
LOG_SEVERITY_COMMAND = 3

class enter_serial_port_name(dialog):

    def __init__(self, parent, hide_parent = True, title = ""):
        self.parent = parent
        self.hide_parent = hide_parent
        dialog.__init__(self, parent, hide_parent, always_on_top = False, always_grab_focus = True, title = title)


    def validate(self):
        serial_port_name = self.serial_port.get()
        if serial_port_name.find("COM") == -1 and serial_port_name.find("tty") == -1:
            return False
        self.parent.serial_port_name = serial_port_name
        return True


    def ok(self, event = None):
        self.parent.ok_clicked = True
        dialog.ok(self)
    

    def body(self):
        frm = Frame(self)
        frm.pack(side = TOP)
        frm1 = Frame(frm)
        frm1.pack(side = TOP, anchor = W)
        Label(frm1, text = "Serial Port Name: ", font = ("Calibri", 11)).pack(side = LEFT, fill = NONE, expand = FALSE, padx = 15, pady = 5)
        self.serial_port = Entry(frm, width = 25, font = ("Calibri", 11))
        self.serial_port.pack(side = TOP, fill = NONE, expand = FALSE, padx = 15, pady = 5)
        self.button_ok = Button(frm, text = "Ok", width = 10, default = ACTIVE, command = self.ok)
        self.button_ok.pack(side = LEFT, fill = NONE, expand = FALSE, padx = 15, pady = 5)
        self.button_cancel = Button(frm, text = "Cancel", width = 10, default = ACTIVE, command = self.cancel)
        self.button_cancel.pack(side = RIGHT, fill = NONE, expand = FALSE, padx = 15, pady = 5)
        self.serial_port.insert(END, self.parent.serial_port_name)
        self.serial_port.bind("<Return>", self.ok)
        return self.serial_port



class enter_tcp_server_address(dialog):

    def __init__(self, parent, hide_parent = True, title = ""):
        self.parent = parent
        self.hide_parent = hide_parent
        dialog.__init__(self, parent, hide_parent, always_on_top = False, always_grab_focus = True, title = title)

    def validate(self):
        address = self.server_address.get()
        port = self.server_port.get()

        if address.strip() == str():
            messagebox.showerror(title = "Error!", message = "The TCP server address is empty")
            return False
            
        if port.isnumeric():
            port_no = int(port)
        else:
            port_no = TCP_SERVER_LISTENING_PORT_DEFAULT
            messagebox.showerror(title = "Error!", message = "The TCP server listening port is wrong")
            return False
            
        if port_no < 0 or port_no > 65535:
            port_no = TCP_SERVER_LISTENING_PORT_DEFAULT
            messagebox.showerror(title = "Error!", message = "The TCP server listening port is wrong")
            return False
           
        self.parent.tcp_client_remote_address = (address, port_no)
        return True


    def ok(self, event = None):
        self.parent.ok_clicked = True
        dialog.ok(self)
        
    
    def body(self):
        frm = Frame(self)
        frm.pack(side = TOP)
        frm1 = Frame(frm)
        frm1.pack(side = TOP, anchor = W)
        Label(frm1, text = "TCP Server Adress: ", font = ("Calibri", 11)).pack(side = LEFT, fill = NONE, expand = FALSE, padx = 15, pady = 5)

        frm2 = Frame(frm)
        frm2.pack(side = TOP, anchor = W)
        self.server_address = Entry(frm2, width = 16, font = ("Calibri", 11))
        self.server_address.pack(side = LEFT, fill = NONE, expand = FALSE, padx = 15, pady = 5)
        Label(frm2, text = ":", font = ("Calibri", 11)).pack(side = LEFT, fill = NONE, expand = FALSE, pady = 5)
        self.server_port = Entry(frm2, width = 6, font = ("Calibri", 11))
        self.server_port.pack(side = LEFT, fill = NONE, expand = FALSE, padx = 15, pady = 5)

        # tcp_client_remote_address
        self.server_address.insert(END, self.parent.tcp_client_remote_address[0])
        self.server_port.insert(END, str(self.parent.tcp_client_remote_address[1]))
                
        self.button_ok = Button(frm, text = "Ok", width = 10, default = ACTIVE, command = self.ok)
        self.button_ok.pack(side = LEFT, fill = NONE, expand = FALSE, padx = 15, pady = 5)
        self.button_cancel = Button(frm, text = "Cancel", width = 10, default = ACTIVE, command = self.cancel)
        self.button_cancel.pack(side = RIGHT, fill = NONE, expand = FALSE, padx = 15, pady = 5)
        return self.server_address



class serial_agent(dialog):

    def __init__(self, parent, hide_parent = True, title = ""):
        self.hide_parent = hide_parent
        self.serial_port_state = SERIAL_PORT_NOT_CONNECTED
        self.serial_port_name = None
        # Serial port open or not - Initial value is not open
        self.serial_port = None
        # TCP Server running or not - Initial value is not running
        self.tcp_server_state = TCP_SERVER_NOT_STARTED
        self.tcp_server_listening_port = TCP_SERVER_LISTENING_PORT_DEFAULT
        self.tcp_server_connection = None
        self.tcp_server_remote_address = None
        # TCP client
        self.tcp_client_state = TCP_CLIENT_NOT_CONNECTED
        self.tcp_client_remote_address = ("127.0.0.1", TCP_SERVER_LISTENING_PORT_DEFAULT)
        self.tcp_client_connection = None
        # The flag to indicate if the ok button is clicked in the dialog
        self.ok_clicked = False
        # Load settings
        self.load_settings()
        dialog.__init__(self, parent, hide_parent, always_on_top = False, always_grab_focus = False, title = title)
        # String to store the data received from the client which is used in emulation mode
        self.receive_from_client = str()

    def body(self):
        # Main Window

        self.geometry("1200x800")
        
        self.image_width = 48
        self.image_height = 48

        # Button image
        try:
            pil_image = Image.fromarray(run_button_image)
            pil_image = pil_image.resize((self.image_width, self.image_height), Image.Resampling.LANCZOS)
 
            pil_image_low_brightness = ImageEnhance.Brightness(pil_image).enhance(0.75)
            
            self.tk_image = ImageTk.PhotoImage(image = pil_image)
            self.tk_image_low_brightness = ImageTk.PhotoImage(image = pil_image_low_brightness)
        except:
            self.load_image = False
        else:
            self.load_image = True
        
        # Controls
        font_id = tkFont.Font(family = 'Calibri', size = 11)

        # Enter AT
        frm = Frame(self)
        frm.pack(side = TOP, fill = X)
        # Label
        Label(frm, text = "Enter AT Command: ", font = font_id).pack(side = LEFT, fill = NONE, expand = FALSE, padx = 5)
        # Entry for AT Command
        self.enter_at = Entry(frm, width = 40, font = font_id, state = DISABLED)
        self.enter_at.pack(side = LEFT, fill = NONE, expand = FALSE)

        # Space
        Frame(frm, width = 60).pack(side = LEFT, fill = NONE, expand = FALSE)

        # TCP Server
        Label(frm, text = "TCP Server Listening Port: ", font = font_id).pack(side = LEFT, fill = NONE, expand = FALSE)
        # Entry for TCP Server Listening Port
        self.enter_tcp_listening_port = Entry(frm, width = 6, font = font_id)
        self.enter_tcp_listening_port.pack(side = LEFT, fill = NONE, expand = FALSE)
        self.enter_tcp_listening_port.insert(END, str(self.tcp_server_listening_port))
        # Space
        Frame(frm, width = 20).pack(side = LEFT, fill = NONE, expand = FALSE)
        # Checkbox for emulator
        self.emulator = False
        self.emulator_on = Checkbutton(frm,text = 'Emulator On', font = font_id, command = self.enable_disable_emulator)
        self.emulator_on.pack(side = LEFT, fill = NONE, expand = FALSE)
        
        # Button
        if self.load_image == False:
            self.button_run = Button(frm, text = "Start", default = ACTIVE, command = self.start_stop_tcp_server)
            self.button_run.pack(side = LEFT, fill = NONE, expand = FALSE, padx = 15)
        else:    
            self.canvas = Canvas(frm, height = 48)
            self.canvas.pack(side = LEFT, fill = NONE, expand = FALSE, padx = 15)
            self.canvas.create_image(self.image_width / 2, self.image_height / 2, image = self.tk_image)
            self.canvas.bind('<ButtonPress-1>', self.run_button_press_handler)

        # Text box for detailed information
        frm1 = Frame(self)
        frm1.pack(side = TOP, fill = BOTH, expand = TRUE)
        self.text_details = Text(frm1, font = ("Calibri", 11), state = DISABLED)
        self.text_details.pack(side = LEFT, padx=3, pady = 3, fill = BOTH, expand = TRUE)

        # Scroll bar
        scroll_bar = Scrollbar(frm1)
        scroll_bar.pack(side = RIGHT, fill = Y)
        scroll_bar.config(command = self.text_details.yview)
        self.text_details.config(yscrollcommand = scroll_bar.set)
        
        # Status bar
        frm2 = Frame(self)
        frm2.pack(side = TOP, anchor = W)
        self.status_bar = StringVar()        
        Label(frm2, bd = 1, relief = SUNKEN, textvariable = self.status_bar, font = ("Calibri", 11), padx = 5, pady = 5).pack(side = LEFT)
        self.update_status_bar_info()
        
        # Menu
        menubar = Menu(self)
        filemenu = Menu(menubar, tearoff = 0)
        menubar.add_cascade(label = "File", menu = filemenu)
        filemenu.add_command(label = "Open Serial Port", command = self.do_open_serial_port, accelerator = 'Ctrl+O')
        filemenu.add_command(label = "Close Serial Port", command = self.do_close_serial_port, accelerator = 'Ctrl+L')
        filemenu.add_separator()    # Add a separator
        filemenu.add_command(label = "Start TCP Client", command = self.do_start_tcp_client)
        filemenu.add_command(label = "Stop TCP Client", command = self.do_stop_tcp_client)
        filemenu.add_separator()    # Add a separator
        filemenu.add_command(label = "Start TCP Server", command = self.do_start_tcp_server)
        filemenu.add_command(label = "Stop TCP Server", command = self.do_stop_tcp_server)
        filemenu.add_separator()    # Add a separator
        filemenu.add_command(label = 'Exit', command = self.cancel) # call tkinter quit() 

        helpmenu = Menu(menubar, tearoff = 0)
        menubar.add_cascade(label = 'Help', menu = helpmenu)
        helpmenu.add_command(label = 'About', command = self.do_dummy)

        self.bind("<Control-o>", self.open_serial_port)
        self.bind("<Control-l>", self.close_serial_port)

        # Show the menu
        self.config(menu = menubar)
        self.enter_at.focus_set()

        self.enter_at.bind("<Return>", self.send_command_to_serial_port)

        
    def cancel(self):
        # Let the Rx thread quit
        dialog.cancel(self)

        
    def do_dummy(self):
        print("Dummy action")


    def enable_disable_emulator(self):
        if self.emulator == False:
            self.emulator = True
            self.emulator_on.select()
        else:
            self.emulator = False
            self.emulator_on.deselect()
        
        
    def start_stop_tcp_server(self):
        if self.tcp_server_state == TCP_SERVER_NOT_STARTED:
            if self.tcp_client_state != TCP_CLIENT_NOT_CONNECTED:
                response = messagebox.askquestion(title='Warning',message = "Need stop the TCP client first, continue?") 
                if response == "no":
                    return
                else:
                    self.start_stop_tcp_client()

            listening_port_string = self.enter_tcp_listening_port.get()
            if listening_port_string.isnumeric():
                self.tcp_server_listening_port = int(listening_port_string)
                if self.tcp_server_listening_port < 0 or self.tcp_server_listening_port > 65535:
                    self.tcp_server_listening_port = TCP_SERVER_LISTENING_PORT_DEFAULT
                    messagebox.showerror(title = "Error!", message = "The TCP server listening port is wrong")
                    return
            else:
                # Wrong port number
                messagebox.showerror(title = "Error!", message = "The TCP server listening port is wrong")
                return
            
            if self.load_image == False:
                self.button_run.configure(state = DISABLED)
            else:
                self.canvas.delete(ALL)
                self.canvas.create_image(self.image_width / 2, self.image_height / 2, image = self.tk_image_low_brightness)
            # Disable the AT entry in server mode
            self.enter_at.configure(state = DISABLED)
            self.tcp_server_state = TCP_SERVER_LISTENING
            self.thread_tcp_server = threading.Thread(target = self.tcp_server)
            self.thread_tcp_server.daemon = True
            self.thread_tcp_server.start()
        else:
            if self.load_image == False:
                self.button_run.configure(state = NORMAL)
            else:
                self.canvas.delete(ALL)
                self.canvas.create_image(self.image_width / 2, self.image_height / 2, image = self.tk_image)
            if self.serial_port_state == SERIAL_PORT_CONNECTED:
                self.enter_at.configure(state = NORMAL)
            self.tcp_server_state = TCP_SERVER_NOT_STARTED 
        self.update_status_bar_info()


    def do_start_tcp_server(self):
        if self.tcp_server_state != TCP_SERVER_NOT_STARTED:
            messagebox.showerror(title = "Error!", message = "The TCP server is already started")
            return
        self.start_stop_tcp_server()
        
        
    def do_stop_tcp_server(self):
        if self.tcp_server_state == TCP_SERVER_NOT_STARTED:
            messagebox.showerror(title = "Error!", message = "The TCP server is not started")
            return
        self.start_stop_tcp_server()
        

    def start_stop_tcp_client(self):
        if self.tcp_client_state == TCP_CLIENT_NOT_CONNECTED:
            if self.serial_port_state != SERIAL_PORT_NOT_CONNECTED or self.tcp_server_state != TCP_SERVER_NOT_STARTED:
                response = messagebox.askquestion(title='Warning',message = "Need close the serial port and stop the TCP server first, continue?") 
                if response == "no":
                    return
                    
            if self.serial_port_state != SERIAL_PORT_NOT_CONNECTED:
                self.open_close_serial_port()

            if self.tcp_server_state != TCP_SERVER_NOT_STARTED:
                self.start_stop_tcp_server()
            
            enter_tcp_server_address(self, False, "Enter TCP Server Address")
            if self.ok_clicked == False:
                return
            else:
                self.ok_clicked = False
                
            self.tcp_client_connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.tcp_client_connection.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.tcp_client_connection.setblocking(False)
            try:
                # In nonblcoking modem the connect will return immediately. But it doesn't mean the 
                # connection is established successfully. 
                self.tcp_client_connection.connect(self.tcp_client_remote_address)
            except Exception as e:
                print(e)

            self.tcp_client_state = TCP_CLIENT_CONNECTING
            self.thread_tcp_client = threading.Thread(target = self.tcp_client)
            self.thread_tcp_client.daemon = True
            self.thread_tcp_client.start()
        else:
            self.tcp_client_state = TCP_CLIENT_NOT_CONNECTED
        self.update_status_bar_info()

    def do_start_tcp_client(self):
        if self.tcp_client_state == TCP_CLIENT_CONNECTED:
            messagebox.showerror(title = "Error!", message = "The TCP client is already connected")
            return
        self.start_stop_tcp_client()


    def do_stop_tcp_client(self):
        if self.tcp_client_state == TCP_CLIENT_NOT_CONNECTED:
            messagebox.showerror(title = "Error!", message = "The TCP client is not connected")
            return
        self.start_stop_tcp_client()


    def run_button_press_handler(self, event):
        x = event.x
        y = event.y
        if x > 5 and x < self.image_width - 5 and y > 5 and y < self.image_height - 5:
            self.start_stop_tcp_server()


    def update_status_bar_info(self):
        state_string = "TCP client " + tcp_client_state[self.tcp_client_state]
        if self.tcp_client_state != TCP_CLIENT_NOT_CONNECTED:
            state_string = state_string + " - " + self.tcp_client_remote_address[0] + ":" + str(self.tcp_client_remote_address[1]) + "; "
        else:
            state_string = state_string + "; "

        state_string = state_string + "TCP server " + tcp_server_state[self.tcp_server_state]
        if self.tcp_server_state == TCP_SERVER_CONNECTED:
            state_string = state_string + " - " + self.tcp_server_remote_address[0] + ":" + str(self.tcp_server_remote_address[1]) + "; "
        else:
            state_string = state_string + ", "

        state_string = state_string + "serial port " + serial_port_state[self.serial_port_state]
        if self.serial_port_state == SERIAL_PORT_CONNECTED:
            state_string = state_string + " - " + self.serial_port_name
        
        self.status_bar.set(state_string)
        
        if self.tcp_server_state != TCP_SERVER_NOT_STARTED:
            self.enter_at.configure(state = DISABLED)
        elif self.serial_port_state == SERIAL_PORT_CONNECTED or self.tcp_client_state == TCP_CLIENT_CONNECTED:
            self.enter_at.configure(state = NORMAL)
        else:
            self.enter_at.configure(state = DISABLED)

        if self.tcp_server_state == TCP_SERVER_NOT_STARTED:
            self.enter_tcp_listening_port.configure(state = NORMAL)
            self.emulator_on.configure(state = NORMAL)
        else:
            self.enter_tcp_listening_port.configure(state = DISABLED)
            self.emulator_on.configure(state = DISABLED)

			
    def log(self, info, severity = LOG_SEVERITY_INFO):
        self.text_details.configure(state = NORMAL)
        self.text_details.insert(END, debug_sprint(info))
        self.text_details.see(END)    
        self.text_details.configure(state = DISABLED)
        # Will use different colors for different severity information
        pass

        
    def load_settings(self):
        self.serial_port_name = str()
        folder = get_current_folder()
        try:
            with open(folder + "/settings.json") as f_settings:
                settings = json.load(f_settings)
                tcp_client_remote_address = None
                tcp_client_remote_port = None
                for key, v in settings.items():
                    if key == "Serial Port":
                        self.serial_port_name = v
                    elif key == "TCP Server Listening Port":
                        listening_port_string = v
                        if listening_port_string.isnumeric():
                            self.tcp_server_listening_port = int(listening_port_string)
                            if self.tcp_server_listening_port < 0 or self.tcp_server_listening_port > 65535:
                                self.tcp_server_listening_port = TCP_SERVER_LISTENING_PORT_DEFAULT
                        else:
                            self.tcp_server_listening_port = TCP_SERVER_LISTENING_PORT_DEFAULT
                    elif key == "TCP Client Remote Address":
                        tcp_client_remote_address = v
                    elif key == "TCP Client Remote Port":
                        tcp_client_remote_port_string = v
                        if tcp_client_remote_port_string.isnumeric():
                            tcp_client_remote_port = int(tcp_client_remote_port_string)
                        else:
                            tcp_client_remote_port = TCP_SERVER_LISTENING_PORT_DEFAULT
                if tcp_client_remote_address != None and tcp_client_remote_port != None:
                    self.tcp_client_remote_address = (tcp_client_remote_address, tcp_client_remote_port) 
                    
        except FileNotFoundError:
            print("The file setting.json is not existed")


    def save_settings(self):
        settings = dict()
        settings["Serial Port"] = self.serial_port_name
        settings["TCP Server Listening Port"] = str(self.tcp_server_listening_port)
        settings["TCP Client Remote Address"] = self.tcp_client_remote_address[0]
        settings["TCP Client Remote Port"] = str(self.tcp_client_remote_address[1])
        
        folder = get_current_folder()

        with open(folder + "/settings.json", 'w') as f_settings:
            json.dump(settings, f_settings)                

        
    def open_serial_port(self, event):
        self.do_open_serial_port()

    
    def open_close_serial_port(self):
        if self.serial_port_state == SERIAL_PORT_NOT_CONNECTED:
            if self.tcp_client_state != TCP_CLIENT_NOT_CONNECTED:
                response = messagebox.askquestion(title='Warning',message = "Need stop the TCP client first, continue?") 
                if response == "no":
                    return
                else:
                    self.start_stop_tcp_client()
			
            enter_serial_port_name(self, False, "Enter Serial Port Name")
            if self.ok_clicked == False:
                return
            else:
                self.ok_clicked = False
                
            try:
                self.serial_port = serial.Serial(self.serial_port_name, 115200)
            except:
                self.log("Can't open " + self.serial_port_name, LOG_SEVERITY_ERROR)
            else:    
                print(self.serial_port)
                if self.serial_port.isOpen():
                    self.log("Open " + self.serial_port_name + " successfully", LOG_SEVERITY_INFO)
                    # Save the port name to the json file
                    self.save_settings()
                    self.serial_port_state = SERIAL_PORT_CONNECTED
                    # Start the serial port Rx thread
                    self.thread_serial_port_rx = threading.Thread(target = self.serial_port_rx)
                    self.thread_serial_port_rx.daemon = True
                    self.thread_serial_port_rx.start()
                else:
                    if self.serial_port_name != None:
                        self.log("Open " + self.serial_port_name + " failed", LOG_SEVERITY_ERROR)
        else:
            self.serial_port_state = SERIAL_PORT_NOT_CONNECTED
        self.update_status_bar_info()
        
        
    def do_open_serial_port(self):
        if self.serial_port_state == SERIAL_PORT_CONNECTED:
            messagebox.showerror(title = "Error!", message = "The serial port is already connected")
            return
        self.open_close_serial_port()    


    def close_serial_port(self, event):
        self.do_close_serial_port()

        
    def do_close_serial_port(self):
        if self.serial_port_state == SERIAL_PORT_NOT_CONNECTED:
            messagebox.showerror(title = "Error!", message = "The serial port is not connected")
            return
        self.open_close_serial_port()
                
                
    def send_command_to_serial_port(self, event):
        if self.tcp_client_state == TCP_CLIENT_CONNECTED:
            data = self.enter_at.get()
            self.log(data, LOG_SEVERITY_COMMAND)
            data = data + "\r" + "\n"
            try:
                # The method encode converting from string to bytes
                self.tcp_client_connection.send(data.encode())
            except:
                self.tcp_client_connection.close()
                self.tcp_client_state = TCP_CLIENT_NOT_CONNECTED
                self.update_status_bar_info()
                self.log("Error: the TCP client connection is closed", LOG_SEVERITY_ERROR)
        elif self.serial_port != None and self.serial_port.isOpen():
            data = self.enter_at.get()
            self.log(data, LOG_SEVERITY_COMMAND)
            data = data + "\r" + "\n"
            # The method encode converting from string to bytes
            self.serial_port.write(data.encode())
        else:
            self.enter_at.configure(state = DISABLED)
            self.log("Both the TCP client connection and the serial port are closed", LOG_SEVERITY_ERROR)

    
    def serial_port_rx(self):
        self.log("The thread serial_port_rx is started", LOG_SEVERITY_INFO)
        print("The thread serial_port_rx is started")
        while self.serial_port_state == SERIAL_PORT_CONNECTED and self.serial_port != None and self.serial_port.isOpen():
            # It looks like the timer is not necessary?
            # If the sleep is not here, the CPU load will be very high
            time.sleep(0.001)
            # If the port is closed at this time, the following call may cause exception
            try:
                data = b''
                count = self.serial_port.inWaiting()
                if count > 0:
                    data = self.serial_port.read(count)
            except:
                self.log("Error: the serial port connection is lost", LOG_SEVERITY_ERROR)
                self.serial_port_state = SERIAL_PORT_NOT_CONNECTED
                break
            else:
                if data != b'':
                    if self.tcp_server_state != TCP_SERVER_CONNECTED:
                        self.text_details.configure(state = NORMAL)
                        # self.text_details.insert(END, data.decode("utf-8"))
                        self.text_details.insert(END, data)
                        self.text_details.see(END)
                        self.text_details.configure(state = DISABLED)
                    else:
                        try:
                            self.tcp_server_connection.send(data)
                        except:
                            # The closure will be handled in the thread tcp_server
                            pass
        self.serial_port.close()
        self.log("Close " + self.serial_port_name + " successfully", LOG_SEVERITY_INFO)
        self.update_status_bar_info()               
        self.log("The thread serial_port_rx is quiting ...", LOG_SEVERITY_INFO)
        print("The thread serial_port_rx is quiting ...")
        # Check if the TCP server is running or not
        if self.tcp_server_state != TCP_SERVER_NOT_STARTED:
            self.log("Warning: The TCP server is still running but the serial port is not connected", LOG_SEVERITY_WARNING)


    
    def tcp_server(self):
        self.log("The thread tcp_server is started", LOG_SEVERITY_INFO)        
        print("The thread tcp_server is started")
        
        tcp_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            tcp_server.bind(("", self.tcp_server_listening_port))
        except:
            self.log("Error: bind failed, the port might be already in use.", LOG_SEVERITY_ERROR)
            tcp_server.close()
            self.log("The thread tcp_server is quiting ...", LOG_SEVERITY_INFO)        
            print("The thread tcp_server is quiting ...")
            self.start_stop_tcp_server()
            return
            
        tcp_server.setblocking(False)
        tcp_server.listen(1)
        self.save_settings()

        # Check if the serial port is connected or not
        if self.serial_port_state == SERIAL_PORT_NOT_CONNECTED:
            self.log("Warning: The TCP server is started but the serial port is not connected", LOG_SEVERITY_WARNING)
        
        r_inputs = [tcp_server, ]

        while self.tcp_server_state != TCP_SERVER_NOT_STARTED:
            r_list, w_list, e_list = select.select(r_inputs, [], [], 1)
            for event in r_list:
                if event == tcp_server:
                    # New connection coming
                    self.tcp_server_connection, self.tcp_server_remote_address = event.accept()
                    r_inputs.append(self.tcp_server_connection)
                    self.tcp_server_state = TCP_SERVER_CONNECTED
                    self.update_status_bar_info()
                    self.log("Connected: " + self.tcp_server_remote_address[0] + ":" + str(self.tcp_server_remote_address[1]), LOG_SEVERITY_INFO)
                elif event == self.tcp_server_connection:
                    try:
                        data = event.recv(1460)
                    except:
                        # Disconnetced from the remote side
                        r_inputs.remove(event)
                        self.tcp_server_state = TCP_SERVER_LISTENING
                        self.update_status_bar_info()                        
                        self.log("The connection is closed by the client", LOG_SEVERITY_INFO)
                    else:
                        if data != b'':
                            # Don't display the data in order to make it faster
                            # Data received
                            # self.text_details.configure(state = NORMAL)
                            # # self.text_details.insert(END, data.decode("utf-8"))
                            # self.text_details.insert(END, data)
                            # self.text_details.see(END)
                            # self.text_details.configure(state = DISABLED)
                            if self.emulator == True:
                                # In emulator mode, the serial agent will parse the AT commands sent from the client and 
                                # respond to the client
                                for k, v in emulator_dict.items():
                                    # Check if we have the key string, if yes, remove the key string and respond the value string to the client
                                    # Using '?‘ to replace the invalid characters
                                    self.receive_from_client += data.decode('utf-8','replace').lower()
                                    index = self.receive_from_client.find(k)
                                    if index != -1:
                                        # Delete the key string from the receive_from_client
                                        self.receive_from_client = self.receive_from_client.replace(k, '')
                                        # Respond the value string back to the client
                                        event.send(v.encode())
                                        # Quit the loop
                                        break
                            elif self.serial_port_state == SERIAL_PORT_CONNECTED and self.serial_port != None and self.serial_port.isOpen():
                                self.serial_port.write(data)
                        else:
                            # Disconnetced from the remote side
                            r_inputs.remove(event)
                            self.tcp_server_state = TCP_SERVER_LISTENING
                            self.update_status_bar_info()                        
                            self.log("The connection is closed by the client", LOG_SEVERITY_INFO)

        if self.tcp_server_connection != None:
            self.tcp_server_connection.close()
        tcp_server.close()        
        self.log("The TCP server is closed successfully", LOG_SEVERITY_INFO)
        self.update_status_bar_info()
        self.log("The thread tcp_server is quiting ...", LOG_SEVERITY_INFO)        
        print("The thread tcp_server is quiting ...")
                        

    def tcp_client(self):

        self.log("The thread tcp_client is started", LOG_SEVERITY_INFO)        
        print("The thread tcp_client is started")
        
        r_inputs = set()
        r_inputs.add(self.tcp_client_connection)
        w_inputs = set()
        w_inputs.add(self.tcp_client_connection)
        e_inputs = set()
        e_inputs.add(self.tcp_client_connection)

        error = False
        while self.tcp_client_state != TCP_CLIENT_NOT_CONNECTED:
            try:
                r_list, w_list, e_list = select.select(r_inputs, w_inputs, e_inputs, 1)
                # read event, the server sent something
                for event in r_list:
                    try:
                        data = event.recv(1024)
                    except Exception as e:
                        print(e)
                    if data and data != b'':
                        self.text_details.configure(state = NORMAL)
                        self.text_details.insert(END, data.decode("utf-8"))
                        self.text_details.see(END)
                        self.text_details.configure(state = DISABLED)
                        data = b''
                    else:
                        self.log("The connection is closed by the server side", LOG_SEVERITY_INFO)
                        r_inputs.clear()
                        error = True
                        break
                if error == True:
                    break
                    
                if len(w_list) > 0:
                    # The write event will be triggered as well once the write buffer is from "full" to "available".
                    # But in our use case, we may not meet such case
                    self.log("Connected: " + self.tcp_client_remote_address[0] + ":" + str(self.tcp_client_remote_address[1]), LOG_SEVERITY_INFO)
                    self.tcp_client_state = TCP_CLIENT_CONNECTED
                    self.update_status_bar_info()
                    w_inputs.clear()                       
                    self.save_settings()
                    
                if len(e_list) > 0:
                    self.log("Connection error", LOG_SEVERITY_ERROR)
                    e_inputs.clear()
                    break
            except OSError as e:
                print(e)        
              
        self.tcp_client_connection.close()
        self.tcp_client_state = TCP_CLIENT_NOT_CONNECTED
        self.log("The TCP client is closed successfully", LOG_SEVERITY_INFO)
        self.update_status_bar_info()
        self.log("The thread tcp_client is quiting ...", LOG_SEVERITY_INFO)        
        print("The thread tcp_client is quiting ...")


def serial_to_socket_main():
    root = Tk()
    root.withdraw()
    serial_agent(root, True, "Serial Agent")
    root.mainloop()    


def main():
    serial_to_socket_main()


if __name__ == '__main__':
    main()
