# -*- coding: utf-8 -*-
"""
May chu HTTP gia cho do an NT230 (DySec).
Chi phuc vu tren 127.0.0.1:8000, tra ve mot "payload" vo hai (chi in chu hello).
Dung cho goi sim-dropper co cho de tai file ve.
Chay:  python fake_http.py
Dung:  Ctrl + C
"""
import http.server, socketserver

HOST, PORT = "127.0.0.1", 8000
PAYLOAD = b'print("hello from harmless dropped payload")\n'

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(PAYLOAD)))
        self.end_headers()
        self.wfile.write(PAYLOAD)

    def log_message(self, fmt, *args):
        print("[fake_http]", self.address_string(), fmt % args)

def main():
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer((HOST, PORT), Handler) as httpd:
        print(f"[fake_http] dang phuc vu tai http://{HOST}:{PORT} (chi loopback). Ctrl+C de dung.")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[fake_http] da dung.")

if __name__ == "__main__":
    main()
