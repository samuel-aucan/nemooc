"""
Diagnóstico del portal Artikos.
Uso: python debug_artikos.py "URL_DEL_EMAIL"
"""
import sys
import requests
from bs4 import BeautifulSoup

URL = sys.argv[1] if len(sys.argv) > 1 else input("Pega la URL del email Artikos: ").strip()
RUT = "76215260-6"

session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})

print("\n=== 1. GET ===")
r1 = session.get(URL, timeout=15)
print(f"Status: {r1.status_code}  |  URL final: {r1.url}")
r1.encoding = r1.apparent_encoding or "latin-1"

soup1 = BeautifulSoup(r1.text, "html.parser")
form = soup1.find("form")
if form:
    print(f"Form action: {form.get('action', '(none)')}")
    print(f"Form method: {form.get('method', '(none)')}")
    for inp in form.find_all("input"):
        print(f"  input: name={inp.get('name')} type={inp.get('type')} value={inp.get('value','')!r}")
else:
    print("NO SE ENCONTRO <form> en la pagina GET")

print("\n=== 2. POST (mismo URL, Key+Key2 del form + Clave=RUT) ===")
hidden = {
    inp.get("name"): inp.get("value", "")
    for inp in soup1.find_all("input", {"type": "hidden"})
    if inp.get("name")
}
print(f"Campos hidden del form: {hidden}")
post_data = {**hidden, "Clave": RUT}
print(f"POST data: {post_data}")
r2 = session.post(URL, data=post_data, timeout=20)
print(f"Status: {r2.status_code}  |  URL final: {r2.url}")
r2.encoding = r2.apparent_encoding or "latin-1"
html2 = r2.text

print(f"Contiene 'ORDEN DE COMPRA': {'ORDEN DE COMPRA' in html2.upper()}")
print(f"Contiene 'Rut': {'Rut' in html2}")
print(f"Primeros 800 chars de la respuesta POST:")
print("-" * 60)
print(html2[:800])
print("-" * 60)

# Extra: mostrar texto extraído por BeautifulSoup
from bs4 import BeautifulSoup as BS
soup2 = BS(html2, "html.parser")
text2 = soup2.get_text(" ", strip=True)
print(f"\n=== 4. TEXTO BS4 (primeros 600 chars) ===")
print(text2[:600])

import re
title = soup2.find("title")
print(f"\nTitle tag: {title}")
m = re.search(r'ORDEN DE COMPRA[^0-9]{{0,40}}(\d{{5,}})', text2, re.IGNORECASE)
print(f"Regex 'ORDEN DE COMPRA...(5+ dígitos)': {m.group(0) if m else 'NO MATCH'}")

# Si el POST falló, intentar con la acción del form
if form and form.get("action") and form.get("action") != URL:
    action = form.get("action")
    if not action.startswith("http"):
        from urllib.parse import urljoin
        action = urljoin(URL, action)
    print(f"\n=== 3. POST a form action: {action} ===")
    r3 = session.post(action, data=post_data, timeout=20)
    print(f"Status: {r3.status_code}")
    r3.encoding = r3.apparent_encoding or "latin-1"
    print(f"Contiene 'ORDEN DE COMPRA': {'ORDEN DE COMPRA' in r3.text.upper()}")
    print(f"Primeros 800 chars:")
    print("-" * 60)
    print(r3.text[:800])
