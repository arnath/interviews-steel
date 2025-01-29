import http.server
import ssl

from proxy_handler import ProxyHandler


if __name__ == "__main__":
    # Define server address and port
    HOST = "localhost"
    PORT = 7777

    # Create HTTPs server
    proxy_server = http.server.HTTPServer((HOST, PORT), ProxyHandler)
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_context.load_cert_chain(certfile="cert.pem", keyfile="key.pem")
    proxy_server.socket = ssl_context.wrap_socket(proxy_server.socket, server_side=True)

    print(f"Serving on https://{HOST}:{PORT}")
    proxy_server.serve_forever()
