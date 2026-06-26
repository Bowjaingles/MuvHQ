# plugins/referral_agent_tracker_and_leads/referral_agent_tracker_and_leads.py
from flask import Blueprint, render_template, request
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import time
import re

referral_tracker_bp = Blueprint(
    'referral_agent_tracker', __name__, template_folder='templates'
)

# ---- Config ----
SHEET_NAME = 'REFERRALS 2024 & 2025***'

# Fixed card order (extras append alphabetically)
TABS_ORDER = [
    'JWC', 'AJRE', 'MORRIS', 'BWR', 'CTX',
    'HOME TEAM', 'LINNEMANN', 'SHINE', 'EVERYDAY RENTALS',
    'MCG', 'ELISHA', 'EARL', 'SOPHIA', 'WEICHERT', 'RAY', 'ARRI', 'AD ASSETS',
    'HOME ROCK', 'GOOGLE', 'MALL', 'OTHER'
]

# Keep Security in data so we don't break, but we won't render it.
UNIFIED_KEYS = [
    'Date', 'Referral', 'Customer', 'Services',
    'Electricity', 'Internet', 'Mobile', 'Security'
]

GC_SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]
CACHE_TTL   = 90
PREVIEW_ROWS = 6

# ---- Caches ----
_gc = None
_ss = None
TAB_CACHE  = {}                 # { tab: {"ts": float, "data": list[dict]} }
TABS_CACHE = {"ts": 0.0, "tabs": []}

# ---- gspread helpers ----
def get_spreadsheet():
    global _gc, _ss
    if _ss is not None:
        return _ss
    creds = Credentials.from_service_account_file(
        'referralsearchapp-66acbc64e9b3.json', scopes=GC_SCOPES
    )
    _gc = gspread.authorize(creds)
    _ss = _gc.open(SHEET_NAME)
    return _ss

def list_tabs(force=False):
    now = time.time()
    if not force and TABS_CACHE["tabs"] and (now - TABS_CACHE["ts"] < CACHE_TTL):
        return TABS_CACHE["tabs"]
    ss = get_spreadsheet()
    titles = [ws.title for ws in ss.worksheets()]
    ordered = [t for t in TABS_ORDER if t in titles]
    extras  = sorted([t for t in titles if t not in TABS_ORDER])
    final   = ordered + extras
    TABS_CACHE.update({"ts": now, "tabs": final})
    return final

def get_sheet_data(tab_name):
    now = time.time()
    cached = TAB_CACHE.get(tab_name)
    if cached and (now - cached["ts"] < CACHE_TTL):
        return cached["data"]
    ws = get_spreadsheet().worksheet(tab_name)
    data = ws.get_all_records()
    TAB_CACHE[tab_name] = {"ts": now, "data": data}
    return data

# ---- parsing/formatting ----
def parse_date(date_str):
    if not date_str:
        return None
    if isinstance(date_str, datetime):
        return date_str
    s = str(date_str).strip()
    for fmt in ('%Y-%m-%d', '%m/%d/%Y', '%m/%d/%y'):
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            pass
    return None

def format_date_out(val):
    dt = parse_date(val)
    return dt.strftime('%Y-%m-%d') if dt else ('' if val is None else str(val))

PHONE_RX = re.compile(r'\+?1?[\s\-\.]?\(?\d{3}\)?[\s\-\.]?\d{3}[\s\-\.]?\d{4}')
PAREN_DIGITS_RX = re.compile(r'\(\s*[\d\-\s\.]+\s*\)')

def strip_phone(text):
    """Remove phone-like bits for compact display pills / provider normalization."""
    if not text:
        return ''
    t = str(text)
    t = PHONE_RX.sub('', t)
    t = PAREN_DIGITS_RX.sub('', t)
    t = re.sub(r'\s{2,}', ' ', t).strip(' ,;|-')
    return t.strip()

def normalize_entry(raw):
    """Normalize to unified keys + add *_display (no phone) + format Date."""
    normalized = {
        'Date':        raw.get('Date') or raw.get('Date Submitted') or raw.get('Submission Date') or '',
        'Referral':    raw.get('Referral') or raw.get('Referral Source') or '',
        'Customer':    raw.get('Customer') or raw.get('Name') or '',
        'Services':    raw.get('Services') or raw.get('Service Type') or '',
        'Electricity': raw.get('Electricity', ''),
        'Internet':    raw.get('Internet', ''),
        'Mobile':      raw.get('Mobile', ''),
        'Security':    raw.get('Security', ''),
    }
    normalized['Date'] = format_date_out(normalized['Date'])
    for k in ('Electricity', 'Internet', 'Mobile', 'Security'):
        normalized[f'{k}_display'] = strip_phone(normalized.get(k, ''))

    ordered = {k: normalized.get(k, '') for k in UNIFIED_KEYS}
    for k in ('Electricity', 'Internet', 'Mobile', 'Security'):
        ordered[f'{k}_display'] = normalized.get(f'{k}_display', '')
    return ordered

