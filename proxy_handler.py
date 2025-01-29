import http.client
import http.server


class ProxyHandler(http.server.BaseHTTPRequestHandler):
    BUFFER_SIZE = 4096

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.protocol_version = "HTTP/1.0"

    def do_CONNECT(self):
        pass

    def do_GET(self):
        print(self.protocol_version)
        if self.path == "/metrics":
            self._handle_metrics()
            return

        http_connection = http.client.HTTPConnection(self.headers["Host"])
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

        self.wfile.write(http_response.read())

    def _handle_metrics(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        # self.wfile.write(json.dumps())

    def _forward_chunked_response(self, http_response: http.client.HTTPResponse):
        while True:
            first_line = http_response.readline()
            self.wfile.write(first_line + b"\r\n")
            chunk_size_str = first_line.strip()
            try:
                chunk_size = int(chunk_size_str, 16)  # Convert hex to int
                print(chunk_size)
            except ValueError:
                self.send_error(400, "Invalid chunk size")
                return

            if chunk_size == 0:
                break  # Last chunk

            chunk_data = http_response.read(chunk_size)
            self.wfile.write(chunk_data + b"\r\n")
            http_response.read(2)  # Consume the trailing CRLF

        # Write final empty chunk.
        self.wfile.write(b"\r\n")
