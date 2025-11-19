# Semantic Video Summarization Pipeline - BE

## About project

This sub-folder is back-end part of [SVSP](../README.md)

## How to run

1. Install required python package
```PowerShell
pip install -r requirements.txt
```

2. Run main.py with following command at svsp/svsp-be/ path
```PowerShell
uvicorn main:app --reload
```

...or

```bash
python main.py
```

### Docker

Build and run it from the container as:

```bash
docker build -t l2s-be .
docker run -p 8080:8080 -v .:/app --env-file .env l2s-be
```

## Backend Description

L2S_BE (Long2Short Backend) is the server-side application for this service.

### Technical Stack

- **FastAPI**: A modern, high-performance web framework for building APIs with Python. We chose FastAPI for its speed, asynchronous support (which is ideal for I/O-bound tasks like file handling), and automatic generation of interactive API documentation from the code.

- **Uvicorn**: A fast ASGI server. Uvicorn is used to run our FastAPI application, providing a foundation to handle concurrent requests efficiently.

## Secret Key

A secret key loaded in `app/config/environments.py` and is used for `SessionMiddleware`. This allows our application to keep track of a user's infrmation across multiple requests (e.g., keep a user logged in) by storing session data in a cookie in the user's browser.

Furthermore, it cryptographically signs the session cookie, which allows the server to verify that the data in the cookie has not been modified or tampered with by the client. 

Without it, a malicious user could alter their session data (like user ID) to gain access to other accounts or parts of our application.

For developers, you need to generate just a long, random and unpredictable string. This can be done using Python `secrets`.

```bash
python -c 'import secrets; print(secrets.token_hex(32))'
```

Then add the output to an `.env` file in the root directory (this is ignored according to `.gitignore`).

```plaintext
SECRET_KEY='<key>'
```

## Testing

1. Using docs

The easiest way to test is by accessing the API documentation at `https://localhost:<PORT_NUMBER>/docs` and press `Try it out`.


2. HTTP File

We can test using an `.http` file (`api.http`) to define and send HTTP requests directly from the code editor using a REST client extension. This file should include requests for all the endpoints defined in our application.

Note that for some requests (e.g., file upload request) we might need additional files. In the case of the file upload request, a sample file in the same directory is required (it can be something like `sample.txt`).

The REST Client extension should be installed. The extension should recognize the requests so we can click a "Send Request" link above eqach one to test the endpoints individually. 

### Troubleshooting

Note that when running through `uvicorn main:app --reload` and closing with `Ctrl+C` sometimes the server won't close completely. In such case:

```bash
sudo lsof -i :<PORT_NUMBER> # see current processes
kill -9 <PID> 
```

## Docs

OpenAPI documentation can be accessed by entering:

```
https://localhost:<PORT_NUMBER>/docs
```
