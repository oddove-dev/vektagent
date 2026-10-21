#!/usr/bin/env python3
"""Bygger index.html for GitHub Pages fra dashbordets side (fragment.html) og datafilene i data/.

Kjøres av den nattlige oppgaven etter at fragment.html og data/*.csv er hentet fra
Claude-dashbordet «Vektprogrammet». Siden er selvstendig: dataene bakes inn som JSON,
og et lite skall etterligner dashbordets `dash`-API (data, calc, onData, colors).
"""
import datetime
import json
import pathlib
import zoneinfo

ROOT = pathlib.Path(__file__).resolve().parent
DATASETS = ["vekt", "mat", "matkilder", "aktivitet", "livvidde", "blodsukker"]

SHELL = """<!doctype html>
<html lang="nb">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>Vektprogrammet</title>
<style>
:root {
  --color-bg: #f9f9f7; --color-panel: #fcfcfb; --color-fg: #0b0b0b; --color-fg-muted: #52514e;
  --color-border-line: #e1e0d9; --color-ok: #006300; --color-warn: #c98500; --color-bad: #d03b3b;
  --cds-chart-grid: #e1e0d9; --cds-chart-axis: #c3c2b7; --cds-chart-reference: #898781; --cds-chart-muted: #a3a19a;
  --cds-surface-popover: #ffffff; --cds-border: #e1e0d9; --cds-text-secondary: #52514e;
  --cds-shadow-popover: 0 4px 16px rgba(0,0,0,.12);
  --s1: #2a78d6; --s2: #eb6834; --s3: #1baf7a; --s4: #eda100; --s5: #e87ba4; --s6: #008300; --s7: #6250d6; --s8: #e34948;
  --font-anthropic-sans: system-ui, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  --font-anthropic-serif: Georgia, "Times New Roman", serif;
  --cds-font-size-caption: .8125rem; --cds-font-size-body: .9375rem; --cds-font-size-heading: 1.0625rem; --cds-font-size-title: 1.75rem;
  --cds-font-weight-medium: 600;
  --cds-gap-xs: 4px; --cds-gap-sm: 8px; --cds-gap-md: 12px; --cds-gap-xl: 28px;
  --cds-pad-xs: 4px; --cds-pad-sm: 8px; --cds-pad-lg: 16px; --cds-radius: 10px; --cds-dur-slow: 300ms;
}
@media (prefers-color-scheme: dark) {
  :root {
    --color-bg: #0d0d0d; --color-panel: #1a1a19; --color-fg: #f0efec; --color-fg-muted: #c3c2b7;
    --color-border-line: #2c2c2a; --color-ok: #0ca30c; --color-bad: #e66767;
    --cds-chart-grid: #2c2c2a; --cds-chart-axis: #383835; --cds-chart-reference: #898781; --cds-chart-muted: #6e6c66;
    --cds-surface-popover: #232322; --cds-border: #383835; --cds-text-secondary: #c3c2b7;
    --cds-shadow-popover: 0 4px 16px rgba(0,0,0,.5);
    --s1: #3987e5; --s2: #d95926; --s3: #199e70; --s4: #c98500; --s5: #d55181; --s6: #008300; --s7: #9085e9; --s8: #e66767;
  }
}
html { -webkit-text-size-adjust: 100%; }
body { margin: 0; background: var(--color-bg); color: var(--color-fg); font-family: var(--font-anthropic-sans); }
#dash-root { padding: 20px 16px 40px; }
.vp-stamp { max-width: 72rem; margin: 0 auto 12px; font-size: var(--cds-font-size-caption); color: var(--color-fg-muted); }
</style>
<script src="https://cdn.jsdelivr.net/npm/d3@7.9.0/dist/d3.min.js"></script>
<script id="vp-data" type="application/json">__DATA__</script>
<script>
window.dash = (function () {
  var raw = JSON.parse(document.getElementById('vp-data').textContent);
  var sets = {};
  Object.keys(raw).forEach(function (id) {
    var rows = d3.csvParse(raw[id]);
    sets[id] = { status: 'ok', data: rows, rows: rows, columns: rows.columns, meta: [], refreshing: false };
  });
  var calcs = [], cache = {}, fresh = false, fns = [];
  function compute() {
    cache = {};
    calcs.forEach(function (c) {
      try {
        var args = c.inputs.map(function (i) { return (sets[i] || cache[i] || { data: [] }).data; });
        var out = c.fn.apply(null, args);
        cache[c.id] = { status: 'ok', data: out, rows: out, columns: out && out.length ? Object.keys(out[0]) : [], meta: [] };
      } catch (e) {
        console.error('calc ' + c.id, e);
        cache[c.id] = { status: 'error', data: [], rows: [], columns: [], message: String(e) };
      }
    });
    fresh = true;
  }
  function run() { fns.forEach(function (f) { try { f(); } catch (e) { console.error(e); } }); }
  var t;
  window.addEventListener('resize', function () { clearTimeout(t); t = setTimeout(run, 150); });
  document.addEventListener('DOMContentLoaded', run);
  return {
    colors: ['var(--s1)', 'var(--s2)', 'var(--s3)', 'var(--s4)', 'var(--s5)', 'var(--s6)', 'var(--s7)', 'var(--s8)'],
    data: function (id) { if (!fresh) compute(); return sets[id] || cache[id] || { status: 'missing', data: [], rows: [], columns: [] }; },
    calc: function (id, spec) { calcs.push({ id: id, inputs: spec.inputs || [], fn: spec.fn }); fresh = false; },
    onData: function (fn) { fns.push(fn); },
    loader: function () {}, refresh: function () {}, params: function () { return {}; },
    setParams: function () {}, resetParams: function () {}, setLink: function () {}
  };
})();
</script>
</head>
<body>
<div id="dash-root">
<p class="vp-stamp">Sist oppdatert __STAMP__ · oppdateres automatisk hver natt</p>
__FRAGMENT__
</div>
</body>
</html>
"""


