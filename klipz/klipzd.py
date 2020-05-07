import argparse, pkg_resources, sys, time
import threading, _thread
import socketserver

connections = []

def command_line_arguments():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", "-v",
        help="Print version number and exit.",
        action="store_true")
    ap.add_argument("--address", "-a",
        help="Address the server listens on. Defaults to all addresses.",
        default="0.0.0.0")
    ap.add_argument("--port", "-p",
        type=int,
        help="Port the server listens on. Defaults to 54321.",
        default=54321)
    return ap

def run_with_timeout(timeout, default, f, *args, **kwargs):
    if not timeout:
        return f(*args, **kwargs)
    try:
        timeout_timer = threading.Timer(timeout, _thread.interrupt_main)
        timeout_timer.start()
        result = f(*args, **kwargs)
        return result
    except KeyboardInterrupt:
        return default
    finally:
        timeout_timer.cancel()

class ThreadedTCPRequestHandler(socketserver.StreamRequestHandler):

    def handle(self):
        global connections
        my_token = self.rfile.readline().strip()
        connections.append((self, my_token))
        while True:
            data =  run_with_timeout(10, b'', self.rfile.readline().strip)
            if data == b'':
                connections.remove((self, my_token))
                break
            print (self.client_address, data)
            for (it, its_token) in connections:
                if my_token == its_token and it != self:
                    it.wfile.write(data + "\n".encode("ASCII"))

class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass

def main():
    global connections
    ap = command_line_arguments()
    cmdline = ap.parse_args()

    if cmdline.version:
        print(pkg_resources.get_distribution("klipz").version)
        sys.exit(0)

    server = ThreadedTCPServer((cmdline.address, cmdline.port), ThreadedTCPRequestHandler)
    with server:
        ip, port = server.server_address
        print(ip, port)

        # Start a thread with the server -- that thread will then start one
        # more thread for each request
        server_thread = threading.Thread(target=server.serve_forever)
        # Exit the server thread when the main thread terminates
        server_thread.daemon = True
        server_thread.start()
        print("Server loop running in thread:", server_thread.name)
        try:
            while True:
                time.sleep(5)
                print (connections)
        except:
            server.shutdown()

if __name__ == "__main__":
    main()
