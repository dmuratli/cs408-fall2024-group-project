import socket
import threading
import os
import tkinter as tk
from tkinter import filedialog

# Global variables
server_socket = None
clients = {} # Connected clients
file_directory = None
metadata_file = "server_metadata.txt"
BUFFER_SIZE = 10485760 # 10 MB

def check_metadata():
    if file_directory != None:
        metadata_path = os.path.join(file_directory, metadata_file)
        if not os.path.exists(metadata_path):
            with open(metadata_path, "w") as f:
                pass  # Create an empty file if the metadata file does not exist
        else:
            pass
    else:
        pass

def upload(client_socket, client_name, file_name):
    try:
        check_metadata()
        file_path = os.path.join(file_directory, f"{client_name}|{file_name}") # Create a file path for the uploaded file in the server

        if os.path.exists(file_path): # Check if the file already exists; remove it if it does to overwrite it
            delete(client_socket, client_name, f"{client_name}|{file_name}")
        else:
            pass

        with open(file_path, "w") as f: # Create the file in the server
            while True:
                data = client_socket.recv(BUFFER_SIZE).decode()

                if data.strip() == "UPLOAD_COMPLETE": # Break the loop if the client has finished uploading the file
                    break
                else:
                    pass

                f.write(data) # Write the data to the file

            metadata_path = os.path.join(file_directory, metadata_file)
            with open(metadata_path, "a") as f:
                f.write(f"{client_name}|{file_name}\n")

            client_socket.send(f"{file_name} uploaded successfully!".encode()) # Send a success message to the client
            update_gui(f"{file_name} uploaded by {client_name}.")
    except Exception as e:
        client_socket.send(f"Error: {e}".encode())
        update_gui(f"{client_name} got the error \"{e}\" during an upload attempt.")

def download(client_socket, client_name, file_name):
    try:
        check_metadata()
        file_path = os.path.join(file_directory, f"{file_name}")

        if os.path.exists(file_path): # Check if the file exists
            with open(file_path, "r") as f:
                for line in f:
                    client_socket.send(line.encode())

            client_socket.send(f"\nDownloaded {file_name}.".encode())
            update_gui(f"{file_name} downloaded by {client_name}.")
        else:
            client_socket.send(f"Error: {file_name} does not exist.".encode())
            update_gui(f"{file_name} does not exist -- download failed.")
    except Exception as e:
        client_socket.send(f"Error: {e}".encode())
        update_gui(f"{client_name} got the error \"{e}\" during a download attempt.")

def delete(client_socket, client_name, file_name):
    try:
        owner, file = file_name.split("|")

        if owner == client_name: # Check if the client is the owner of the file
            file_path = os.path.join(file_directory, f"{file_name}")

            if os.path.exists(file_path): # Check if the file exists
                os.remove(file_path)
                
                metadata_path = os.path.join(file_directory, metadata_file)
                with open(metadata_path, "r") as f:
                    lines = f.readlines()

                with open(metadata_path, "w") as f:
                    for line in lines:
                        if line.strip() != file_name:
                            f.write(line)

                client_socket.send(f"{file_name} deleted successfully!".encode())
                update_gui(f"{file_name} deleted by {client_name}.")
            else:
                client_socket.send(f"Error: {file_name} does not exist.".encode())
                update_gui(f"{file_name} does not exist -- deletion failed.")
        else:
            client_socket.send("Error: You do not have permission to delete this file.".encode())
            update_gui(f"{client_name} attempted to delete a file they do not own.")
    except Exception as e:
        client_socket.send(f"Error: {e}".encode())
        update_gui(f"{client_name} got the error \"{e}\" while attempting to delete a file.")

def list(client_socket, client_name):
    try:
        check_metadata()
        metadata_path = os.path.join(file_directory, metadata_file)

        with open(metadata_path, "r") as f: # Parse the file list
            file_list = []

            for line in f:
                file_list.append(line.strip())

        if file_list != []: # Display the list if there are files on the server
            response = "Files on the server: " + ", ".join(file_list)
        else:
            response = "There are no files on the server."

        client_socket.send(response.encode())
        update_gui(f"{client_name} requested the file list.")
    except Exception as e:
        client_socket.send(f"Error: {e}".encode())
        update_gui(f"{client_name} got the error \"{e}\" during a list request.")