# Tilpasninger for den offentlige siden (bestemt 21.10): ingen «glidende snitt»,
# og ingen detaljlister for turer og blodsukker – grafene holder.
PUBLIC_REPLACE = [
    ("Korrigert vekt og glidende snitt", "Vekt og vekttrend"),
    ("Snittet tar de fem siste korrigerte målingene.", "Vekttrenden er snittet av de fem siste målingene."),
    ("Starter i siste glidende snitt", "Starter i siste vekttrend"),
    ("Glidende snitt, målt", "Vekttrend, målt"),
    ("Glidende snitt", "Vekttrend"),
    ("Fem siste korrigerte målinger, per", "Snitt av fem siste målinger, per"),
]
PUBLIC_CSS = """<style>
.vp-card:has(#tur-tabell), .vp-card:has(#bs-tabell), .vp-foot { display: none !important; }
</style>
"""


def public(fragment):
    for old, new in PUBLIC_REPLACE:
        fragment = fragment.replace(old, new)
    return PUBLIC_CSS + fragment


def main():
    fragment = public((ROOT / "fragment.html").read_text(encoding="utf-8"))
    data = {}
    for name in DATASETS:
        p = ROOT / "data" / f"{name}.csv"
        if p.exists():
            data[name] = p.read_text(encoding="utf-8")
    blob = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    now = datetime.datetime.now(zoneinfo.ZoneInfo("Europe/Oslo"))
    stamp = now.strftime("%d.%m.%Y kl. %H:%M")
    html = SHELL.replace("__DATA__", blob).replace("__STAMP__", stamp).replace("__FRAGMENT__", fragment)
    (ROOT / "index.html").write_text(html, encoding="utf-8")
    print(f"index.html bygget ({len(html)} tegn, {len(data)} datakilder, {stamp})")


if __name__ == "__main__":
    main()
