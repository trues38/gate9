import httpx
print(f"httpx version: {httpx.__version__}")
try:
    httpx.Client(proxy="http://test")
    print("httpx.Client accepts proxy")
except TypeError as e:
    print(f"httpx.Client DOES NOT accept proxy: {e}")
try:
    httpx.Client(proxies="http://test")
    print("httpx.Client accepts proxies")
except TypeError as e:
    print(f"httpx.Client DOES NOT accept proxies: {e}")
