with open('studio_dashboard.html', 'r', encoding='utf-8') as f:
    text = f.read()

bad_part = """            } catch (err) {
                showToast("Sweep trigger error: " + err.message, "error");
            }
        }`, "info");
        }"""

good_part = """            } catch (err) {
                showToast("Sweep trigger error: " + err.message, "error");
            }
        }"""

# Try exact or normalized replacement
text_norm = text.replace('\r\n', '\n')
bad_part_norm = bad_part.replace('\r\n', '\n')
good_part_norm = good_part.replace('\r\n', '\n')

if bad_part_norm in text_norm:
    text_norm = text_norm.replace(bad_part_norm, good_part_norm, 1)
    print("Replaced bad token successfully!")
else:
    import re
    # Match corrupted block
    pattern = r'(showToast\("Sweep trigger error: "[^\n]*\n\s*\}\n\s*\}[\s\S]*?info"\);\s*\n\s*\})'
    m = re.search(pattern, text_norm)
    if m:
        text_norm = text_norm[:m.start()] + 'showToast("Sweep trigger error: " + err.message, "error");\n            }\n        }' + text_norm[m.end():]
        print("Replaced using regex pattern!")
    else:
        print("Could not find bad token pattern!")

with open('studio_dashboard.html', 'w', encoding='utf-8') as f:
    f.write(text_norm)

# Extract script and test
idx = text_norm.find('<script>')
end_idx = text_norm.find('</script>', idx)
script = text_norm[idx+8:end_idx]

with open('extracted_script.js', 'w', encoding='utf-8') as f:
    f.write(script)

print("Saved studio_dashboard.html and updated extracted_script.js")
