import http.server
import json
import os
import ssl

from proxy_handler import ProxyHandler


if __name__ == "__main__":
    # We load these here just to throw if they don't exist
    PROXY_USERNAME = os.environ["PROXY_USERNAME"]
    PROXY_PASSWORD = os.environ["PROXY_PASSWORD"]

    # Define server address and port
    HOST = os.getenv("PROXY_HOST", "localhost")
    PORT = os.getenv("PROXY_PORT", "7777")

    # Create HTTPs server
    proxy_server = http.server.HTTPServer((HOST, int(PORT)), ProxyHandler)
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_context.load_cert_chain(certfile="cert.pem", keyfile="key.pem")
    proxy_server.socket = ssl_context.wrap_socket(proxy_server.socket, server_side=True)

    print(
        f"Proxy server started, listening for connections on https://{HOST}:{PORT} ..."
    )
    try:
        proxy_server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        print(
            f"\nProxy server stopped. Metrics:\n{json.dumps(ProxyHandler.get_metrics(), indent=4)}"
        )
