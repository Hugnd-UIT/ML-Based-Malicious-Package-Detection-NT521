# -*- coding: utf-8 -*-
"""
May chu gia (fake C2) cho do an NT230 (DySec).
Chi lang nghe tren 127.0.0.1:9999, ghi lai nhung gi nhan duoc. Khong lam gi khac.
Dung cho cac goi mo phong exfil / reverse-shell co dich de ket noi toi.
Chay:  python fake_c2.py
Dung:  Ctrl + C
"""
import socket, datetime, os

HOST, PORT = "127.0.0.1", 9999
LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fake_c2.log")

def main():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((HOST, PORT))
    srv.listen(5)
    print(f"[fake_c2] dang nghe tai {HOST}:{PORT} (chi loopback). Ctrl+C de dung.")
    try:
        while True:
            conn, addr = srv.accept()
            conn.settimeout(3)
            data = b""
            try:
                while True:
                    chunk = conn.recv(4096)
                    if not chunk:
                        break
                    data += chunk
            except Exception:
                pass
            conn.close()
            ts = datetime.datetime.now().isoformat(timespec="seconds")
            line = f"{ts} tu {addr[0]}:{addr[1]} nhan {len(data)} byte: {data[:120]!r}"
            print("[fake_c2]", line)
            with open(LOG, "a", encoding="utf-8") as f:
                f.write(line + "\n")
    except KeyboardInterrupt:
        print("\n[fake_c2] da dung.")
    finally:
        srv.close()

if __name__ == "__main__":
    main()
