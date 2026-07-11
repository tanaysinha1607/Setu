import urllib.request, json, sys

key = open('.env').read().split('=',1)[1].strip()
sys.stdout.write(f"Key prefix: {repr(key[:25])}\n")
sys.stdout.flush()

url = f'https://generativelanguage.googleapis.com/v1beta/models?key={key}'
req = urllib.request.Request(url)
try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode())
        models = data.get('models', [])
        sys.stdout.write(f"Found {len(models)} models:\n")
        for m in models:
            sys.stdout.write(f"  {m.get('name')} | {m.get('supportedGenerationMethods', [])}\n")
        sys.stdout.flush()
except urllib.error.HTTPError as e:
    body = e.read().decode()
    sys.stdout.write(f"HTTP {e.code}: {body}\n")
    sys.stdout.flush()
except Exception as e:
    sys.stdout.write(f"Error: {e}\n")
    sys.stdout.flush()
