import re
import select
import socket
from urllib.parse import urlparse


class ProxyServer:
    BUFFER_SIZE = 4096

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.bandwidth_usage_bytes = 0
        self.site_visits = dict[str, int]()

    def start(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            server_socket.bind((self.host, self.port))
            server_socket.listen()
            print(
                f"Proxy server started, listening for connections on {self.host}:{self.port}..."
            )

            while True:
                client_socket, client_address = server_socket.accept()
                self._handle_client(client_socket)
        except KeyboardInterrupt:
            print("Proxy server stopped.")
        finally:
            server_socket.close()
            self.print_metrics()

    def print_metrics(self):
        top_sites = sorted(
            [{"url": key, "visits": value} for key, value in self.site_visits.items()],
            key=lambda s: s["visits"],
            reverse=True,
        )

        print(
            {
                "bandwidth_usage": f"{self.bandwidth_usage_bytes / 1024 / 1024}MB",
                "top_sites": top_sites[:10],
            }
        )

    def _handle_client(self, client_socket: socket.socket):
        # Read some initial amount from the client socket.
        request = client_socket.recv(self.BUFFER_SIZE).decode()

        # Get the method and URL from the first line of data.
        lines = request.splitlines()
        parts = lines[0].split()
        method, url, _ = parts

        print(url)
        parse_result = urlparse(url)
        print(parse_result)
        if method == "CONNECT":
            # For HTTPs CONNECT requests, we get a string of the form www.google.com:443
            host, port = url.split(":")
            is_https = True
        else:
            # For HTTP requests, we get either a string starting with / for local paths or
            # a string of the form http://www.google.com/ for remote ones.
            if url.startswith("http://"):
                match = re.match(r"http://(.+)/?", url)
                host = match.group(1)
            elif url == "/metrics":
                self.print_metrics()
            port = 80
            is_https = False

        # Connect to the remote server.
        remote_socket = socket.create_connection((host, int(port)))

        if is_https:
            # For HTTPs, send the connection established message.
            client_socket.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")
        else:
            # For HTTP, send the initially parsed portion of the request.
            remote_socket.sendall(request.encode())

        # Forward data between the two sockets until communication is complete.
        self.bandwidth_usage_bytes += self._forward_data(client_socket, remote_socket)
        self.site_visits[host] = self.site_visits.get(host, 0) + 1

    def _forward_data(
        self, client_socket: socket.socket, remote_socket: socket.socket
    ) -> int:
        total_bytes = 0
        try:
            while True:
                # Wait for one of the sockets to indicate as ready.
                ready_sockets, _, _ = select.select(
                    [client_socket, remote_socket], [], []
                )
                for socket in ready_sockets:
                    data = socket.recv(self.BUFFER_SIZE)
                    if not data:
                        return total_bytes

                    total_bytes += len(data)

                    # Send the data to the other socket.
                    if socket is client_socket:
                        remote_socket.sendall(data)
                    else:
                        client_socket.sendall(data)
        except Exception as e:
            print(f"Error forwarding data: {e}")

        return total_bytes
