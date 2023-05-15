# serial2socket
A python program to covert a serial port to a TCP socket. It is just like the part of the functions of the utility socat on Linux. Since it is a python program, it can be run on different OS. 

## Preconditions
- It is a python3 program. You have to install python3.
- You need also install some addtion python libs via pip, such as pyserial, numpy, pillow.

## Usage
On the server PC which has the serial port physically:
- Run the command `python serial_agent_main.py`. It is GUI program.
- Select the menu item `File | Open Serial Port` and enter the serial port you want to connect.
- Click the play button or select the menu item `File | Start TCP Server`. The default port number the program listening is 27025.  
or  
- Run the command `python serial_agent.py -c <serial port> -p <tcp port>`. It is command line program.  
  For example:  
  C:\Developments\serial2socket>python serial_agent.py -c COM12 -p 27025  
  [2023-05-11 15:59:06] INFO    Serial Agent v1.0.0, press x then enter key to quit  
  [2023-05-11 15:59:06] INFO    Open COM12 successfully  
  [2023-05-11 15:59:06] INFO    The thread serial_port_rx is started  
  [2023-05-11 15:59:06] INFO    The thread tcp_server is started  
  [2023-05-11 15:59:23] INFO    Connected: 127.0.0.1:54558  
  x  
  [2023-05-11 15:59:51] INFO    Close COM12 successfully  
  [2023-05-11 15:59:51] INFO    The thread serial_port_rx is quiting ...  
  [2023-05-11 15:59:51] INFO    The thread tcp_server is quiting ...  
  [2023-05-11 15:59:53] INFO    Closed  

On the client PC:
- Run your application and open the socket `server_ip_adress:27025` instead of openning the serial port.
- Send the command and you will get the response from the remote serail port just like it is a local serial port. 
