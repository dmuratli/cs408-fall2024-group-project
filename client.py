import socket
import threading
import os
import tkinter as tk
from tkinter import filedialog
import time
import stat

#region Global Variables
#================

name = None
file_directory = None
server_IP = None
server_port = None
client_socket = None
file_name = None
transfer_event = threading.Event()

BUFFER_SIZE = 65536 # 64 KB each packet (CHUNK)

#================
#endregion



#region Functions
#================

def get_IP():  #Getter function to get IP adress from GUI's Server IP entry box 
    global server_IP
    server_IP = (serverIP_entry.get().strip()) #Global Server IP variable assigned from the GUI box
    if not server_IP:
        update_GUI("Server IP must not be empty")  #If the GUI box is empty gives this error
        return False
    return True
    
def get_port(): #Getter function to get port number from GUI's port entry box 
    global server_port
    try: 
        server_port = int(port_entry.get().strip()) #Global server_port variable assigned from the GUI box, if there is an empty char it is eleminated by strip function
    except ValueError:
        update_GUI("Port must be a number") #If port is not a numeric value it gives an error
        return False
    if not server_port:
        update_GUI("Port must not be empty") #If port box is empty from GUI it gives this error
        return False
    return True

def get_name(): #Getter function to get port username from GUI's port entry box 
    global name
    name = name_entry.get() #Global name variable assigned from the GUI box
    if not name:
        update_GUI("Name must not be empty") #If name box is empty it gives this error
        return False
    return True

def get_file_name(): #Getter function to get port filename from GUI's port entry box 
    global file_name
    file_name = file_name_entry.get() # Global finename variable assigned from the GUI box
    if not file_name:
        return False 
    return True

def listen_server(): #The clients listen to the server to get update messages actually it is a thread function
    global client_socket
    while client_socket: #If the connection has not been established the loop does not work
        if not transfer_event.is_set():  #If there is not active download or upload (transfer event) the client always listens to the server
            try:
                client_socket.settimeout(0.1)
                message = client_socket.recv(BUFFER_SIZE).decode() #Buffer size is the chunk size, the message comes from the server
                if message:
                    update_GUI(f"Server: {message}") #All data those come from server other than download data printed in the GUI
                client_socket.settimeout(None)
            except socket.timeout:
                continue
            except:
                break
        else:
            time.sleep(0.1) #To prevent CPU time usage this thread sleep each 100 ms
        
def disable_transfer_buttons(): #all server related buttons disabled during the transfers (download and upload) to prevent thread collisions.
    download_button.config(state="disabled")
    upload_button.config(state="disabled")
    delete_button.config(state="disabled")
    list_files_button.config(state="disabled")
    file_name_entry.config(state="disabled")

def enable_transfer_buttons():  #To activate re-activate the server related buttons 
    download_button.config(state="normal")
    upload_button.config(state="normal")
    delete_button.config(state="normal")
    list_files_button.config(state="normal")
    file_name_entry.config(state="normal")

def connect(): #The function to establish connection between client and server
    if check_connection():
        update_GUI("Connection has been already set, please disconnect and connect again") #The the connection has already been established it gives this message
    else:
        global client_socket
        try: 
            if not get_IP(): #If IP is null is returns
                return
            if not get_port(): #If port number is null is returns
                return
            if not get_name(): #If user name number is null is returns
                return
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #TCP connection has been established as client_socket
            client_socket.connect((server_IP, server_port)) #Server's IP and Port number is given to the TCP connectiion
            update_GUI(f"Connecting to {server_IP}:{server_port}") #Server's IP and Port number printed out in the GUI
            
            name_prompt = client_socket.recv(BUFFER_SIZE).decode() #If the server asks for USERNAME...
            if name_prompt == "USERNAME: ":
                client_socket.send(name.encode()) #...Client sends the username to the server
                response = client_socket.recv(BUFFER_SIZE).decode() #Server sends an response about the username
            
                if response.startswith("Error"): #If the server sends an error 
                    client_socket.close() #Connection aborted
                    client_socket = None
                    update_GUI(response)
                else:
                    update_GUI(f"Successfully connected to server!") #Otherwise successful connection message appeared in the GUO
                    threading.Thread(target=listen_server, daemon=True).start() #Listening thread has been initiliazed

        except ConnectionRefusedError:
            update_GUI("Connection refused. Make sure server is running.") #If the connection refused (probably server is not running)
            if client_socket:
                client_socket.close()
                client_socket = None
            
        except Exception as e: #Other server connection errors
            update_GUI(f"Connection error: {str(e)}")
            if client_socket:
                client_socket.close()
                client_socket = None

