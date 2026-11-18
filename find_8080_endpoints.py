import re

with open("app_8080_page.html", "r", encoding="utf-8") as f:
    html = f.read()

# Find all fetch/api endpoints in the html
endpoints = set(re.findall(r'["\'](/api/[^"\']+|/snapshot\.bmp[^"\']*)["\']', html))
print("Endpoints found in port 8080 page:")
for ep in sorted(endpoints):
    print(" -", ep)
