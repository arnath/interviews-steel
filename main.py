import base64
import os
import requests
from fastapi import FastAPI, HTTPException, Request, Response, status

app = FastAPI()

# Using os.environ so this throws if these aren't set.
username = os.environ["STEEL_USERNAME"]
password = os.environ["STEEL_PASSWORD"]


@app.get("/")
def proxy(request: Request):
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

    return Response(response.text, media_type="text/html; charset=UTF-8")


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