def disconnect(): #Discconect function to reset all connection. It also resets all global variables to their NULL values 
    global name
    global file_directory 
    global server_IP
    global server_port
    global client_socket
    global file_name
    if client_socket:
        try:
            client_socket.send("DISCONNECT".encode()) #TCP connection ended
            client_socket.close()
        except Exception as e:
            update_GUI(f"Disconnect error: {str(e)}")
        finally:
            name = None
            file_directory = None  #Attention: If a user disconnects selected directory has been reset. So a new connected user must declare its own path
            server_IP = None
            server_port = None
            client_socket = None
            file_name = None
            update_GUI("Disconnected from server")

def list_files(): #List files function to list all files in the server. Actually is reads the Metadat in the server and it prints out in the Client's GUI
    if check_connection():
        try:
            client_socket.send("LIST".encode())
        except Exception as e:
            update_GUI(f"List files error: {str(e)}")
    else:
        update_GUI("Please connect to the server first") #If there is active connection it gives this error

def download_file(filename): #The thread function to download files from server. In my perspective it is the complex function in this project due to multithreading
    try:
        disable_transfer_buttons()
        transfer_event.set() #The listening events (threads) blocked since the server sends the file data
        time.sleep(0.1)  # 100 ms wait before download
        client_socket.send(f"DOWNLOAD {filename}".encode())
        save_filename = filename.split("|")[-1] if "|" in filename else filename #If an user wants to download other users file, the file name must include a pipe (|)
        file_path = os.path.join(file_directory, save_filename)
        update_GUI("Downloading...")
        complete_data = []
    
        while True: #The transfer loop. Data recieved as chunks during the while loop
            data = client_socket.recv(BUFFER_SIZE).decode()

            if "Error:" in data: #If there is an error during the transfer. It aborts
                update_GUI(data)
                return
                
            if "\nDownloaded" in data: #If the download process succesfully finished, server sends the downloaded signal and loop breaks
                final_part = data.split("\nDownloaded")[0]
                if final_part:
                    complete_data.append(final_part)
                break
                
            complete_data.append(data) 

        with open(file_path, 'w', encoding="ascii") as file: #The data is writing to the file to local path
            file.write(''.join(complete_data))

        os.chmod(file_path, stat.S_IWRITE | stat.S_IREAD)

        update_GUI(f"Successfully downloaded {save_filename}")
    except Exception as e:
        update_GUI(f"Download error: {str(e)}")
        if os.path.exists(file_path):
            os.remove(file_path)
    finally:
        transfer_event.clear() #Listening thread can continue to work
        enable_transfer_buttons() #enable download and other transfer related buttons again

def download(): #Download function. It runs when the user clicks the download button from the GUI. It runs the download_file thread function to initiliaze download
    global file_name
    if check_connection(): #The connection and file name etc controlled. If there is an error it print in the GUI
        if file_directory:
            get_file_name()
            if file_name:
                if "|" not in file_name: #If there is no pipe in the file_name it means the user tries to access his/her own file
                    file_name = f"{name}|{file_name}"
                threading.Thread(target=download_file, args=(file_name,)).start()
            else:
                update_GUI("File name must not be empty")      
        else:
            update_GUI("Please select a directory to download first")    
    else:
        update_GUI("Please connect to the server first")


def upload_file(filename): #The thread function to upload files from client to the server
    try:
        disable_transfer_buttons() #During the process all server related buttons are disabled to prevent thread collision
        transfer_event.set() #The listening thread is disabled
        time.sleep(0.1)
        client_socket.send(f"UPLOAD {os.path.basename(filename)}".encode()) #Upload started signal sent to the server
        with open(filename, 'r', encoding="ascii") as file:
            content = file.read()
        update_GUI("Uploading...")

        for i in range(0, len(content), BUFFER_SIZE): #The main algorithm to handle conflicts
            chunk = content[i:i+BUFFER_SIZE]   #The data are send as chunks of BUFFER_SIZE
            client_socket.send(chunk.encode()) #The thread waits a little of time between each chunk to prevent conflicts
            time.sleep(0.001)                  #1 ms waits between each chunk
            
        time.sleep(0.1)                       #100 ms wait before sending upload_complete signal
        client_socket.send("UPLOAD_COMPLETE".encode())

        response = client_socket.recv(BUFFER_SIZE).decode()
        update_GUI(response)

    except Exception as e:
        update_GUI(f"Upload error: {e}")
    finally:
        transfer_event.clear() #The listening thread is enabled
        enable_transfer_buttons() #The buttons are re-enabled

