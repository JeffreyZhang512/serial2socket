# serial2socket
A python program to covert a serial port to a socket. It is just like the part of the functions of the utility socat on Linux. Since it is a python program, it can be run on different OS. 

## Preconditions
- It is a python3 program. You have to install python3.
- You need also install some addtion python libs via pip, such as pyserial, numpy, Pillow.

## Usage
On the server PC which has the serial port physically:
- Run the command "python serial_agent_main.py". It is GUI program.
- Select the menu item "File | Open Serial Port" and enter the serial port you want to connect.
- Click the play button or select the menu "File | Start TCP Server". The default port number the program listening is 27025.

On the client PC:
- Run your application and open the socket "server_ip_adress:27025" instead of openning the serial port.
- Send the command and you will get the response from the remote serail port just like it is a local serial port. 
