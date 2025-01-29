import http.client
import http.server
import json
import select
import socket


class ProxyHandler(http.server.BaseHTTPRequestHandler):
    BUFFER_SIZE = 4096

    bandwidth_usage_bytes = 0
    visited_sites = dict[str, int]()

    def do_CONNECT(self):
        # Connect to the remote server.
        host, port = self.path.split(":")
        remote_socket = socket.create_connection((host, int(port)))

        # Send the connection established message.
        self.send_response_only(200, "Connection Established")
        self.end_headers()

        # Tunnel data between the servers.
        ProxyHandler.bandwidth_usage_bytes += self._forward_data(
            self.request, remote_socket
        )
        ProxyHandler.visited_sites[host] = ProxyHandler.visited_sites.get(host, 0) + 1

    def do_GET(self):
        # Check for the metrics handler.
        if self.path == "/metrics":
            metrics = self._get_metrics()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(metrics).encode())
            return

        # Otherwise, forward the call to the HTTP server and send the response back.
        host = self.headers["Host"]
        http_connection = http.client.HTTPConnection(host)
        http_connection.putrequest(self.command, self.path, skip_host=True)
        for key, value in self.headers.items():
            http_connection.putheader(key, value)
        http_connection.endheaders()
        http_connection.sock

        http_response = http_connection.getresponse()
        self.send_response(http_response.getcode())
        for key, value in http_response.getheaders():
            # The HTTPResponse class internally handles chunked encoding in a convenient way.
            if key != "Transfer-Encoding":
                self.send_header(key, value)
        self.end_headers()

        data = http_response.read()
        self.wfile.write(data)
        ProxyHandler.bandwidth_usage_bytes += len(data)
        ProxyHandler.visited_sites[host] = ProxyHandler.visited_sites.get(host, 0) + 1

    def _forward_data(
        self, client_socket: socket.socket, remote_socket: socket.socket
    ) -> int:
        total_bytes = 0
        try:
            while True:
                # Wait for one of the sockets to indicate as ready.
                ready, _, _ = select.select([client_socket, remote_socket], [], [])
                for socket in ready:
                    data = socket.recv(ProxyHandler.BUFFER_SIZE)
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

    def _get_metrics(self):
        top_sites = sorted(
            [
                {"url": key, "visits": value}
                for key, value in ProxyHandler.visited_sites.items()
            ],
            key=lambda s: s["visits"],
            reverse=True,
        )

        if ProxyHandler.bandwidth_usage_bytes < 1_048_576:
            bandwidth_usage = f"{ProxyHandler.bandwidth_usage_bytes // 1024}KB"
        else:
            bandwidth_usage = f"{ProxyHandler.bandwidth_usage_bytes // 1_048_576}MB"

        metrics = {
            "bandwidth_usage": bandwidth_usage,
            "top_sites": top_sites[:5],
        }

        return metrics
