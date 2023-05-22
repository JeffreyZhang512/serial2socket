# ------------------------------------------------------------------------------
#     Copyright (c) 2023
#     Author: Zhang, Jeffrey <jeffreyzh512@outlook.com>
# ------------------------------------------------------------------------------

from time import *
import sys
import threading
import serial
import time
import socket
import select
import getopt

# Serial port
SERIAL_PORT_NOT_CONNECTED = 0
SERIAL_PORT_CONNECTED = 1

# TCP server
TCP_SERVER_NOT_STARTED = 0
TCP_SERVER_LISTENING = 1
TCP_SERVER_CONNECTED = 2
TCP_SERVER_LISTENING_PORT_DEFAULT = 27025

# Log
LOG_SEVERITY_INFO = 0
LOG_SEVERITY_WARNING = 1
LOG_SEVERITY_ERROR = 2

class serial_agent():

    def log(self, info, severity = LOG_SEVERITY_INFO):
        time_stamp = "[" + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + "] "
        if severity == LOG_SEVERITY_ERROR:
            message = time_stamp + "ERROR   " + info 
        elif severity == LOG_SEVERITY_WARNING:
            message = time_stamp + "WARNING " + info
        else:
            message = time_stamp + "INFO    " + info 
        # Will use different colors for different severity information
        pass
        print(message)


    def __init__(self, serial_port_name, tcp_port_name):
        self.log("Serial Agent v0.2.0.0, press x then enter key to quit", LOG_SEVERITY_INFO)
        self.error = 0
        if serial_port_name == "":
            self.log("Serial port not specified", LOG_SEVERITY_ERROR)
            self.error = 1
            return
            
        if tcp_port_name.isnumeric():
            tcp_port = int(tcp_port_name)
            if tcp_port < 0 or tcp_port > 65535:
                tcp_port = TCP_SERVER_LISTENING_PORT_DEFAULT
                self.log("Use default TCP port 27025", LOG_SEVERITY_INFO)                
        else:
            tcp_port = TCP_SERVER_LISTENING_PORT_DEFAULT
            self.log("Use default TCP port 27025", LOG_SEVERITY_INFO)

        # Serial port
        self.serial_port_state = SERIAL_PORT_NOT_CONNECTED
        self.serial_port_name = serial_port_name
        self.serial_port = None
        # TCP Server
        self.tcp_server_state = TCP_SERVER_NOT_STARTED
        self.tcp_server_listening_port = tcp_port
        self.tcp_server_connection = None
        self.tcp_server_remote_address = None

        self.open_serial_port()
        self.start_tcp_server()
    
    
    def start_tcp_server(self):
        if self.tcp_server_state != TCP_SERVER_NOT_STARTED:
            self.log("The TCP server is already started", LOG_SEVERITY_ERROR)
            return
        self.start_stop_tcp_server()
        
        
    def stop_tcp_server(self):
        if self.tcp_server_state == TCP_SERVER_NOT_STARTED:
            self.log("The TCP server is not started", LOG_SEVERITY_ERROR)
            return
        self.start_stop_tcp_server()
        

    def start_stop_tcp_server(self):
        self.thread_tcp_server = None
        if self.tcp_server_state == TCP_SERVER_NOT_STARTED:
            self.tcp_server_state = TCP_SERVER_LISTENING
            self.thread_tcp_server = threading.Thread(target = self.tcp_server)
            self.thread_tcp_server.daemon = True
            self.thread_tcp_server.start()
        else:
            self.tcp_server_state = TCP_SERVER_NOT_STARTED

        
    def open_serial_port(self):
        if self.serial_port_state == SERIAL_PORT_CONNECTED:
            self.log("The serial port is already connected", LOG_SEVERITY_WARNING)
            return
        self.open_close_serial_port()    


    def close_serial_port(self):
        if self.serial_port_state == SERIAL_PORT_NOT_CONNECTED:
            self.log("The serial port is not connected", LOG_SEVERITY_WARNING)
            return
        self.open_close_serial_port()


    def open_close_serial_port(self):
        self.thread_serial_port_rx = None
        if self.serial_port_state == SERIAL_PORT_NOT_CONNECTED:

            try:
                self.serial_port = serial.Serial(self.serial_port_name, 115200)
            except:
                self.log("Can't open " + self.serial_port_name, LOG_SEVERITY_ERROR)
                return
            else:    
                if self.serial_port.isOpen():
                    self.log("Open " + self.serial_port_name + " successfully", LOG_SEVERITY_INFO)
                    self.serial_port_state = SERIAL_PORT_CONNECTED
                    # Start the serial port Rx thread
                    self.thread_serial_port_rx = threading.Thread(target = self.serial_port_rx)
                    self.thread_serial_port_rx.daemon = True
                    self.thread_serial_port_rx.start()
                else:
                    if self.serial_port_name != None:
                        self.log("Open " + self.serial_port_name + " failed", LOG_SEVERITY_ERROR)
                    return
        else:
            self.serial_port_state = SERIAL_PORT_NOT_CONNECTED

                
    def serial_port_rx(self):
        self.log("The thread serial_port_rx is started", LOG_SEVERITY_INFO)
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
                self.log("The serial port connection is lost", LOG_SEVERITY_ERROR)
                self.serial_port_state = SERIAL_PORT_NOT_CONNECTED
                break
            else:
                if data != b'':
                    if self.tcp_server_state == TCP_SERVER_CONNECTED:
                        try:
                            self.tcp_server_connection.send(data)
                        except:
                            # The closure will be handled in the thread tcp_server
                            pass
        self.serial_port.close()
        self.log("Close " + self.serial_port_name + " successfully", LOG_SEVERITY_INFO)
        self.log("The thread serial_port_rx is quiting ...", LOG_SEVERITY_INFO)

    
    def tcp_server(self):
        self.log("The thread tcp_server is started", LOG_SEVERITY_INFO)        
        
        tcp_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            tcp_server.bind(("", self.tcp_server_listening_port))
        except:
            self.log("bind failed, the port might be already in use.", LOG_SEVERITY_ERROR)
            tcp_server.close()
            self.log("The thread tcp_server is quiting ...", LOG_SEVERITY_INFO)        
            return
            
        tcp_server.setblocking(False)
        tcp_server.listen(1)

        # Check if the serial port is connected or not
        if self.serial_port_state == SERIAL_PORT_NOT_CONNECTED:
            self.log("The TCP server is started but the serial port is not connected", LOG_SEVERITY_WARNING)
        
        r_inputs = [tcp_server, ]

        while self.tcp_server_state != TCP_SERVER_NOT_STARTED:
            r_list, w_list, e_list = select.select(r_inputs, [], [], 1)
            for event in r_list:
                if event == tcp_server:
                    # New connection coming
                    self.tcp_server_connection, self.tcp_server_remote_address = event.accept()
                    r_inputs.append(self.tcp_server_connection)
                    self.tcp_server_state = TCP_SERVER_CONNECTED
                    self.log("Connected: " + self.tcp_server_remote_address[0] + ":" + str(self.tcp_server_remote_address[1]), LOG_SEVERITY_INFO)
                elif event == self.tcp_server_connection:
                    try:
                        data = event.recv(1460)
                    except:
                        # Disconnetced from the remote side
                        r_inputs.remove(event)
                        self.tcp_server_state = TCP_SERVER_LISTENING
                        self.log("The connection is closed by the client", LOG_SEVERITY_INFO)
                    else:
                        if data != b'':
                            # Data received
                            if self.serial_port_state == SERIAL_PORT_CONNECTED and self.serial_port != None and self.serial_port.isOpen():
                                self.serial_port.write(data)
                        else:
                            # Disconnetced from the remote side
                            r_inputs.remove(event)
                            self.tcp_server_state = TCP_SERVER_LISTENING
                            self.log("The connection is closed by the client", LOG_SEVERITY_INFO)

        if self.tcp_server_connection != None:
            self.tcp_server_connection.close()
        self.log("The thread tcp_server is quiting ...", LOG_SEVERITY_INFO)        
                        

def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], "c:p:", ["SerialPort", "TcpPort"])
    except getopt.GetoptError:
        # print help information and exit:
        print("Usage: serial_agent.py [options]")
        print("General Options:")
        print("  -c <Serial Port>")
        print("  -p <TCP Port>")
        return

    serial_port_name = ""
    tcp_port_name = ""
    for o, a in opts:
        if o in ("-c", "--c"):
            serial_port_name = a
        if o in ("-p", "--p"):
            tcp_port_name = a

    serialAgent = serial_agent(serial_port_name, tcp_port_name)
    if serialAgent.error == 1:
        return

    # Wait enter key
    while input().lower() != "x":
        pass
    
    serialAgent.close_serial_port()
    serialAgent.stop_tcp_server()

    if serialAgent.thread_serial_port_rx != None:
        while serialAgent.thread_serial_port_rx.is_alive():
            pass

    if serialAgent.thread_tcp_server != None:
        while serialAgent.thread_tcp_server.is_alive():
            pass

    time.sleep(2)
    serialAgent.log("Closed", LOG_SEVERITY_INFO)


if __name__ == '__main__':
    main()
