with open("requirements_v2.txt", "rb") as f:
    content = f.read()
content = content.replace(b"\x00", b"")
with open("requirements_v2.txt", "wb") as f:
    f.write(content)
