"""Computer Use - screenshot -> local vision model -> action -> verify"""
import base64, json, os, re, sys, time, urllib.request
from io import BytesIO
from PIL import ImageGrab
import win32api, win32con, win32clipboard
import pywinauto.keyboard as kb

# Force UTF-8 on Windows
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

OLLAMA = "http://localhost:11434/api/chat"
MODEL = "minicpm-v:8b"
MAX_STEPS = 8
TMP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_cu_tmp")


def call_vision(img_b64, task, history):
    """Call local Ollama vision model"""
    ctx = f"Task: {task}"
    if history:
        ctx += f"\nPrevious: {json.dumps(history[-2:], ensure_ascii=False)}"
    ctx += "\nAnalyze screenshot, output next action JSON only."

    body = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": ctx, "images": [img_b64]}],
        "stream": False,
    }).encode("utf-8")

    req = urllib.request.Request(OLLAMA, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    resp = urllib.request.urlopen(req, timeout=120)
    text = json.loads(resp.read())["message"]["content"]
    raw = text.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    print(f"  DEBUG raw: {raw[:300]}")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Try to find JSON object with balanced braces
        for m in re.finditer(r"\{", raw):
            depth, end = 0, -1
            for i in range(m.start(), len(raw)):
                if raw[i] == "{": depth += 1
                elif raw[i] == "}":
                    depth -= 1
                    if depth == 0:
                        end = i + 1
                        break
            if end > 0:
                try:
                    return json.loads(raw[m.start():end])
                except json.JSONDecodeError:
                    continue
        return {"action": "fail", "reason": f"parse err: {raw[:200]}"}


def do(action):
    """Execute an action"""
    act = action.get("action", "")
    if act == "click":
        x, y = int(action["x"]), int(action["y"])
        win32api.SetCursorPos((x, y))
        time.sleep(0.05)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        time.sleep(0.02)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        print(f"  CLICK ({x},{y})")
    elif act == "type":
        t = action["text"]
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardText(t, win32clipboard.CF_UNICODETEXT)
        win32clipboard.CloseClipboard()
        time.sleep(0.05)
        kb.send_keys("^v")
        print(f"  TYPE: {t}")
    elif act == "key":
        kb.send_keys(action["keys"])
        print(f"  KEY: {action['keys']}")
    elif act == "done":
        print(f"  DONE: {action.get('reason', '')}")
    elif act == "fail":
        print(f"  FAIL: {action.get('reason', '')}")


def run(task, bbox=None):
    """Main loop: screenshot -> analyze -> act -> repeat"""
    os.makedirs(TMP, exist_ok=True)
    history = []
    print(f"\n{'='*50}\nTASK: {task}\n{'='*50}")

    for step in range(1, MAX_STEPS + 1):
        print(f"\n--- Step {step}/{MAX_STEPS} ---")
        img = ImageGrab.grab(bbox=bbox)
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=70)
        buf.seek(0)
        img_b64 = base64.b64encode(buf.read()).decode()
        img.save(os.path.join(TMP, f"s{step}.jpg"))

        print("  Thinking...")
        action = call_vision(img_b64, task, history)
        print(f"  OBS: {action.get('obs', '?')}")
        print(f"  ACT: {action.get('action')} | {action.get('reason', '')}")

        if action.get("action") in ("done", "fail"):
            do(action)
            break

        do(action)
        history.append({"s": step, "a": action.get("action"), "r": action.get("reason")})
        time.sleep(0.8)

        if step == MAX_STEPS:
            print("  WARNING: max steps reached")

    for f in os.listdir(TMP):
        os.remove(os.path.join(TMP, f))
    os.rmdir(TMP)
    print("  Cleaned up")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    run(task=sys.argv[1] if len(sys.argv) > 1 else "open Start menu")