def upload(): #Upload function. It runs when the user clicks the upload button from the GUI. It runs the upload_file thread function to initiliaze download
    if check_connection():
        filename = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")]) #only txt files are allowed as the document says
        if filename:
            threading.Thread(target=upload_file, args=(filename,)).start()
    else:
        update_GUI("Please connect to the server first") #If there is no connection is gives this error

def delete(): #Delete function to delete files in the server. Clients sends a Delete request with this function. It activates the user click delete button in the GUI
    global file_name
    if check_connection(): #If there is no connection the error message is printed
        get_file_name()
        if file_name:
            try:
                if "|" not in file_name: #There is pipe or not the function runs in both ways
                    delete_command = f"DELETE {name}|{file_name}"
                else:
                    delete_command = f"DELETE {file_name}"
                client_socket.send(delete_command.encode())
            except Exception as e:
                update_GUI(f"Delete error: {str(e)}")
        else:
            update_GUI("File name must not be empty")
    else:
        update_GUI("Please connect to the server first")

def check_connection(): #Boolean function to check there is connection or not
    if client_socket is None:
        return False
    return True

def select_directory(): #The file directory can be selected from the OS GUI thanks to this function
    global file_directory
    file_directory = filedialog.askdirectory()
    update_GUI(f"Files will be downloaded to: {file_directory}")

def update_GUI(message): #The message parameter prints out in the GUI. Actually it is a print function for the GUI
    log_listbox.insert(tk.END, message)
    log_listbox.yview(tk.END)

#================
#endregion



#region GUI
#================

app = tk.Tk()
app.title("Cloud File SUtorage and Publishing")

app.columnconfigure(1, weight=1)
app.columnconfigure(3, weight=1)

app.rowconfigure(6, weight=1) #log box's row has been configured

#ServerIP entry
tk.Label(app, text="Server IP:").grid(row=0, column=0, padx=5, pady=5, sticky="E")
serverIP_entry = tk.Entry(app)
serverIP_entry.grid(row=0, column=1, padx=5, pady=5, sticky="EW")

#Port entry
tk.Label(app, text="Port:").grid(row=0, column=2, padx=5, pady=5, sticky="E")
port_entry = tk.Entry(app)
port_entry.grid(row=0, column=3, padx=5, pady=5, sticky="EW")

#Name entry
tk.Label(app, text="Name:").grid(row=1, column=0, padx=5, pady=5, sticky="E")
name_entry = tk.Entry(app)
name_entry.grid(row=1, column=1, padx=5, pady=5, columnspan=3, sticky="EW")

#Delete entry
tk.Label(app, text="File Name:").grid(row=2, column=0, padx=5, pady=5, sticky="E")
file_name_entry = tk.Entry(app)
file_name_entry.grid(row=2, column=1, padx=5, pady=5, columnspan=3, sticky="EW")

#Connect button
connect_button = tk.Button(app, text= "Connect", command = connect)
connect_button.grid(row=3, column=0, columnspan= 2, padx=5, pady =5, sticky="EW")

#Disconnect button 
disconnect_button = tk.Button(app, text= "Disconnect", command = disconnect)
disconnect_button.grid(row=3, column=2, columnspan= 2, padx=5, pady =5, sticky="EW")

#List files button
list_files_button = tk.Button(app, text="List Files", command= list_files)
list_files_button.grid(row=4, column=0, columnspan=2, padx=5, pady=5, sticky="EW")

#Select directory button to download there (a.k.a. browser button)
select_directory_button = tk.Button(app, text="Select Directory", command=select_directory)
select_directory_button.grid(row=4, column=2, columnspan=2, padx=5, pady=5, sticky="EW")


#row 4 has been split into 3 parts to fit download, upload and delete buttons
button_frame = tk.Frame(app)
button_frame.grid(row=5, column=0, columnspan=4, sticky="EW")

button_frame.columnconfigure(0, weight=1)
button_frame.columnconfigure(1, weight=1)
button_frame.columnconfigure(2, weight=1)

#download button
download_button = tk.Button(button_frame, text="Download", command=download)
download_button.grid(row=0, column=0, padx=5, pady=5, sticky="EW")

#upload button
upload_button = tk.Button(button_frame, text="Upload", command=upload)
upload_button.grid(row=0, column=1, padx=5, pady=5, sticky="EW")

#delete button
delete_button = tk.Button(button_frame, text="Delete", command=delete, fg="red")
delete_button.grid(row=0, column=2, padx=5, pady=5, sticky="EW")

#Log box
log_listbox = tk.Listbox(app, width=50, height=15)
log_listbox.grid(row=6, column=0, columnspan=4, padx=5, pady=5, sticky="NSEW")

app.mainloop()

#================
# endregion