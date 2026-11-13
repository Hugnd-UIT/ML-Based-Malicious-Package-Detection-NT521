#!/usr/bin/env bash
# Tao file moi va bien moi truong gia cho cac goi mo phong doc.
# Chay trong VM sandbox TRUOC khi cai cac goi:  source setup_decoys.sh
# File moi chi chua chu gia, khong phai bi mat that.

DECOY="$HOME/fake_secret.txt"
if [ ! -f "$DECOY" ]; then
  cat > "$DECOY" <<'EOF'
# DAY LA FILE MOI VO HAI CHO DO AN NT230 (DySec)
# Khong phai bi mat that. Dung de cac goi mo phong co cai de "doc trom".
AWS_ACCESS_KEY_ID=FAKE-AKIA-0000-DECOY
AWS_SECRET_ACCESS_KEY=FAKE-decoy-secret-not-real
API_TOKEN=FAKE-decoy-token-1234567890
EOF
  echo "[setup_decoys] da tao $DECOY"
else
  echo "[setup_decoys] $DECOY da co san"
fi

# Bien moi truong gia cho sim-exfil-env
export FAKE_TOKEN="FAKE-decoy-env-token-abcdef"
echo "[setup_decoys] da dat bien moi truong FAKE_TOKEN (gia)"
echo "[setup_decoys] xong. Nho chay fake_c2.py va fake_http.py o cua so khac neu can."
