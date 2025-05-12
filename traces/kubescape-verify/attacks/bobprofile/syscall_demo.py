import os
import socket
import time
import platform

def file_operations():
    """Perform basic file operations."""
    with open("test_file.txt", "w") as f:
        f.write("This is a test file.\n")
    with open("test_file.txt", "r") as f:
        print(f.read())
    os.remove("test_file.txt")

def network_operations():
    """Perform basic network operations."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(("example.com", 80))
        s.sendall(b"GET / HTTP/1.1\r\nHost: example.com\r\n\r\n")
        response = s.recv(1024)
        print("Received response:", response.decode("utf-8", errors="ignore"))
        s.close()
    except Exception as e:
        print("Network operation failed:", e)

def process_operations():
    """Perform basic process management."""
    pid = os.fork()
    if pid == 0:
        print("Child process: PID =", os.getpid())
        os._exit(0)
    else:
        print("Parent process: PID =", os.getpid())
        os.wait()

def main():
    print("Running on:", platform.system(), platform.release(), platform.machine())
    print("Performing file operations...")
    file_operations()
    print("Performing network operations...")
    network_operations()
    print("Performing process operations...")
    process_operations()
    print("Demo complete.")

if __name__ == "__main__":
    main()