import json


def flatten_headers(file_path):
    """Converts a colon-separated key-value file (like headers) to a JSON string."""
    data = {}
    with open(file_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or ": " not in line:
                continue
            key, value = line.split(": ", 1)
            data[key.strip()] = value.strip()
    return json.dumps(data)


def flatten_netscape_cookies(file_path):
    """
    Converts a standard Netscape cookie file (tab-separated) into a
    simple key-value JSON string suitable for httpx.
    """
    cookies = {}
    with open(file_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if not line or line.startswith("#"):
                continue

            parts = line.split("\t")

            if len(parts) == 7:
                cookie_name = parts[5]
                cookie_value = parts[6]
                cookies[cookie_name] = cookie_value

    return json.dumps(cookies)


def flatten_payload(file_path):
    """Converts the specific tab-separated payload file to a JSON string."""
    data = {}
    with open(file_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or "\t" not in line:
                continue
            key, value_str = line.split("\t", 1)
            key = key.strip()
            value_str = value_str.strip()

            if key == "variables":
                try:
                    data[key] = json.loads(value_str)
                except json.JSONDecodeError:
                    print(
                        f"Warning: Could not parse JSON for key '{key}'. Storing as string."
                    )
                    data[key] = value_str
            else:
                data[key] = value_str
    return json.dumps(data)


if __name__ == "__main__":
    print("--- INSTAGRAM_HEADERS_JSON ---")
    print(flatten_headers("headers.txt"))
    print("\n--- INSTAGRAM_COOKIES_JSON ---")
    print(flatten_netscape_cookies("cookies.txt"))
    print("\n--- INSTAGRAM_PAYLOAD_JSON ---")
    print(flatten_payload("payload.txt"))
