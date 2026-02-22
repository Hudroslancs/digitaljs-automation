from flask import Flask, render_template, request, jsonify
import psycopg2
import psycopg2.extras
import os
import json
import requests
from datetime import datetime

app = Flask(__name__)

# ── Database connection ───────────────────────────────────────────────────────
def get_db():
    return psycopg2.connect(
        host=os.environ.get("DB_HOST"),
        dbname=os.environ.get("DB_NAME", "jobsheet"),
        user=os.environ.get("DB_USER", "postgres"),
        password=os.environ.get("DB_PASSWORD"),
        port=5432,
        sslmode="require"
    )

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS jobsheets (
            id SERIAL PRIMARY KEY,
            js_number INTEGER UNIQUE NOT NULL,
            status VARCHAR(20) DEFAULT 'draft',
            acc_no VARCHAR(50),
            client_name VARCHAR(200),
            address TEXT,
            contacts VARCHAR(200),
            date_issued VARCHAR(50),
            app_date_time VARCHAR(100),
            date_purchased VARCHAR(50),
            warranty VARCHAR(10),
            brand_model TEXT,
            serial_no TEXT,
            service_request TEXT,
            service_report TEXT,
            service_types TEXT,
            service_others_text VARCHAR(200),
            parts TEXT,
            service_charge NUMERIC(10,2),
            grand_total NUMERIC(10,2),
            payment_terms VARCHAR(100),
            job_completed BOOLEAN DEFAULT FALSE,
            job_follow_up BOOLEAN DEFAULT FALSE,
            job_issue_quotation BOOLEAN DEFAULT FALSE,
            job_unit_returned BOOLEAN DEFAULT FALSE,
            date VARCHAR(50),
            time_in VARCHAR(50),
            time_out VARCHAR(50),
            signature TEXT,
            created_at TIMESTAMP DEFAULT NOW(),
            submitted_at TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS js_counter (
            id INTEGER PRIMARY KEY DEFAULT 1,
            last_number INTEGER DEFAULT 199999
        );

        INSERT INTO js_counter (id, last_number)
        VALUES (1, 199999)
        ON CONFLICT (id) DO NOTHING;
    """)
    conn.commit()
    cur.close()
    conn.close()

# ── Health & metrics ──────────────────────────────────────────────────────────
@app.route("/health")
def health():
    return jsonify({"status": "ok"}), 200

@app.route("/metrics")
def metrics():
    return "# HELP up App is up\n# TYPE up gauge\nup 1\n", 200, {
        "Content-Type": "text/plain; charset=utf-8"
    }

# ── Home: list all jobsheets ──────────────────────────────────────────────────
@app.route("/")
def home():
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT js_number, status, client_name, acc_no, date_issued, created_at
        FROM jobsheets ORDER BY js_number DESC
    """)
    jobsheets = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("index.html", jobsheets=jobsheets)

# ── Create new jobsheet ───────────────────────────────────────────────────────
@app.route("/create")
def create_jobsheet():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        UPDATE js_counter SET last_number = last_number + 1
        WHERE id = 1 RETURNING last_number
    """)
    js_number = cur.fetchone()[0]
    cur.execute("""
        INSERT INTO jobsheets (js_number, status)
        VALUES (%s, 'draft') ON CONFLICT (js_number) DO NOTHING
    """, (js_number,))
    conn.commit()
    cur.close()
    conn.close()
    return render_template("create_jobsheet.html", js_number=js_number, jobsheet=None)

# ── Open existing jobsheet ────────────────────────────────────────────────────
@app.route("/jobsheet/<int:js_number>")
def view_jobsheet(js_number):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM jobsheets WHERE js_number = %s", (js_number,))
    jobsheet = cur.fetchone()
    cur.close()
    conn.close()
    if not jobsheet:
        return "Jobsheet not found", 404
    return render_template("create_jobsheet.html", js_number=js_number, jobsheet=dict(jobsheet))

# ── Save draft ────────────────────────────────────────────────────────────────
@app.route("/api/save", methods=["POST"])
def save_draft():
    data = request.json
    js_number = data.get("js_number")
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        UPDATE jobsheets SET
            acc_no=%s, client_name=%s, address=%s, contacts=%s,
            date_issued=%s, app_date_time=%s, date_purchased=%s, warranty=%s,
            brand_model=%s, serial_no=%s,
            service_request=%s, service_report=%s,
            service_types=%s, service_others_text=%s,
            parts=%s, service_charge=%s, grand_total=%s, payment_terms=%s,
            job_completed=%s, job_follow_up=%s, job_issue_quotation=%s, job_unit_returned=%s,
            date=%s, time_in=%s, time_out=%s, signature=%s
        WHERE js_number=%s
    """, (
        data.get("acc_no"), data.get("client_name"), data.get("address"), data.get("contacts"),
        data.get("date_issued"), data.get("app_date_time"), data.get("date_purchased"), data.get("warranty"),
        data.get("brand_model"), data.get("serial_no"),
        data.get("service_request"), data.get("service_report"),
        json.dumps(data.get("service_types", [])), data.get("service_others_text"),
        json.dumps(data.get("parts", [])),
        data.get("service_charge") or None, data.get("grand_total") or None,
        data.get("payment_terms"),
        data.get("job_completed", False), data.get("job_follow_up", False),
        data.get("job_issue_quotation", False), data.get("job_unit_returned", False),
        data.get("date"), data.get("time_in"), data.get("time_out"), data.get("signature"),
        js_number
    ))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"status": "saved"})

# ── Print: save + mark printed ────────────────────────────────────────────────
@app.route("/api/print/<int:js_number>", methods=["POST"])
def mark_printed(js_number):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE jobsheets SET status='printed' WHERE js_number=%s", (js_number,))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"status": "printed"})

# ── Submit: complete + trigger n8n ────────────────────────────────────────────
@app.route("/api/submit/<int:js_number>", methods=["POST"])
def submit_jobsheet(js_number):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        UPDATE jobsheets SET status='submitted', submitted_at=NOW()
        WHERE js_number=%s RETURNING *
    """, (js_number,))
    jobsheet = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()

    n8n_webhook = os.environ.get("N8N_WEBHOOK_URL")
    if n8n_webhook and jobsheet:
        try:
            payload = {k: str(v) if v is not None else "" for k, v in dict(jobsheet).items()}
            requests.post(n8n_webhook, json=payload, timeout=5)
        except Exception as e:
            print(f"n8n webhook error: {e}")

    return jsonify({"status": "submitted", "js_number": js_number})

# ── Get jobsheet data (API) ───────────────────────────────────────────────────
@app.route("/api/jobsheet/<int:js_number>")
def get_jobsheet(js_number):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM jobsheets WHERE js_number=%s", (js_number,))
    jobsheet = cur.fetchone()
    cur.close()
    conn.close()
    if not jobsheet:
        return jsonify({"error": "not found"}), 404
    return jsonify({k: str(v) if v is not None else "" for k, v in dict(jobsheet).items()})

if __name__ == "__main__":
    init_db()
    app.run(debug=True, host="0.0.0.0", port=5000)