def slugify_tab(title: str) -> str:
    return re.sub(r'[^a-z0-9]+', '_', str(title).lower()).strip('_') or 'tab'

# ---- stats helpers (since date) ----
def compute_stats_since(rows_sorted, since_dt):
    """Counts Water/Elec/Net/Mobile since since_dt inclusive (lists are unaffected)."""
    def _has(v): return bool(str(v or '').strip())
    elec = net = mobile = water = 0
    for r in rows_sorted:
        dt = parse_date(r.get('Date'))
        if not dt or (since_dt and dt < since_dt):
            continue
        if _has(r.get('Electricity')): elec += 1
        if _has(r.get('Internet')):    net  += 1
        if _has(r.get('Mobile')):      mobile += 1
        if 'water' in str(r.get('Services','')).lower(): water += 1
    return {'water': water, 'elec': elec, 'net': net, 'mobile': mobile}

def _provider_key(text: str) -> str:
    return strip_phone(text or '').strip().lower()

def _provider_display(key_lower: str) -> str:
    k = (key_lower or '').strip()
    if k in ('att', 'at&t', 'at and t', 'at t'): return 'AT&T'
    if k in ('txu', 'txu energy'):               return 'TXU Energy'
    return k.title()

def compute_provider_counts_since(rows_sorted, since_dt):
    """Per-service provider counts (Electricity/Internet/Mobile) since since_dt inclusive."""
    buckets = {'Electricity': {}, 'Internet': {}, 'Mobile': {}}
    for r in rows_sorted:
        dt = parse_date(r.get('Date'))
        if since_dt and (not dt or dt < since_dt):
            continue
        for col in ('Electricity', 'Internet', 'Mobile'):
            raw = r.get(col) or r.get(f'{col}_display') or ''
            key = _provider_key(raw)
            if not key:
                continue
            buckets[col][key] = buckets[col].get(key, 0) + 1

    out = {}
    for col, d in buckets.items():
        items = sorted(d.items(), key=lambda kv: (-kv[1], kv[0]))
        out[col] = [{'name': _provider_display(k), 'count': v} for k, v in items]
    return out

def first_of_month_str():
    now = datetime.now()
    return now.replace(day=1).strftime('%Y-%m-%d')

# ---- Route: always-on grid, lists ALL rows; stats & provider counts since per-tab date ----
@referral_tracker_bp.route('/referral_agent_tracker', methods=['GET'])
def referral_agent_tracker():
    tabs = list_tabs()

    # read per-tab stats dates from query (e.g., ?since_jwc=YYYY-MM-DD); default MTD
    stats_dates = {}
    for t in tabs:
        slug = slugify_tab(t)
        raw = (request.args.get(f'since_{slug}') or '').strip()
        if raw and parse_date(raw):
            stats_dates[slug] = raw
        else:
            stats_dates[slug] = first_of_month_str()

    cards = []
    for tab in tabs:
        try:
            raw = get_sheet_data(tab)
        except Exception:
            continue

        rows = [normalize_entry(x) for x in raw]
        rows_sorted = sorted(
            rows, key=lambda r: (parse_date(r.get('Date')) or datetime.min), reverse=True
        )

        slug = slugify_tab(tab)
        since_str = stats_dates.get(slug, first_of_month_str())
        since_dt  = parse_date(since_str)

        stats     = compute_stats_since(rows_sorted, since_dt)
        providers = compute_provider_counts_since(rows_sorted, since_dt)

        cards.append({
            "tab": tab,
            "slug": slug,
            "total": len(rows_sorted),                                  # lists = ALL rows
            "last_date": rows_sorted[0].get('Date', '') if rows_sorted else '',
            "preview": rows_sorted[:PREVIEW_ROWS],
            "all_rows": rows_sorted,
            "stats": stats,                                              # counts since date
            "provider_counts": providers,                                # per-service providers since date
            "stats_since_ui": since_str,                                 # inline date value
        })

    # pass current per-tab dates so each form preserves others
    return render_template('referral_agent_tracker.html',
                           cards=cards,
                           headers=UNIFIED_KEYS,
                           stats_dates=stats_dates)

def init_plugin(app):
    app.register_blueprint(referral_tracker_bp)
