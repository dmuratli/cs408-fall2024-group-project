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

BUFFER_SIZE = 10485760 # 10 MB

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
    while client_socket:
        if not transfer_event.is_set():
            try:
                client_socket.settimeout(0.1)
                message = client_socket.recv(BUFFER_SIZE).decode()
                if message:
                    update_GUI(f"Server: {message}")
                client_socket.settimeout(None)
            except socket.timeout:
                continue
            except:
                break
        else:
            time.sleep(0.1)
        
def disable_transfer_buttons():
    download_button.config(state="disabled")
    upload_button.config(state="disabled")
    delete_button.config(state="disabled")
    list_files_button.config(state="disabled")
    file_name_entry.config(state="disabled")

def enable_transfer_buttons():
    download_button.config(state="normal")
    upload_button.config(state="normal")
    delete_button.config(state="normal")
    list_files_button.config(state="normal")
    file_name_entry.config(state="normal")

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
            
            name_prompt = client_socket.recv(BUFFER_SIZE).decode()
            if name_prompt == "USERNAME: ":
                client_socket.send(name.encode())
                response = client_socket.recv(BUFFER_SIZE).decode()
            
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

def download_file(filename):
    try:
        disable_transfer_buttons()
        transfer_event.set()
        time.sleep(0.1)  # 100 ms wait before download
        client_socket.send(f"DOWNLOAD {filename}".encode())
        save_filename = filename.split("|")[-1] if "|" in filename else filename
        file_path = os.path.join(file_directory, save_filename)
        update_GUI("Downloading...")
        complete_data = []
    
        while True:
            data = client_socket.recv(BUFFER_SIZE).decode()

            if "Error:" in data:
                update_GUI(data)
                return
                
            if "\nDownloaded" in data:
                final_part = data.split("\nDownloaded")[0]
                if final_part:
                    complete_data.append(final_part)
                break
                
            complete_data.append(data)

        with open(file_path, 'w', encoding="ascii") as file:
            file.write(''.join(complete_data))

        os.chmod(file_path, stat.S_IWRITE | stat.S_IREAD)

        update_GUI(f"Successfully downloaded {save_filename}")
    except Exception as e:
        update_GUI(f"Download error: {str(e)}")
        if os.path.exists(file_path):
            os.remove(file_path)
    finally:
        transfer_event.clear()
        enable_transfer_buttons()

def download():
    global file_name
    if check_connection():
        if file_directory:
            get_file_name()
            if file_name:
                if "|" not in file_name:
                    file_name = f"{name}|{file_name}"
                threading.Thread(target=download_file, args=(file_name,)).start()
            else:
                update_GUI("File name must not be empty")      
        else:
            update_GUI("Please select a directory to download first")    
    else:
        update_GUI("Please connect to the server first")


def upload_file(filename):
    try:
        disable_transfer_buttons() 
        transfer_event.set() 
        time.sleep(0.1)
        client_socket.send(f"UPLOAD {os.path.basename(filename)}".encode())
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
        transfer_event.clear()
        enable_transfer_buttons()

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
                if "|" not in file_name:
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