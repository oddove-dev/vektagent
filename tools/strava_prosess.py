#!/usr/bin/env python3
"""Lager Strava-datafilene til dashbordet fra rå Strava-svar.

Bruk:  python3 tools/strava_prosess.py <rådatamappe> <utmappe>

Rådatamappen skal inneholde
  aktiviteter.json   – svaret fra Strava list_activities (objekt med "activities", eller en liste),
                       alle aktiviteter fra 2026-10-08
  <id>.json          – svaret fra get_activity_streams med time, distance, altitude, velocity_smooth
                       (enten {"time":[...], ...} eller en liste av {"type":..., "data":[...]})
  <id>.perf.json     – svaret fra get_activity_performance

Utdata: strava_turer.csv og strava_splitter.csv i utmappen.
Regler: bevegelsestid og distanse fra Stravas oppsummering; har turen en bildel (maks fart over 7 m/s),
kuttes strømmen før første sammenhengende parti over 6 m/s og alt regnes fra strømmen.
Splitter per hele km regnes fra strømmen, med «i bevegelse» = fart over 0,8 m/s (treffer Strava-appen).
"""
import csv
import json
import pathlib
import sys

TH_MOV = 0.8
BAKKE = "Hettis_bakke"


def mss(s):
    s = int(round(s))
    if s >= 3600:
        return f"{s // 3600}:{(s % 3600) // 60:02d}:{s % 60:02d}"
    return f"{s // 60}:{s % 60:02d}"


def load_streams(p):
    d = json.loads(p.read_text())
    if isinstance(d, dict) and "streams" in d:
        d = d["streams"]
    if isinstance(d, list):
        d = {x.get("type"): x.get("data") for x in d}
    return d["time"], d["distance"], d.get("altitude") or [0] * len(d["time"]), d["velocity_smooth"]


def mov_cum(t, ds, v):
    c = [0.0]
    for i in range(1, len(t)):
        dt = t[i] - t[i - 1] or 1
        ok = v[i] > TH_MOV or (ds[i] - ds[i - 1]) / dt > TH_MOV
        c.append(c[-1] + (dt if ok else 0))
    return c


def smooth(a, w):
    out = []
    for i in range(len(a)):
        lo, hi = max(0, i - w), min(len(a), i + w + 1)
        out.append(sum(a[lo:hi]) / (hi - lo))
    return out


def gain(a, w=2, thr=1.0):
    s = smooth(a, w)
    g, base = 0.0, s[0]
    for x in s[1:]:
        if x > base + thr:
            g += x - base
            base = x
        elif x < base - thr:
            base = x
    return g


def best(t, ds, L):
    b, j = None, 0
    for i in range(len(t)):
        while j + 1 < i and ds[i] - ds[j + 1] >= L:
            j += 1
        if ds[i] - ds[j] >= L:
            tgt = ds[i] - L
            tk = t[j] + ((tgt - ds[j]) / (ds[j + 1] - ds[j]) * (t[j + 1] - t[j]) if ds[j + 1] > ds[j] else 0)
            el = t[i] - tk
            b = el if b is None or el < b else b
    return b


def cut_car(t, ds, a, v):
    cs = next(i for i in range(len(v)) if v[i] > 6)
    j = cs
    while j > 0 and ds[cs] - ds[j] < 120:
        j -= 1
    plat = ds[j]
    while j > 0 and plat - ds[j - 1] < 1.0:
        j -= 1
    return t[: j + 1], ds[: j + 1], a[: j + 1], v[: j + 1]


def splits(t, ds, a, v):
    mc = mov_cum(t, ds, v)
    sa = smooth(a, 3)

    def at(arr, x):
        for i in range(1, len(ds)):
            if ds[i] >= x:
                if ds[i] == ds[i - 1]:
                    return arr[i]
                f = (x - ds[i - 1]) / (ds[i] - ds[i - 1])
                return arr[i - 1] + f * (arr[i] - arr[i - 1])
        return arr[-1]

    out, k, prev, total = [], 1, 0.0, ds[-1]
    while prev < total - 1:
        nxt = min(k * 1000.0, total)
        if nxt - prev < 50:  # rester under 50 m er støy
            break
        tt = (at(mc, nxt) if nxt < total else mc[-1]) - (at(mc, prev) if prev > 0 else 0)
        dh = (at(sa, nxt) if nxt < total else sa[-1]) - (at(sa, prev) if prev > 0 else sa[0])
        out.append((k, (nxt - prev) / 1000, tt, dh))
        prev, k = nxt, k + 1
    return out


def main(raw, out):
    raw, out = pathlib.Path(raw), pathlib.Path(out)
    acts = json.loads((raw / "aktiviteter.json").read_text())
    acts = acts.get("activities", acts) if isinstance(acts, dict) else acts
    acts = sorted(acts, key=lambda x: x["start_local"])
    tur, spl = [], []
    for act in acts:
        aid, typ, s = str(act["id"]), act["sport_type"], act["summary"]
        if typ not in ("Run", "Walk", "Hike", "TrailRun"):
            continue
        dato, kl = act["start_local"][:10], act["start_local"][11:16]
        perf_p, str_p = raw / f"{aid}.perf.json", raw / f"{aid}.json"
        perf = json.loads(perf_p.read_text()) if perf_p.exists() else {}
        km, mov, hm = s["distance"] / 1000, s["moving_time"], s.get("elevation_gain") or 0
        note = []
        be = {b.get("name"): b.get("value") for b in perf.get("best_efforts", [])}
        b1, b5 = be.get("Fastest1k"), be.get("Fastest5k")
        segs = [x for x in perf.get("segment_efforts", []) if x.get("segment_name") == BAKKE]
        bakke = min((x["moving_time"] for x in segs), default=None)
        streams = load_streams(str_p) if str_p.exists() else None
        if streams and (s.get("max_speed") or 0) > 7:
            t, ds, a, v = cut_car(*streams)
            streams = (t, ds, a, v)
            km, mov, hm = ds[-1] / 1000, mov_cum(t, ds, v)[-1], gain(a)
            b1, b5 = best(t, ds, 1000), best(t, ds, 5000)
            note.append("Bildel fjernet fra registreringen; tall regnet fra løpedelen")
        løp = typ != "Walk"
        tur.append([dato, kl, aid, "Jogging" if løp else "Gåtur", f"{km:.2f}", int(round(mov)), mss(mov),
                    mss(mov / km) if løp else "", round(hm), int(round(b1)) if b1 and løp else "",
                    int(round(b5)) if b5 and løp else "", bakke if løp and bakke else "", "; ".join(note)])
        if løp and streams:
            for k, L, tt, dh in splits(*streams):
                spl.append([dato, aid, k, f"{L:.2f}", int(round(tt)), mss(tt / L), f"{dh:.0f}"])
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "strava_turer.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["dato", "klokkeslett", "id", "type", "km", "tid_s", "tid", "snitt_per_km", "hoydemeter",
                    "raskeste_1k_s", "raskeste_5k_s", "bakke_s", "merknad"])
        w.writerows(tur)
    with open(out / "strava_splitter.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["dato", "id", "km_nr", "km_lengde", "tid_s", "tempo", "hoydeendring_m"])
        w.writerows(spl)
    print(f"strava_turer.csv: {len(tur)} rader, strava_splitter.csv: {len(spl)} rader")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
