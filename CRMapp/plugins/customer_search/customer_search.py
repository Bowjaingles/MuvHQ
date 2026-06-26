from flask import Blueprint, render_template, request, current_app
from google_sheets_reader import get_google_sheet
from datetime import datetime
from dateutil.parser import parse as fuzzy_parse


HEADER_ORDER = [
    'Timestamp', 'Referral Source', 'Sign Up Date', 'Name', 'Address', 'Phone', 'Email', 
    'Date of Birth', 'Previous Address', 'Services', 'Water', 'Water Service Start Date', 
    'Electricity', 'Electricity Account', 'Electricity Service Start Date', 'Internet', 
    'Internet Account', 'Internet Service Start Date', 'Mobile', 'Mobile Account', 
    'Mobile Account Start Date', 'Security', 'Serial Number'
]


def fetch_sheet_records(tab_name="CMNH Master"):
    ws = get_google_sheet('CMNH CUSTOMERS + CELL', tab_name)
    try:
        rows = ws.get_all_records()
    except AttributeError:
        rows = list(ws)
    normalized = []
    for r in rows:
        new = {str(k).strip(): v for k, v in r.items()}
        normalized.append(new)
    return normalized


def fuzzy_date(date_str):
    try:
        return fuzzy_parse(date_str, fuzzy=True)
    except (ValueError, TypeError):
        return None


def init_plugin(app):
    bp = Blueprint(
        'customer_search',
        __name__,
        url_prefix='/customer_search',
        template_folder='templates'
    )

    @bp.route('/', methods=['GET', 'POST'])
    def search():
        query = request.form.get('query', '').strip().lower()
        start_date_str = request.form.get('start_date', '').strip()
        end_date_str = request.form.get('end_date', '').strip()

        start_date = fuzzy_date(start_date_str)
        end_date = fuzzy_date(end_date_str)

        raw_records = []

        if request.method == 'POST':
            raw_records = fetch_sheet_records()

        normalized_records = []

        for record in raw_records:
            normalized = {str(k).strip(): v for k, v in record.items()}
            signup_date = fuzzy_date(normalized.get('Sign Up Date'))

            if signup_date:
                if start_date and signup_date < start_date:
                    continue
                if end_date and signup_date > end_date:
                    continue

            normalized_records.append(normalized)

        total = len(normalized_records)

        if query:
            results = [
                r for r in normalized_records
                if any(query in str(v).lower() for v in r.values())
            ]
        else:
            results = normalized_records

        matched = len(results)

        current_app.logger.info(
            f"[customer_search] total={total}, matched={matched}, query='{query}'"
        )

        return render_template(
            'customer_search.html',
            query=query,
            total=total,
            matched=matched,
            results=results,
            headers=HEADER_ORDER,
            start_date=start_date_str,
            end_date=end_date_str
        )

    app.register_blueprint(bp)