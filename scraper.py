#!/usr/bin/env python3
"""
Traqueur de stock gratuit pour le Midea PortaSplit (MMCS-12HRN8-QRD0).
Scanne plusieurs enseignes, détecte les changements de statut, envoie une
alerte ntfy quand un produit repasse en stock, et écrit status.json
(consommé par index.html pour l'affichage).
"""

import json
import os
import re
import sys
from datetime import datetime, timezone

import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fr-FR,fr;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

STATUS_FILE = "status.json"

# ---- Configuration des enseignes ------------------------------------------------
SITES = [
    {
        "name": "Amazon.fr",
        "url": "https://www.amazon.fr/dp/B0CY2YW8BT",
        "in_stock_markers": ["ajouter au panier", "acheter maintenant"],
        "out_of_stock_markers": [
            "actuellement indisponible",
            "quantité insuffisante",
        ],
    },
    {
        "name": "Leroy Merlin",
        "url": "https://www.leroymerlin.fr/produits/climatiseur-split-mobile-reversible-portasplit-midea-par-optimea-93857579.html",
        "in_stock_markers": ["ajouter au panier"],
        "out_of_stock_markers": ["rupture de stock", "indisponible", "épuisé"],
    },
    {
        "name": "Boulanger",
        "url": "https://www.boulanger.com/ref/1216685",
        "in_stock_markers": ["ajouter au panier"],
        "out_of_stock_markers": ["produit indisponible", "rupture de stock"],
    },
    {
        "name": "Darty",
        "url": "https://www.darty.com/nav/achat/gros_electromenager/chauffage_climatisation/climatiseur/midea_mmcs-12hrn8-qrd0.html",
        "in_stock_markers": ["ajouter au panier"],
        "out_of_stock_markers": ["produit indisponible", "rupture de stock"],
    },
    {
        "name": "ManoMano",
        "url": "https://www.manomano.fr/p/midea-climatiseur-split-mobile-reversible-froid-chaud-3500w12000btu-wifi-deshumidificateur-ventilateur-jusqua-40m2-kit-fenetre-inclus-83810402",
        "in_stock_markers": ["ajouter au panier", "en stock"],
        "out_of_stock_markers": ["rupture de stock", "indisponible"],
    },
]

NTFY_TOPIC = os.environ.get("NTFY_TOPIC")
NTFY_SERVER = os.environ.get("NTFY_SERVER", "https://ntfy.sh")


def extract_jsonld_availability(html: str):
    """Cherche un bloc JSON-LD schema.org Product/Offer et renvoie
    (disponibilité, prix) si trouvé."""
    for match in re.finditer(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html,
        re.DOTALL | re.IGNORECASE,
    ):
        raw = match.group(1).strip()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue

        candidates = data if isinstance(data, list) else [data]
        for node in candidates:
            if not isinstance(node, dict):
                continue
            # Parfois le Product est dans "@graph"
            graph = node.get("@graph") if isinstance(node.get("@graph"), list) else [node]
            for item in graph:
                if not isinstance(item, dict):
                    continue
                offers = item.get("offers")
                if isinstance(offers, list):
                    offers = offers[0] if offers else None
                if isinstance(offers, dict):
                    availability = str(offers.get("availability", "")).lower()
                    price = offers.get("price")
                    if "instock" in availability:
                        return "in_stock", price
                    if "outofstock" in availability or "soldout" in availability:
                        return "out_of_stock", price
    return None, None


def detect_status(html: str, site: dict):
    low = html.lower()

    jsonld_status, price = extract_jsonld_availability(html)
    if jsonld_status:
        return jsonld_status, price

    # Fallback texte : priorité au marqueur "rupture" explicite
    for marker in site["out_of_stock_markers"]:
        if marker in low:
            return "out_of_stock", None
    for marker in site["in_stock_markers"]:
        if marker in low:
            return "in_stock", None

    return "unknown", None


def check_site(site: dict):
    try:
        resp = requests.get(site["url"], headers=HEADERS, timeout=20)
        if resp.status_code == 403 or resp.status_code == 503:
            return {"status": "blocked", "price": None, "http_code": resp.status_code}
        resp.raise_for_status()
    except requests.RequestException as exc:
        return {"status": "error", "price": None, "error": str(exc)}

    status, price = detect_status(resp.text, site)
    return {"status": status, "price": price, "http_code": resp.status_code}


def send_ntfy_alert(title: str, message: str, url: str = None):
    if not NTFY_TOPIC:
        print("⚠️  NTFY_TOPIC absent, alerte non envoyée.")
        return
    headers = {
        "Title": title.encode("utf-8"),
        "Priority": "high",
        "Tags": "snowflake",
    }
    if url:
        headers["Click"] = url
    try:
        requests.post(
            f"{NTFY_SERVER}/{NTFY_TOPIC}",
            data=message.encode("utf-8"),
            headers=headers,
            timeout=15,
        )
    except requests.RequestException as exc:
        print(f"Erreur envoi ntfy: {exc}")


def load_previous_status():
    if os.path.exists(STATUS_FILE):
        with open(STATUS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"sites": {}}


def main():
    previous = load_previous_status()
    prev_sites = previous.get("sites", {})

    now = datetime.now(timezone.utc).isoformat()
    result = {"last_checked": now, "sites": {}}

    alerts = []

    for site in SITES:
        check = check_site(site)
        result["sites"][site["name"]] = {
            "url": site["url"],
            "status": check["status"],
            "price": check.get("price"),
            "last_checked": now,
        }

        prev_status = prev_sites.get(site["name"], {}).get("status")
        new_status = check["status"]

        print(f"{site['name']}: {prev_status} -> {new_status}")

        if new_status == "in_stock" and prev_status != "in_stock":
            price_txt = f" à {check['price']} €" if check.get("price") else ""
            alerts.append(
                {
                    "title": f"❄️ PortaSplit en stock chez {site['name']}",
                    "message": f"Disponible{price_txt} — touche pour ouvrir la page.",
                    "url": site["url"],
                }
            )

    for alert in alerts:
        send_ntfy_alert(alert["title"], alert["message"], alert["url"])

    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print("OK — status.json mis à jour.")


if __name__ == "__main__":
    sys.exit(main())
