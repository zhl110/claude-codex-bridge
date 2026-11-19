"""Computer Use Bridge — Claude Code drives, Python executes atomic actions."""
import base64, json, os, re, sys, time, urllib.request
from io import BytesIO
from PIL import ImageGrab
import win32api, win32con, win32clipboard
import pywinauto.keyboard as kb

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

OLLAMA = "http://localhost:11434/api/chat"
VISION_MODEL = "minicpm-v:8b"
SCREENSHOT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_bridge_screen.jpg")

DESCRIBE_PROMPT = """Describe this Windows desktop screenshot in exhaustive, methodical detail.

Your task is purely descriptive. Do NOT suggest what to do next. Do NOT output JSON.
Output only a plain-text inventory of the screen.

Follow this structure:

=== WINDOWS AND LAYOUT ===
- Which applications are open? List each window, its title, its position.
- Which window is currently focused/active? How can you tell?
- What does the taskbar show (open apps, system tray, clock)?

=== TEXT CONTENT (read everything) ===
- Every visible text string: headings, paragraphs, button labels, menu items,
  input field contents, status messages, error messages, tooltips.
- Quote the text exactly where possible.

=== INTERACTIVE ELEMENTS (with approximate coordinates) ===
- Buttons: label text, approximate center coordinates, whether they look enabled or grayed out.
- Text fields / input boxes: any existing content, placeholder text, approximate bounding box.
- Links / clickable text: the visible text, approximate position.
- Dropdown menus, checkboxes, radio buttons, tabs, sliders.
- Icons: what they represent, approximate position.
- Scrollbars: which region has one, approximate thumb position.

=== MOUSE CURSOR ===
- If a cursor is visible, note its approximate coordinates and shape (arrow, I-beam, hand, hourglass, etc.).

=== NOTABLE VISUAL STATE ===
- Any highlighted/selected text or elements.
- Any loading spinners, progress bars, flashing elements.
- Any error dialogs, popups, notifications, or overlays.

Be as coordinate-specific as possible. Use the format "approximately (X,Y)" or "roughly spanning (X1,Y1) to (X2,Y2)"."""


def take_screenshot(path=SCREENSHOT_PATH):
    """Capture full screen, save as JPEG, return (path, width, height)."""
    img = ImageGrab.grab()
    img.save(path, format="JPEG", quality=70)
    return {"path": path, "width": img.width, "height": img.height}


def describe_screen(model=VISION_MODEL):
    """Take screenshot, send to vision model, return plain-text description."""
    img = ImageGrab.grab()
    img.save(SCREENSHOT_PATH, format="JPEG", quality=70)
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=70)
    img_b64 = base64.b64encode(buf.getvalue()).decode()

    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": DESCRIBE_PROMPT, "images": [img_b64]}],
        "stream": False,
    }).encode("utf-8")

    req = urllib.request.Request(OLLAMA, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    resp = urllib.request.urlopen(req, timeout=120)
    text = json.loads(resp.read())["message"]["content"]
    raw = text.strip()
    raw = re.sub(r"^```(?:json|markdown|text)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return raw


def click(x, y):
    """Left-click at pixel coordinates."""
    win32api.SetCursorPos((x, y))
    time.sleep(0.05)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(0.02)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    return {"action": "click", "x": x, "y": y, "status": "ok"}


def rclick(x, y):
    """Right-click at pixel coordinates."""
    win32api.SetCursorPos((x, y))
    time.sleep(0.05)
    win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
    time.sleep(0.02)
    win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)
    return {"action": "rclick", "x": x, "y": y, "status": "ok"}


def dclick(x, y):
    """Double-click at pixel coordinates."""
    win32api.SetCursorPos((x, y))
    time.sleep(0.05)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(0.02)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    time.sleep(0.05)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(0.02)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    return {"action": "dclick", "x": x, "y": y, "status": "ok"}


def move(x, y):
    """Move cursor to coordinates without clicking."""
    win32api.SetCursorPos((x, y))
    return {"action": "move", "x": x, "y": y, "status": "ok"}


def drag(x1, y1, x2, y2):
    """Mouse drag from (x1,y1) to (x2,y2) with interpolated steps."""
    win32api.SetCursorPos((x1, y1))
    time.sleep(0.05)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(0.05)
    steps = 10
    for i in range(1, steps + 1):
        xi = int(x1 + (x2 - x1) * i / steps)
        yi = int(y1 + (y2 - y1) * i / steps)
        win32api.SetCursorPos((xi, yi))
        time.sleep(0.008)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    return {"action": "drag", "from": [x1, y1], "to": [x2, y2], "status": "ok"}


def type_text(text):
    """Type text via clipboard paste (handles Unicode including Chinese)."""
    win32clipboard.OpenClipboard()
    win32clipboard.EmptyClipboard()
    win32clipboard.SetClipboardText(text, win32clipboard.CF_UNICODETEXT)
    win32clipboard.CloseClipboard()
    time.sleep(0.05)
    kb.send_keys("^v")
    return {"action": "type", "text": text, "status": "ok"}


def send_key(keys):
    """Send keystrokes — ^c, {ENTER}, {TAB}, {VK_F5}, etc."""
    kb.send_keys(keys)
    return {"action": "key", "keys": keys, "status": "ok"}


def scroll(n):
    """Scroll up (n>0) or down (n<0) by n notches at current cursor position."""
    delta = n * 120
    win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, delta, 0)
    direction = "up" if n > 0 else "down" if n < 0 else "none"
    return {"action": "scroll", "notches": n, "direction": direction, "status": "ok"}


