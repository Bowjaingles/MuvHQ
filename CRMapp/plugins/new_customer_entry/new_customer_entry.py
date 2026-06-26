from flask import Blueprint, render_template, request, jsonify, current_app
import gspread
from google.oauth2.service_account import Credentials
from gspread.exceptions import WorksheetNotFound
from flask_mail import Mail, Message
from flask_login import login_required
from datetime import datetime
import re

new_customer_entry_bp = Blueprint(
    'new_customer_entry', __name__,
    static_folder='static',
    template_folder='templates'
)

def get_google_sheet():
    creds = Credentials.from_service_account_file(
        'referralsearchapp-66acbc64e9b3.json',
        scopes=[
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
    )
    client = gspread.authorize(creds)
    return client.open('CMNH CUSTOMERS + CELL').worksheet('CMNH Master')


def get_referrals_workbook():
    creds = Credentials.from_service_account_file(
        'referralsearchapp-66acbc64e9b3.json',
        scopes=[
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
    )
    client = gspread.authorize(creds)
    return client.open('REFERRALS 2024 & 2025***')


def _norm_phone(s: str) -> str:
    return re.sub(r"\D+", "", (s or ""))


def _tab_for_source(source):
    tab_map = {
        'linnemann': 'LINNEMANN',
        'jwc': 'JWC',
        'home team': 'HOME TEAM',
        'morris': 'MORRIS',
        'shine': 'SHINE',
        'bwr': 'BWR',
        'everyday rentals': 'EVERYDAY RENTALS',
        'home rock': 'HOME ROCK',
        'ajre': 'AJRE',
        'google': 'GOOGLE',
        'ctx': 'CTX',
        'mall': 'MALL',
        'return': 'RETURN',
        'mcg': 'MCG',
        'elisha': 'ELISHA',
        'earl': 'EARL',
        'sophia': 'SOPHIA',
        'weichart': 'WEICHART',
        'ray': 'RAY',
        'arri': 'ARRI',
        'ad assets': 'AD ASSETS',
        'other': 'OTHER'
    }
    return tab_map.get((source or '').strip().lower(), 'OTHER')


def update_referrals(source, name, services, signup_date, email, force_append=False):
    referrals_wb = get_referrals_workbook()
    title = _tab_for_source(source)

    try:
        ws = referrals_wb.worksheet(title)
    except WorksheetNotFound:
        ws = referrals_wb.worksheet('OTHER')

    summary_rows = ws.get_all_values()

    summary_index = next(
        (
            i for i, row in enumerate(summary_rows, 1)
            if len(row) > 2 and (row[2] or '').strip().lower() == (name or '').strip().lower()
        ),
        None
    )

    src_ws = get_google_sheet()
    src_records = src_ws.get_all_values()

    src_index = None
    for i, row in enumerate(src_records, 1):
        if len(row) > 6 and (row[6] or '').strip().lower() == (email or '').strip().lower():
            src_index = i

    elec = internet = mobile = ''

    if src_index:
        elec = src_ws.cell(src_index, 13).value or ''
        internet = src_ws.cell(src_index, 16).value or ''
        mobile = src_ws.cell(src_index, 19).value or ''

    if summary_index and not force_append:
        ws.update_cell(summary_index, 1, signup_date)
        ws.update_cell(summary_index, 4, services)
        ws.update_cell(summary_index, 5, elec)
        ws.update_cell(summary_index, 6, internet)
        ws.update_cell(summary_index, 7, mobile)
    else:
        ws.append_row([signup_date, source, name, services, elec, internet, mobile])


def update_referrals_provider(providers, customer_info):
    referrals_wb = get_referrals_workbook()
    source = (customer_info or {}).get('referral_source', '')
    title = _tab_for_source(source)

    try:
        ws = referrals_wb.worksheet(title)
    except WorksheetNotFound:
        ws = referrals_wb.worksheet('OTHER')

    records = ws.get_all_values()

    customer_name = (customer_info.get('customer_name', '') or '').strip().lower()
    signup_date = (customer_info.get('signup_date', '') or '').strip()
    action = (customer_info.get('action', '') or '').strip()

    row_index = None

    if action == 'new_address':
        for i, row in enumerate(records, 1):
            row_signup_date = (row[0] if len(row) > 0 else '').strip()
            row_name = (row[2] if len(row) > 2 else '').strip().lower()

            if row_name == customer_name and row_signup_date == signup_date:
                row_index = i

    if not row_index:
        for i, row in enumerate(records, 1):
            row_name = (row[2] if len(row) > 2 else '').strip().lower()

            if row_name == customer_name:
                row_index = i

    col_map = {
        'Electricity': 5,
        'Internet': 6,
        'Mobile': 7
    }

    if row_index:
        for p in providers or []:
            col = col_map.get(p.get('service'))
            if col:
                ws.update_cell(row_index, col, p.get('provider', ''))


def build_customer_row(data):
    timestamp = datetime.now().strftime('%I:%M:%S %p %m/%d/%Y')
    email = (data.get('email', '') or '').strip().lower()

    row_data = [
        timestamp,
        data.get('referral_source', ''),
        data.get('signup_date', ''),
        data.get('customer_name', ''),
        data.get('address', ''),
        data.get('phone', ''),
        email,
        data.get('date_of_birth', ''),
        data.get('previous_address', ''),
        data.get('services', '')
    ]

    row_data += [''] * 13
    return row_data


def find_existing_customer_row(records, data):
    email = (data.get('email', '') or '').strip().lower()
    phone = _norm_phone(data.get('phone', '') or '')
    name = (data.get('customer_name', '') or '').strip().lower()

    for i, row in enumerate(records, 1):
        row_email = ((row[6] if len(row) > 6 else '') or '').strip().lower()
        row_phone = _norm_phone((row[5] if len(row) > 5 else '') or '')
        row_name = ((row[3] if len(row) > 3 else '') or '').strip().lower()

        if email and row_email == email:
            return i

        if phone and row_phone == phone:
            return i

        if name and row_name == name:
            return i

    return None


@new_customer_entry_bp.route('/customer_lookup', methods=['GET'])
@login_required
def customer_lookup():
    email = (request.args.get('email') or '').strip().lower()
    phone = _norm_phone(request.args.get('phone') or '')
    name = (request.args.get('name') or '').strip().lower()

    if not (email or phone or name):
        return jsonify({"error": "email or phone or name is required"}), 400

    ws = get_google_sheet()
    rows = ws.get_all_values()

    matches = []

    for i, row in enumerate(rows, 1):
        row_email = ((row[6] if len(row) > 6 else '') or '').strip().lower()
        row_phone = _norm_phone((row[5] if len(row) > 5 else '') or '')
        row_name = ((row[3] if len(row) > 3 else '') or '').strip().lower()

        if (
            (email and row_email == email)
            or (phone and row_phone == phone)
            or (name and row_name == name)
        ):
            matches.append({
                "row_index": i,
                "customer": {
                    "timestamp": row[0] if len(row) > 0 else "",
                    "referral_source": row[1] if len(row) > 1 else "",
                    "signup_date": row[2] if len(row) > 2 else "",
                    "customer_name": row[3] if len(row) > 3 else "",
                    "address": row[4] if len(row) > 4 else "",
                    "phone": row[5] if len(row) > 5 else "",
                    "email": row[6] if len(row) > 6 else "",
                    "date_of_birth": row[7] if len(row) > 7 else "",
                    "previous_address": row[8] if len(row) > 8 else "",
                    "services": row[9] if len(row) > 9 else ""
                }
            })

    if not matches:
        return jsonify({"error": "not found"}), 404

    return jsonify({"matches": matches})


@new_customer_entry_bp.route('/new_customer', methods=['GET'])
@login_required
def new_customer():
    return render_template('new_customer_entry.html')


@new_customer_entry_bp.route('/submit_customer', methods=['POST'])
@login_required
def submit_customer():
    data = request.json or {}
    action = data.get('action', '')

    sheet = get_google_sheet()
    records = sheet.get_all_values()

    idx_existing = find_existing_customer_row(records, data)

    if idx_existing and not action:
        return jsonify({
            'status': 'existing_customer_found',
            'message': 'Existing customer found.',
            'row_index': idx_existing
        })

    row_data = build_customer_row(data)

    email = (data.get('email', '') or '').strip().lower()
    services = data.get('services', '')
    name = (data.get('customer_name', '') or '').strip()
    signup_date = data.get('signup_date', '')

    if idx_existing and action == 'update_existing':
        for col_num, value in enumerate(row_data, start=1):
            sheet.update_cell(idx_existing, col_num, value)

        update_referrals(
            data.get('referral_source', ''),
            name,
            services,
            signup_date,
            email,
            force_append=False
        )

        return jsonify({
            'status': 'success',
            'message': 'Existing customer updated.',
            'row_index': idx_existing
        })

    sheet.append_row(row_data)
    idx_new = len(sheet.get_all_values())

    update_referrals(
        data.get('referral_source', ''),
        name,
        services,
        signup_date,
        email,
        force_append=(action == 'new_address')
    )

    return jsonify({
        'status': 'success',
        'message': 'New customer entry added.',
        'row_index': idx_new
    })


@new_customer_entry_bp.route('/submit_provider', methods=['POST'])
@login_required
def submit_provider():
    data = request.json or {}
    providers = data.get('providers', [])
    email = (data.get('email', '') or '').strip().lower()
    customer_info = data.get('customer_info', {}) or {}

    sheet = get_google_sheet()
    records = sheet.get_all_values()

    row_index = data.get('row_index')

    if row_index:
        try:
            target_row = int(row_index)
        except ValueError:
            target_row = None
    else:
        target_row = None

    if not target_row:
        target_row = next(
            (
                i for i, row in enumerate(records, start=1)
                if len(row) > 6 and (row[6] or '').strip().lower() == email
            ),
            None
        )

    if not target_row:
        return jsonify({
            "status": "error",
            "message": "Could not find customer row for provider details."
        }), 400

    cols_map = {
        'Water': {
            'provider': 11,
            'start_date': 12
        },
        'Electricity': {
            'provider': 13,
            'account_number': 14,
            'start_date': 15
        },
        'Internet': {
            'provider': 16,
            'account_number': 17,
            'start_date': 18
        },
        'Mobile': {
            'provider': 19,
            'account_number': 20,
            'start_date': 21,
            'serial_number': 23
        },
        'Home Security': {
            'provider': 22
        },
        'Security': {
            'provider': 22
        }
    }

    for p in providers:
        service = p.get('service')
        cols = cols_map.get(service)

        if not cols:
            continue

        if 'provider' in cols:
            sheet.update_cell(target_row, cols['provider'], p.get('provider', ''))

        if 'account_number' in cols:
            sheet.update_cell(target_row, cols['account_number'], p.get('account_number', ''))

        if 'start_date' in cols:
            sheet.update_cell(target_row, cols['start_date'], p.get('start_date', ''))

        if 'serial_number' in cols:
            sheet.update_cell(target_row, cols['serial_number'], p.get('serial_number', ''))

    update_referrals_provider(providers, customer_info)

    email_body = f"""
    <html>
    <body style="font-family:Arial,sans-serif;line-height:1.6;">
        <h2 style="color:#4CAF50;">Thank You for Signing Up!</h2>
        <p>We appreciate you allowing us the opportunity to help you save time and money connecting your utilities. Enjoy your new home!</p>

        <h3 style="border-bottom:1px solid #ccc;">Customer Information</h3>
        <p><strong>Sign Up Date:</strong> {customer_info.get('signup_date','')}<br>
        <strong>Customer Name:</strong> {customer_info.get('customer_name','')}<br>
        <strong>Address:</strong> {customer_info.get('address','')}<br>
        <strong>Phone Number:</strong> {customer_info.get('phone','')}<br>
        <strong>Email Address:</strong> {email}<br>
        <strong>Services:</strong> {customer_info.get('services','')}</p>

        <h3 style="border-bottom:1px solid #ccc;">Provider Details</h3>
        {''.join([
            "<p><strong>{svc} Provider:</strong> {prov}<br>{acct}{start}{serial}</p>".format(
                svc=(p.get('service','')),
                prov=(p.get('provider','')),
                acct=(f"<strong>{p.get('service','')} Account #:</strong> {p.get('account_number','')}<br>" if p.get('account_number') else ''),
                start=(f"<strong>{p.get('service','')} Service Start Date:</strong> {p.get('start_date','')}<br>" if p.get('start_date') else ''),
                serial=(f"<strong>Serial Number:</strong> {p.get('serial_number','')}<br>" if (p.get('service')=='Mobile' and p.get('serial_number')) else '')
            )
            for p in (providers or [])
        ])}

        <p style="color:#4CAF50;">If any of the above information is incorrect, please let us know right away.<br>
        (254)300-9800 or (361)210-8800</p>

        <p>Best regards,<br>
        <strong>Connect My New Home Team</strong></p>
    </body>
    </html>
    """

    email_sent = True
    email_error = ""

    try:
        msg = Message(
            "Thank You for Signing Up - Connect My New Home",
            sender='info@connectmynewhome.com',
            recipients=[email],
            html=email_body
        )
        current_app.extensions['mail'].send(msg)
    except Exception as e:
        email_sent = False
        email_error = str(e)
        current_app.logger.exception("Provider details saved, but confirmation email failed.")

    return jsonify({
        "status": "success",
        "message": "Provider details saved." if not email_sent else "Provider details saved and email sent.",
        "email_sent": email_sent,
        "email_error": email_error
    })


def init_plugin(app):
    app.config['MAIL_SERVER'] = 'smtp.office365.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = 'info@connectmynewhome.com'
    app.config['MAIL_PASSWORD'] = 'Cmnh*987654'

    mail = Mail(app)
    app.mail = mail
    app.register_blueprint(new_customer_entry_bp)