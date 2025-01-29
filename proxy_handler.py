import http.client
import http.server
import json


class ProxyHandler(http.server.BaseHTTPRequestHandler):
    bandwidth_usage_bytes = 0
    visited_sites = dict[str, int]()

    def do_CONNECT(self):
        pass

    def do_GET(self):
        if self.path == "/metrics":
            metrics = self._get_metrics()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(metrics).encode())
            return

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
