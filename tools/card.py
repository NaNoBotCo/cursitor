#!/usr/bin/env python3
"""Share card for the Cursitor page: renders tools/card.html in headless Chrome to docs/card.jpg (1200x630).
Chrome shapes the Thai line; Pillow on this Mac has no text shaping."""
import os, subprocess, tempfile
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
png = os.path.join(tempfile.mkdtemp(), "card.png")
subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--window-size=1200,630",
                "--virtual-time-budget=6000", "--screenshot=" + png, "file://" + os.path.join(HERE, "card.html")],
               check=True, capture_output=True)
out = os.path.join(HERE, "..", "docs", "card.jpg")
Image.open(png).convert("RGB").save(out, quality=88)
print(os.path.normpath(out))
