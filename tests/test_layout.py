"""Allineamenti responsive: home e intro a 6 schermi (360, 390, 430, 768, 1366, 1920): python -m tests.test_layout
Nessuno sbordamento orizzontale, nessun elemento fuori schermo, «La nostra storia» (titolo, riga, player) centrata con margini simmetrici,
intro centrata su telefono in verticale. Usa tools/audit_layout.py (che può anche salvare gli screenshot)."""
import contextlib
import io
import sys

from tools import audit_layout

buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    rc = audit_layout.main()
out = [l for l in buf.getvalue().splitlines() if l.startswith("PROBLEMA") or "problemi" in l or "nessun problema" in l]
for l in out:
    print(l)
print(("PASS" if rc == 0 else "FAIL"), "home e intro allineate su 6 schermi")
print(f"\n{1 if rc == 0 else 0} ok, {0 if rc == 0 else 1} falliti")
sys.exit(rc)