def handle_client(client_socket, client_address):
    client_name = None

    try:
        client_socket.send("USERNAME: ".encode())
        client_name = client_socket.recv(BUFFER_SIZE).decode().strip() # Receive the client name

        if client_name in clients: # Ensure that the client name is unique
            client_socket.send("Error: Username already exists!".encode())
            client_socket.close()

            return
        else:
            client_socket.send("OK".encode()) #Added by Emir otherwise the client keep waiting a response from server

        clients[client_name] = client_socket # Add the client to the dictionary
        update_gui(f"{client_name} has connected.")

        while True: # Take client commands
            # Possible commands:
            # UPLOAD <file_name>
            # DOWNLOAD <file_name>
            # DELETE <file_name>
            # LIST
            # DISCONNECT

            command = client_socket.recv(BUFFER_SIZE).decode().strip()
            command_elts = command.split(" ")

            if command.startswith("UPLOAD") or command.startswith("DOWNLOAD") or command.startswith("DELETE"):
                try:
                    file_name = command_elts[1]
                except:
                    client_socket.send("Error: Invalid command!".encode())
                    continue

                if command.startswith("UPLOAD"):
                    upload(client_socket, client_name, file_name)
                elif command.startswith("DOWNLOAD"):
                    download(client_socket, client_name, file_name)
                elif command.startswith("DELETE"):
                    delete(client_socket, client_name, file_name)
                else:
                    pass
            elif command.startswith("LIST") or command.startswith("DISCONNECT"):
                if command.startswith("LIST"):
                    list(client_socket, client_name)
                elif command.startswith("DISCONNECT"):
                    break
                else:
                    pass
            else:
                pass
    except Exception as e:
        update_gui(f"Error: {e}")
    finally:
        if client_name in clients: # Remove the client from the dictionary when they disconnect
            del clients[client_name]
            client_socket.close()
            update_gui(f"{client_name} has disconnected.")
        else:
            pass

def start_server():
    global server_socket, file_directory
    
    try:
        port = int(port_entry.get()) # Get the port number from the entry box

        if file_directory == None:
            update_gui("Error: Please select a directory.")
            return
        else:
            pass

        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # Create a server socket
        server_socket.bind(("", port)) # Bind the server socket to the port
        server_socket.listen(50) # Listen for up to 50 connections (arbitrary)
        update_gui(f"Server started on port {port}.")

        def accept_clients():
            while True:
                client_socket, client_address = server_socket.accept()
                client_thread = threading.Thread(target=handle_client, args=(client_socket, client_address))
                client_thread.daemon = True
                client_thread.start()

        
        accept_clients_thread = threading.Thread(target=accept_clients) # Accept clients
        accept_clients_thread.daemon = True
        accept_clients_thread.start()
    except Exception as e:
        update_gui(f"Error: {e}")

def stop_server():
    global server_socket

    if server_socket != None: # Close the server socket
        server_socket.close()
        server_socket = None
        update_gui("Server stopped.")

def select_directory():
    global file_directory
    
    file_directory = filedialog.askdirectory()
    update_gui(f"File directory set to: {file_directory}")

def update_gui(message):
    log_listbox.insert(tk.END, message)
    log_listbox.yview(tk.END)

# GUI
app = tk.Tk()
app.title("Cloud File SUtorage and Publishing")

app.rowconfigure(3, weight=1)
app.columnconfigure(1, weight=1)

tk.Label(app, text="Port:").grid(row=0, column=0, padx=5, pady=5, sticky="W")
port_entry = tk.Entry(app)
port_entry.grid(row=0, column=1, padx=5, pady=5, sticky="EW")

tk.Button(app, text="Select Directory", command=select_directory).grid(row=1, column=0, columnspan=2, pady=5, sticky="EW")
tk.Button(app, text="Start Server", command=start_server).grid(row=2, column=0, pady=5, sticky="EW")
tk.Button(app, text="Stop Server", command=stop_server).grid(row=2, column=1, pady=5, sticky="EW")

log_listbox = tk.Listbox(app, width=50, height=15)
log_listbox.grid(row=3, column=0, columnspan=2, padx=5, pady=5, sticky="NSEW")

app.mainloop()