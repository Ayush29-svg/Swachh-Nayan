with open('studio_dashboard.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Fix CSS syntax error
bad_css = """.toast {
            pointer-events: auto;
        .toast {"""
good_css = """.toast {
            pointer-events: auto;
        }
        .toast {"""

if bad_css in content:
    content = content.replace(bad_css, good_css)
    print("Fixed CSS syntax error in .toast!")

# 2. Fix BASE_URL so relative endpoints are always used when accessed via HTTP
target_old = 'let BASE_URL = window.location.protocol + "//" + PICO_IP + ":" + PICO_PORT;\n        if (window.location.protocol === "file:") {\n            BASE_URL = "http://172.32.0.93:8088";\n        }'
target_new = 'let BASE_URL = (window.location.protocol === "file:") ? "http://172.32.0.93:8088" : "";'

if target_old in content:
    content = content.replace(target_old, target_new)
    print("Replaced BASE_URL with bulletproof relative endpoint logic!")
else:
    print("Searching for BASE_URL line...")
    import re
    content = re.sub(
        r'let BASE_URL = window\.location\.protocol \+ "//" \+ PICO_IP \+ ":" \+ PICO_PORT;\s+if \(window\.location\.protocol === "file:"\) \{\s+BASE_URL = "http://172\.32\.0\.93:8088";\s+\}',
        'let BASE_URL = (window.location.protocol === "file:") ? "http://172.32.0.93:8088" : "";',
        content
    )
    print("Replaced with regex!")

with open('studio_dashboard.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Saved studio_dashboard.html!")
