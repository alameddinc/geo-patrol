#!/usr/bin/env python3
"""
Mapillary importer — Türkiye için ~1000 sokak konumu çeker.

Kullanım:
  export MAPILLARY_TOKEN="MLY|xx... veya access token"
  python3 mapillary_import.py --target 1000 --per-city 18 [--download] [--pano-only]

Çıktı:
  locations.json        -> [{id, lat, lng, city, img_url, is_pano, captured_at}]
  img/<id>.jpg          -> (--download verilirse) görüntüler
  ATTRIBUTION.txt       -> Mapillary/CC-BY-SA kaynak notu

Not: Mapillary görüntüleri CC-BY-SA. Public kullanımda attribution zorunlu.
"""
import os, sys, json, time, math, argparse, urllib.request, urllib.parse, urllib.error

API = "https://graph.mapillary.com/images"

# İl merkezleri + bazı büyük ilçeler (seed). Yaklaşık koordinat = arama merkezi.
SEED_CITIES = [
    ("İstanbul", 41.0082, 28.9784), ("Kadıköy", 40.9903, 29.0270), ("Beşiktaş", 41.0429, 29.0096),
    ("Ankara", 39.9334, 32.8597), ("İzmir", 38.4237, 27.1428), ("Bursa", 40.1826, 29.0669),
    ("Antalya", 36.8969, 30.7133), ("Adana", 37.0000, 35.3213), ("Konya", 37.8746, 32.4932),
    ("Gaziantep", 37.0662, 37.3833), ("Şanlıurfa", 37.1591, 38.7969), ("Kayseri", 38.7312, 35.4787),
    ("Mersin", 36.8121, 34.6415), ("Eskişehir", 39.7767, 30.5206), ("Diyarbakır", 37.9144, 40.2306),
    ("Samsun", 41.2867, 36.3300), ("Denizli", 37.7765, 29.0864), ("Trabzon", 41.0027, 39.7168),
    ("Malatya", 38.3552, 38.3095), ("Kahramanmaraş", 37.5858, 36.9371), ("Erzurum", 39.9000, 41.2700),
    ("Van", 38.4891, 43.4089), ("Batman", 37.8812, 41.1351), ("Elazığ", 38.6810, 39.2264),
    ("Sivas", 39.7477, 37.0179), ("Manisa", 38.6191, 27.4289), ("Balıkesir", 39.6484, 27.8826),
    ("Tekirdağ", 40.9833, 27.5167), ("Sakarya", 40.7889, 30.4056), ("Kocaeli", 40.8533, 29.8815),
    ("Aydın", 37.8560, 27.8416), ("Muğla", 37.2153, 28.3636), ("Bodrum", 37.0344, 27.4305),
    ("Fethiye", 36.6213, 29.1164), ("Marmaris", 36.8550, 28.2740), ("Çanakkale", 40.1553, 26.4142),
    ("Edirne", 41.6771, 26.5557), ("Kırklareli", 41.7333, 27.2167), ("Bolu", 40.7392, 31.6089),
    ("Zonguldak", 41.4564, 31.7987), ("Kastamonu", 41.3887, 33.7827), ("Çorum", 40.5506, 34.9556),
    ("Amasya", 40.6499, 35.8353), ("Tokat", 40.3167, 36.5500), ("Ordu", 40.9839, 37.8764),
    ("Giresun", 40.9128, 38.3895), ("Rize", 41.0201, 40.5234), ("Artvin", 41.1828, 41.8183),
    ("Kars", 40.6013, 43.0975), ("Ağrı", 39.7191, 43.0503), ("Erzincan", 39.7500, 39.5000),
    ("Bingöl", 38.8853, 40.4989), ("Muş", 38.9462, 41.7539), ("Bitlis", 38.4006, 42.1095),
    ("Siirt", 37.9333, 41.9500), ("Mardin", 37.3212, 40.7245), ("Hakkari", 37.5744, 43.7408),
    ("Şırnak", 37.5164, 42.4611), ("Adıyaman", 37.7648, 38.2786), ("Osmaniye", 37.0682, 36.2614),
    ("Hatay", 36.4018, 36.3498), ("Antakya", 36.2028, 36.1600), ("Kilis", 36.7184, 37.1212),
    ("Nevşehir", 38.6939, 34.6857), ("Ürgüp", 38.6316, 34.9130), ("Niğde", 37.9667, 34.6833),
    ("Aksaray", 38.3687, 34.0370), ("Kırşehir", 39.1425, 34.1709), ("Kırıkkale", 39.8468, 33.5153),
    ("Yozgat", 39.8181, 34.8147), ("Çankırı", 40.6013, 33.6134), ("Karabük", 41.2061, 32.6204),
    ("Bartın", 41.6344, 32.3375), ("Sinop", 42.0231, 35.1531), ("Düzce", 40.8438, 31.1565),
    ("Yalova", 40.6500, 29.2667), ("Bilecik", 40.1506, 29.9792), ("Kütahya", 39.4200, 29.9833),
    ("Afyonkarahisar", 38.7507, 30.5567), ("Uşak", 38.6823, 29.4082), ("Isparta", 37.7648, 30.5566),
    ("Burdur", 37.7203, 30.2908), ("Karaman", 37.1759, 33.2287), ("Tunceli", 39.1079, 39.5401),
    ("Gümüşhane", 40.4602, 39.4813), ("Bayburt", 40.2552, 40.2249), ("Iğdır", 39.9237, 44.0450),
    ("Ardahan", 41.1105, 42.7022), ("Bolu-Abant", 40.6050, 31.2830), ("Safranbolu", 41.2508, 32.6947),
    ("Alanya", 36.5439, 31.9990), ("Side", 36.7673, 31.3890), ("Kuşadası", 37.8600, 27.2597),
    ("Çeşme", 38.3236, 26.3050), ("Ayvalık", 39.3192, 26.6961), ("Göreme", 38.6431, 34.8283),
]

