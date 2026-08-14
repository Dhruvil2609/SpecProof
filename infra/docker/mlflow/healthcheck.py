from urllib.request import urlopen

with urlopen("http://127.0.0.1:5000/health", timeout=5) as response:
    if response.status != 200:
        raise SystemExit(1)