def wait(n):
    """Sleep for n seconds."""
    time.sleep(n)
    return {"action": "wait", "seconds": n, "status": "ok"}


def get_resolution():
    """Return primary monitor resolution."""
    w = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
    h = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
    return {"width": w, "height": h}


def print_usage():
    print("Usage: python bridge.py <command> [args]")
    print("  screen                         Take screenshot, return path+resolution")
    print("  describe [model]               Describe screen via vision model")
    print("  click X Y                      Left-click")
    print("  rclick X Y                     Right-click")
    print("  dclick X Y                     Double-click")
    print("  move X Y                       Move cursor")
    print("  drag X1 Y1 X2 Y2               Mouse drag")
    print("  type TEXT                      Type via clipboard paste")
    print("  key KEYS                       Send keystrokes")
    print("  scroll N                       Scroll up(+)/down(-)")
    print("  wait N                         Sleep N seconds")
    print("  resolution                     Get screen resolution")


def main():
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)

    cmd = sys.argv[1]

    try:
        if cmd == "screen":
            print(json.dumps(take_screenshot()))

        elif cmd == "describe":
            model = sys.argv[2] if len(sys.argv) > 2 else VISION_MODEL
            print(describe_screen(model))

        elif cmd == "click":
            x, y = int(sys.argv[2]), int(sys.argv[3])
            print(json.dumps(click(x, y)))

        elif cmd == "rclick":
            x, y = int(sys.argv[2]), int(sys.argv[3])
            print(json.dumps(rclick(x, y)))

        elif cmd == "dclick":
            x, y = int(sys.argv[2]), int(sys.argv[3])
            print(json.dumps(dclick(x, y)))

        elif cmd == "move":
            x, y = int(sys.argv[2]), int(sys.argv[3])
            print(json.dumps(move(x, y)))

        elif cmd == "drag":
            x1, y1, x2, y2 = map(int, sys.argv[2:6])
            print(json.dumps(drag(x1, y1, x2, y2)))

        elif cmd == "type":
            text = " ".join(sys.argv[2:])
            print(json.dumps(type_text(text)))

        elif cmd == "key":
            keys = " ".join(sys.argv[2:])
            print(json.dumps(send_key(keys)))

        elif cmd == "scroll":
            n = int(sys.argv[2])
            print(json.dumps(scroll(n)))

        elif cmd == "wait":
            n = float(sys.argv[2])
            print(json.dumps(wait(n)))

        elif cmd == "resolution":
            print(json.dumps(get_resolution()))

        else:
            print_usage()
            sys.exit(1)

    except Exception as e:
        print(json.dumps({"status": "error", "error": str(e)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
