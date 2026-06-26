from flask import Blueprint, render_template, request, redirect, send_file, jsonify
import sqlite3
import os
from datetime import datetime
import csv
from .email_templates import get_customer_pitch_email, get_agent_referral_email
import smtplib
from email.mime.text import MIMEText
from flask_login import login_required, current_user

SMTP_SERVER = "smtp.office365.com"
SMTP_PORT = 587
EMAIL_ADDRESS = "info@connectmynewhome.com"
EMAIL_PASSWORD = "Cmnh*987654"

leads_central_bp = Blueprint('leads_central', __name__, template_folder='templates')
DB_FILE = os.path.join(os.path.dirname(__file__), "leads_central.db")

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT,
                business_name TEXT,
                contact_name TEXT,
                contact_info TEXT,
                number TEXT,
                email TEXT,
                notes TEXT,
                timestamp TEXT,
                status TEXT,
                follow_up TEXT,
                created_by TEXT,
                display_order INTEGER DEFAULT 0
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS lead_notes (
                note_id INTEGER PRIMARY KEY AUTOINCREMENT,
                lead_id INTEGER,
                note TEXT,
                timestamp TEXT,
                created_by TEXT,
                FOREIGN KEY (lead_id) REFERENCES leads(id)
            )
        ''')

        # Ensure 'display_order' column exists if table is already created
        try:
            conn.execute("ALTER TABLE leads ADD COLUMN display_order INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass  # Column already exists, ignore the error


@leads_central_bp.route("/", methods=["GET", "POST"])
@login_required
def index():
    if request.method == "POST":
        notes = request.form.get("notes", "").strip()
        if not notes:
            return "You must enter notes before submitting!", 400  # simple error message
        
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute(
                """
                INSERT INTO leads 
                (category, business_name, contact_name, contact_info, number, email, notes, timestamp, status, follow_up, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    request.form["category"],
                    request.form["business_name"],
                    request.form["contact_name"],
                    request.form["contact_info"],
                    request.form["number"],
                    request.form.get("email", ""),
                    notes,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    request.form.get("status", "New Lead"),
                    request.form.get("follow_up", ""),
                    current_user.username
                )
            )
        return redirect("/leads_central/")
    with sqlite3.connect(DB_FILE) as conn:
        leads = conn.execute("SELECT * FROM leads ORDER BY id DESC").fetchall()
    return render_template("leads_central.html", leads=leads, edit_lead=None)

@leads_central_bp.route('/delete/<int:lead_id>', methods=['DELETE'])
def delete_lead(lead_id):
    try:
        # Make sure this path matches your actual Flask app's database location
        db_path = os.path.join(os.path.dirname(__file__), 'leads_central.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Safely delete notes if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='lead_notes';")
        if cursor.fetchone():
            cursor.execute("DELETE FROM lead_notes WHERE lead_id = ?", (lead_id,))

        # Delete the lead itself
        cursor.execute("DELETE FROM leads WHERE id = ?", (lead_id,))

        conn.commit()
        conn.close()

        return jsonify({"success": True})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@leads_central_bp.route("/update_inline/<int:lead_id>", methods=["POST"])
def update_inline(lead_id):
    data = request.json
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute(
            """
            UPDATE leads SET 
                category=?, business_name=?, contact_name=?, email=?, contact_info=?, number=?, status=?, follow_up=?
            WHERE id=?
            """,
            (
                data["category"],
                data["business_name"],
                data["contact_name"],
                data["email"],
                data["contact_info"],
                data["number"],
                data["status"],
                data["follow_up"],
                lead_id
            )
        )
    return jsonify({"success": True})

@leads_central_bp.route("/add_note/<int:lead_id>", methods=["POST"])
@login_required
def add_note(lead_id):
    note_content = request.form["note"]
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute(
            """
            INSERT INTO lead_notes (lead_id, note, timestamp, created_by) VALUES (?, ?, ?, ?)
            """,
            (lead_id, note_content, timestamp, current_user.username)
        )
    return redirect(f"/leads_central/view/{lead_id}")

@leads_central_bp.route("/view/<int:lead_id>")
def view_lead(lead_id):
    with sqlite3.connect(DB_FILE) as conn:
        lead = conn.execute("SELECT * FROM leads WHERE id=?", (lead_id,)).fetchone()
        notes = conn.execute(
            "SELECT * FROM lead_notes WHERE lead_id=? ORDER BY timestamp DESC",
            (lead_id,)
        ).fetchall()
    return render_template("view_lead.html", lead=lead, notes=notes)

@leads_central_bp.route("/export")
def export_csv():
    csv_path = os.path.join(os.path.dirname(__file__), "leads_export.csv")
    with sqlite3.connect(DB_FILE) as conn, open(csv_path, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([
            "ID", "Category", "Business Name", "Contact Name", "Contact Info", "Phone",
            "Email", "Notes", "Timestamp", "Status", "Follow-up Date", "Created By"
        ])
        for row in conn.execute("SELECT * FROM leads"):
            writer.writerow(row)
    return send_file(csv_path, as_attachment=True)

@leads_central_bp.route("/leads_tracker/data")
def tracker_data():
    with sqlite3.connect(DB_FILE) as conn:
        leads = conn.execute("SELECT * FROM leads ORDER BY display_order ASC, id DESC").fetchall()
    return jsonify([
        {
            "id":           lead[0],
            "logged_by":    lead[11],      # <-- new field
            "category":     lead[1],
            "business_name":lead[2],
            "contact_name": lead[3],
            "status":       lead[9],
            "follow_up":    lead[10]
        }
        for lead in leads
    ])

@leads_central_bp.route('/leads_tracker/save_order', methods=['POST'])
@login_required
def save_lead_order():
    ordered_ids = request.json.get('ordered_ids', [])
    try:
        with sqlite3.connect(DB_FILE) as conn:
            for index, lead_id in enumerate(ordered_ids):
                conn.execute("UPDATE leads SET display_order=? WHERE id=?", (index, lead_id))
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@leads_central_bp.route("/generate_email_template", methods=["POST"])
def generate_email_template():
    data = request.json
    category = data.get("category")
    area_code = data.get("area_code")
    if category == "Generic":
        body = get_agent_referral_email()
        subject = "Partner with Connect My New Home!"
    else:
        body = get_customer_pitch_email(category, area_code)
        subject = "Welcome to Connect My New Home!"
    return jsonify({"subject": subject, "body": body})

@leads_central_bp.route("/send_custom_email/<int:lead_id>", methods=["POST"])
@login_required
def send_custom_email(lead_id):
    data = request.json
    subject = data["subject"]
    body = data["body"]
    with sqlite3.connect(DB_FILE) as conn:
        email = conn.execute("SELECT email FROM leads WHERE id=?", (lead_id,)).fetchone()[0]
    result = send_email_to_lead(email, subject, body)
    if result.get("success"):
        note_content = f"📧 Sent Email: '{subject}' to {email}"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute(
                """
                INSERT INTO lead_notes (lead_id, note, timestamp, created_by) VALUES (?, ?, ?, ?)
                """,
                (lead_id, note_content, timestamp, current_user.username)
            )
    return jsonify(result)


def send_email_to_lead(to_email, subject, body):
    msg = MIMEText(body, "plain")
    msg["Subject"] = subject
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = to_email
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)
        return {"success": True, "message": f"{subject} sent successfully!"}
    except Exception as e:
        return {"success": False, "message": str(e)}

def init_plugin(app):
    if not os.path.exists(DB_FILE):
        init_db()
    app.register_blueprint(leads_central_bp, url_prefix="/leads_central")
