import base64
from contextlib import asynccontextmanager
import os
import requests
from fastapi import FastAPI, HTTPException, Request, Response, status


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    print(metrics())


bandwidth_usage = 0
visited_sites = dict()

# Using os.environ so this throws if these aren't set.
username = os.environ["STEEL_USERNAME"]
password = os.environ["STEEL_PASSWORD"]

app = FastAPI(lifespan=lifespan)


@app.get("/")
def proxy(request: Request):
    global bandwidth_usage
    global visited_sites

    print(request.headers)

    check_authorization(request)

    target_url = request.headers["Host"]
    if not target_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required header Host.",
        )

    # The host is missing a scheme and we can't meaningfully proxy https.
    response = requests.get(f"http://{target_url}")
    response.raise_for_status()

    content_length = int(response.headers.get("Content-Length", "0"))
    bandwidth_usage += content_length
    num_visits = visited_sites.get(target_url, 0)
    visited_sites[target_url] = num_visits + 1

    return Response(response.text, media_type="text/html; charset=UTF-8")


@app.get("/metrics")
def metrics():
    global bandwidth_usage
    global visited_sites

    # If we're below 1 MB, use KB for the bandwidth display.
    if bandwidth_usage < 1048576:
        bandwidth_string = f"{bandwidth_usage // 1024}KB"
    else:
        bandwidth_string = f"{bandwidth_usage // 1048576}MB"

    return {
        "bandwidth_usage": bandwidth_string,
        "top_sites": [
            {"url": key, "visits": value}
            for key, value in sorted(
                visited_sites.items(),
                key=lambda item: item[1],
                reverse=True,
            )
        ][:10],
    }


def check_authorization(request: Request) -> None:
    auth_header = request.headers["Proxy-Authorization"]
    if not auth_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing required header Proxy-Authorization.",
        )

    if not auth_header.startswith("Basic "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Only basic authorization is supported.",
        )

    encoded_credentials = auth_header[len("Basic ") :]
    decoded_credentials = base64.b64decode(encoded_credentials).decode("utf-8")
    request_username, request_password = decoded_credentials.split(":", 1)
    if request_username != username or request_password != password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password provided.",
        )