def haversine(a, b):
    R = 6371000.0
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    dla, dlo = la2-la1, lo2-lo1
    h = math.sin(dla/2)**2 + math.cos(la1)*math.cos(la2)*math.sin(dlo/2)**2
    return 2*R*math.asin(math.sqrt(h))

def fetch_city(token, lat, lng, radius_deg=0.045, limit=400, pano_only=False):
    minx, miny, maxx, maxy = lng-radius_deg, lat-radius_deg, lng+radius_deg, lat+radius_deg
    params = {
        "access_token": token,
        "fields": "id,computed_geometry,thumb_1024_url,captured_at,is_pano",
        "bbox": f"{minx},{miny},{maxx},{maxy}",
        "limit": str(limit),
    }
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "geo-patrol-importer/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            data = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        print(f"  ! HTTP {e.code}: {e.read().decode()[:200]}", file=sys.stderr); return []
    except Exception as e:
        print(f"  ! {e}", file=sys.stderr); return []
    out = []
    for it in data.get("data", []):
        g = it.get("computed_geometry") or {}
        c = g.get("coordinates")
        if not c: continue
        if pano_only and not it.get("is_pano"): continue
        out.append({"id": it["id"], "lat": c[1], "lng": c[0],
                    "img_url": it.get("thumb_1024_url"), "is_pano": bool(it.get("is_pano")),
                    "captured_at": it.get("captured_at")})
    return out

def download(url, path):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "geo-patrol-importer/1.0"})
        with urllib.request.urlopen(req, timeout=30) as r, open(path, "wb") as f:
            f.write(r.read())
        return True
    except Exception as e:
        print(f"  ! indirme hata {e}", file=sys.stderr); return False

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=int, default=1000)
    ap.add_argument("--per-city", type=int, default=18)
    ap.add_argument("--min-dist", type=float, default=180.0, help="noktalar arası min metre")
    ap.add_argument("--pano-only", action="store_true")
    ap.add_argument("--download", action="store_true")
    ap.add_argument("--out", default="locations.json")
    args = ap.parse_args()

    token = os.environ.get("MAPILLARY_TOKEN")
    if not token:
        print("HATA: MAPILLARY_TOKEN yok. export MAPILLARY_TOKEN=... ", file=sys.stderr); sys.exit(1)

    picked, all_pts = [], []
    for name, lat, lng in SEED_CITIES:
        if len(picked) >= args.target: break
        cand = fetch_city(token, lat, lng, pano_only=args.pano_only)
        # şehir başına min-mesafe filtresi + cap
        city_pick, kept = 0, []
        for p in sorted(cand, key=lambda x: -(x["is_pano"])):  # pano öncelik
            if city_pick >= args.per_city: break
            pt = (p["lat"], p["lng"])
            if any(haversine(pt, q) < args.min_dist for q in [(k["lat"], k["lng"]) for k in picked+kept]):
                continue
            p["city"] = name; kept.append(p); city_pick += 1
        picked.extend(kept)
        print(f"{name}: +{len(kept)} (toplam {len(picked)})")
        time.sleep(0.25)

    picked = picked[:args.target]
    if args.download:
        os.makedirs("img", exist_ok=True)
        for i, p in enumerate(picked):
            if p.get("img_url") and download(p["img_url"], f"img/{p['id']}.jpg"):
                p["local"] = f"img/{p['id']}.jpg"
            if i % 50 == 0: print(f"  indirildi {i}/{len(picked)}")

    with open(args.out, "w") as f:
        json.dump(picked, f, ensure_ascii=False, indent=1)
    with open("ATTRIBUTION.txt", "w") as f:
        f.write("Görüntüler: Mapillary katkıcıları, CC-BY-SA 4.0.\nKaynak: https://www.mapillary.com\n")
    npano = sum(1 for p in picked if p["is_pano"])
    print(f"\nBİTTİ: {len(picked)} nokta -> {args.out} ({npano} panorama, {len(picked)-npano} düz)")

if __name__ == "__main__":
    main()
