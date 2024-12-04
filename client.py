import socket
import threading
import os
import tkinter as tk
from tkinter import filedialog
import time

#region Global Variables
#================

name = None
file_directory = None
server_IP = None
server_port = None
client_socket = None
file_name = None
is_downloading = False

#================
#endregion

def get_IP():
    global server_IP
    server_IP = (serverIP_entry.get().strip())
    if not server_IP:
        update_GUI("Server IP must not be empty")
        return False
    return True
    
def get_port():
    global server_port
    try: 
        server_port = int(port_entry.get().strip())
    except ValueError:
        update_GUI("Port must be a number")
        return False
    if not server_port:
        update_GUI("Port must not be empty")
        return False
    return True

def get_name():
    global name
    name = name_entry.get()
    if not name:
        update_GUI("Name must not be empty")
        return False
    return True

def get_file_name():
    global file_name
    file_name = file_name_entry.get()
    if not file_name:
        return False
    return True

def listen_server():
    global client_socket
    global is_downloading
    while client_socket:
        if (is_downloading != True):
            try:
                message = client_socket.recv(1024).decode()
                if message:
                    update_GUI(f"Server: {message}")
                else:
                    pass
            except:
                break
        else:
            time.sleep(0.1) # 100 ms waits
        time.sleep(0.001)  # 1 ms wait between listening
        


def connect():
    if check_connection():
        update_GUI("Connection has been already set, please disconnect and connect again")
    else:
        global client_socket
        try: 
            if not get_IP():
                return
            if not get_port():
                return
            if not get_name():
                return
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((server_IP, server_port))
            update_GUI(f"Connecting to {server_IP}:{server_port}")
            
            name_prompt = client_socket.recv(1024).decode()
            if name_prompt == "USERNAME: ":
                client_socket.send(name.encode())
                response = client_socket.recv(1024).decode()
            
                if response.startswith("Error"):
                    client_socket.close()
                    client_socket = None
                    update_GUI(response)
                else:
                    update_GUI(f"Successfully connected to server!")
                    threading.Thread(target=listen_server, daemon=True).start()

        except ConnectionRefusedError:
            update_GUI("Connection refused. Make sure server is running.")
            if client_socket:
                client_socket.close()
                client_socket = None
            
        except Exception as e:
            update_GUI(f"Connection error: {str(e)}")
            if client_socket:
                client_socket.close()
                client_socket = None

def disconnect():
    global name
    global file_directory
    global server_IP
    global server_port
    global client_socket
    global file_name
    if client_socket:
        try:
            client_socket.send("DISCONNECT".encode())
            client_socket.close()
        except Exception as e:
            update_GUI(f"Disconnect error: {str(e)}")
        finally:
            name = None
            file_directory = None
            server_IP = None
            server_port = None
            client_socket = None
            file_name = None
            update_GUI("Disconnected from server")

def list_files():
    if check_connection():
        try:
            client_socket.send("LIST".encode())
        except Exception as e:
            update_GUI(f"List files error: {str(e)}")
    else:
        update_GUI("Please connect to the server first")

def parse_file_info(file_entry):
    parts = file_entry.split("|")
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    return None, None


def download_file(filename): 
    global is_downloading
    try:
        parts = filename.split("|")
        if len(parts) == 2:
            owner, pure_filename = parts[0].strip(), parts[1].strip()
        else:
            pure_filename = filename
            owner = name 

        if owner != name:
            request_filename = f"{owner}|{pure_filename}"
        else:
            request_filename = pure_filename
            
        client_socket.send(f"DOWNLOAD {request_filename}".encode())
        file_path = os.path.join(file_directory, pure_filename)
        update_GUI("Downloading...")
        is_downloading = True
        time.sleep(1) 
        downloaded_data = []

        while True:
            data = client_socket.recv(1024).decode()
            
            if "Error:" in data:
                update_GUI(data)
                is_downloading = False
                return
                
            if "\nDownloaded" in data:
                data = data.split("\nDownloaded")[0]
                if data:
                    downloaded_data.append(data)
                break
            
            downloaded_data.append(data)
            time.sleep(0.01) 
        
        with open(file_path, 'w', encoding="ascii") as file:
            file.write(''.join(downloaded_data))
        update_GUI(f"Successfully downloaded {pure_filename}")
    except Exception as e:
        update_GUI(f"Download error: {str(e)}")
        if os.path.exists(file_path):
            os.remove(file_path)
    finally:
        is_downloading = False

def download():
    global file_name
    if check_connection():
        if file_directory:
            get_file_name()
            if file_name:
                threading.Thread(target=download_file, args=(file_name,)).start()
            else:
                update_GUI("File name must not be empty")      
        else:
            update_GUI("Please select a directory to download first")    
    else:
        update_GUI("Please connect to the server first")


def upload_file(filename): #thread function for uploading
    try:
        client_socket.send(f"UPLOAD {os.path.basename(filename)}".encode())
        with open(filename, 'r', encoding="ascii") as file:
            content = file.read()
            update_GUI("Uploading...")
            for i in range(0, len(content), 1024): #The main algorithm to handle conflicts
                chunk = content[i:i+1024]          #The data are send as chunks 1kB (1kilo = 1024 (binary kilo))
                client_socket.send(chunk.encode()) #The thread waits a little of time between each chunk to prevent conflicts
                time.sleep(0.01) #10 ms waits between each chunk
        time.sleep(1) #1 second wait before sending upload_complete signal
        client_socket.send("UPLOAD_COMPLETE".encode()) 
    except Exception as e:
        update_GUI(f"Upload error: {e}")

def upload():
    if check_connection():
        filename = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")]) #only txt files are allowed as the document says
        if filename:
            threading.Thread(target=upload_file, args=(filename,)).start()
    else:
        update_GUI("Please connect to the server first")

def delete():
    global file_name
    if check_connection():
        get_file_name()
        if file_name:
            try:
                delete_command = f"DELETE {name}|{file_name}"
                client_socket.send(delete_command.encode())
            except Exception as e:
                update_GUI(f"Delete error: {str(e)}")
        else:
            update_GUI("File name must not be empty")
    else:
        update_GUI("Please connect to the server first")

def check_connection():
    if client_socket is None:
        return False
    return True

def select_directory():
    global file_directory
    file_directory = filedialog.askdirectory()
    update_GUI(f"Files will be downloaded to: {file_directory}")

def update_GUI(message):
    log_listbox.insert(tk.END, message)
    log_listbox.yview(tk.END)


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