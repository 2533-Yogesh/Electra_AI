import os
import requests
import psycopg2
import hashlib
from flask import Flask, render_template, request, redirect, url_for, session, jsonify

app = Flask(__name__)
app.secret_key = "cspdcl_secret_vault_key"  # Enterprise fallback cryptographic token

# ==============================================================
# ☁️ CLOUD INFRASTRUCTURE: NEON POSTGRESQL CONFIGURATION
# ==============================================================
NEON_CONN_STRING = "postgresql://neondb_owner:npg_Uix1NVbDrPJ4@ep-floral-smoke-apbja9z7-pooler.c-7.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

def get_db_connection():
    return psycopg2.connect(NEON_CONN_STRING)

# ==============================================================
# 🎛️ DATA STREAM EXTRACTION HELPER ENGINE
# ==============================================================
def extract_credentials(req):
    """
    Seamlessly extracts request payloads regardless of content architecture.
    Handles traditional form encoding and modern JavaScript JSON streams.
    """
    if req.is_json:
        data = req.get_json() or {}
        return data.get("username"), data.get("password"), data.get("role")
    else:
        return req.form.get("username"), req.form.get("password"), req.form.get("role")

# ==============================================================
# 🔐 SECURE AUTHENTICATION & IDENTITY PIPELINES
# ==============================================================

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username, password, _ = extract_credentials(request)
        
        if not username or not password:
            return jsonify({"success": False, "message": "Missing username or password variables."}), 400

        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT password_hash, user_role, is_approved FROM system_users WHERE username = %s", (username,))
            user = cur.fetchone()
            cur.close()
            conn.close()
        except Exception as e:
            return jsonify({"success": False, "message": f"Database handshake failed: {str(e)}"}), 500

        if user:
            # 🌟 UNIFIED MATCH: Compute standard SHA-256 hex string to match your database row style
            input_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
            
            if input_hash == user[0]:
                if not user[2]:  # Check administrative is_approved clearance flag
                    return jsonify({"success": False, "message": "Access Denied: Account pending administrator vetting approval."}), 403
                
                session["username"] = username
                session["role"] = user[1]
                return jsonify({"success": True, "redirect": url_for("dashboard")})
        
        # 🟢 FIXED: Safe JSON dictionary return prevents browser token compilation errors
        return jsonify({"success": False, "message": "Invalid username or password credentials."}), 401
        
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username, password, role = extract_credentials(request)
        
        if not username or not password or not role:
            return jsonify({"success": False, "message": "All layout registration fields are mandatory."}), 400

        # 🌟 UNIFIED MATCH: Convert password using identical SHA-256 to fit column constraints securely
        hashed_pw = hashlib.sha256(password.encode('utf-8')).hexdigest()

        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO system_users (username, password_hash, user_role, is_approved) VALUES (%s, %s, %s, FALSE)",
                (username, hashed_pw, role)
            )
            conn.commit()
            cur.close()
            conn.close()
            return jsonify({"success": True, "message": "Account submitted successfully! Awaiting admin activation mapping."})
        except Exception as e:
            return jsonify({"success": False, "message": f"Cloud database insert blocked: {str(e)}"}), 400
            
    return render_template("register.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ==============================================================
# 🧭 DECOUPLED MULTI-PAGE TEMPLATE ROUTING ROUTERS
# ==============================================================

@app.route("/")
def index():
    return redirect(url_for("dashboard"))

@app.route("/dashboard")
def dashboard():
    if "username" not in session: return redirect(url_for("login"))
    return render_template("dashboard.html", username=session["username"], role=session["role"], active_page="dashboard")

@app.route("/forecast")
def forecast():
    if "username" not in session: return redirect(url_for("login"))
    return render_template("forecast.html", username=session["username"], role=session["role"], active_page="forecast")

@app.route("/theft")
def theft():
    if "username" not in session: return redirect(url_for("login"))
    return render_template("theft.html", username=session["username"], role=session["role"], active_page="theft")

@app.route("/evaluation")
def evaluation():
    if "username" not in session: return redirect(url_for("login"))
    return render_template("evaluation.html", username=session["username"], role=session["role"], active_page="evaluation")

# ==============================================================
# 🛡️ ADMINISTRATIVE API VETTING CHANNELS
# ==============================================================

@app.route("/admin/pending_users")
def get_pending_users():
    if session.get("role") != "Admin": return jsonify({"success": False, "message": "Unauthorized scope"}), 403
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, username, user_role FROM system_users WHERE is_approved = FALSE")
    users = [{"id": r[0], "username": r[1], "role": r[2]} for r in cur.fetchall()]
    cur.close()
    conn.close()
    return jsonify({"success": True, "users": users})

@app.route("/admin/approve_user/<int:user_id>", methods=["POST"])
def approve_user(user_id):
    if session.get("role") != "Admin": return jsonify({"success": False, "message": "Unauthorized scope"}), 403
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE system_users SET is_approved = TRUE WHERE id = %s", (user_id,))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"success": True})

# ==============================================================
# 📈 TELEMETRY CORE GATEWAYS: FASTAPI ASYNC NETWORK PIPES
# ==============================================================

@app.route("/portal/forecast_data", methods=["POST"])
def portal_forecast_data():
    if "username" not in session: return jsonify({"status": "unauthorized"}), 401
    
    file = request.files.get("file")
    feeder_id = request.form.get("feeder_id", "")
    dtr_id = request.form.get("dtr_id", "Aggregate Feeder Demand")

    if not file: return jsonify({"status": "error", "message": "Grid spreadsheet streaming empty"}), 400

    # Stream the file buffers safely through system memory over to FastAPI core
    files = {'file': (file.filename, file.read(), file.content_type)}
    params = {'feeder_id': feeder_id, 'dtr_id': dtr_id}
    
    try:
        response = requests.post("http://127.0.0.1:8000/api/v1/demand-forecast", files=files, params=params)
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"status": "error", "message": f"ML Backend Core Communication Fault: {str(e)}"}), 503

@app.route("/portal/theft_data", methods=["POST"])
def portal_theft_data():
    if "username" not in session: return jsonify({"status": "unauthorized"}), 401
    
    file = request.files.get("file")
    if not file: return jsonify({"status": "error", "message": "Grid data sheet invalid"}), 400

    files = {'file': (file.filename, file.read(), file.content_type)}
    
    try:
        response = requests.post("http://127.0.0.1:8000/api/v1/theft-detection", files=files)
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"status": "error", "message": f"ML Backend Core Communication Fault: {str(e)}"}), 503

@app.route("/portal/sync_theft_audit", methods=["POST"])
def sync_theft_audit():
    if "username" not in session:
        return jsonify({"success": False, "message": "Unauthorized session."}), 401
    
    current_user = session["username"]
    payload = request.get_json() or {}
    anomaly_rows = payload.get("anomalies", [])

    if not anomaly_rows:
        return jsonify({"success": False, "message": "No high-risk records available to commit."}), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # 1. Insert into the Manifest Table to log WHO committed this batch
        cur.execute(
            "INSERT INTO theft_upload_manifest (uploaded_by, total_records) VALUES (%s, %s) RETURNING batch_id",
            (current_user, len(anomaly_rows))
        )
        batch_id = cur.fetchone()[0]

        # 2. Bulk insert rows into the audit trail tagged with the current username
        inserted_count = 0
        for row in anomaly_rows:
            # Check for duplicates to prevent clean row collisions
            cur.execute(
                "SELECT 1 FROM theft_audit_trail WHERE consumer_no = %s AND detection_date = %s",
                (str(row.get("Consumer_No")), str(row.get("Date")))
            )
            if not cur.fetchone():
                cur.execute("""
                    INSERT INTO theft_audit_trail 
                    (detection_date, feeder_id, dtr_id, consumer_no, consumption_kwh, risk_score, uploaded_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    str(row.get("Date")),
                    str(row.get("Feeder_ID")),
                    str(row.get("DTR_ID")),
                    str(row.get("Consumer_No")),
                    float(row.get("Consumption_kWh", 0)),
                    float(row.get("Risk_Score", 0)),
                    current_user
                ))
                inserted_count += 1

        conn.commit()
        cur.close()
        conn.close()

        return jsonify({
            "success": True, 
            "message": f"Successfully verified and committed batch #{batch_id}. Saved {inserted_count} new high-risk anomalies.",
            "inserted": inserted_count
        })

    except Exception as e:
        return jsonify({"success": False, "message": f"Neon Transaction Aborted: {str(e)}"}), 500

# ==============================================================
# 🚀 INITIALIZATION DIAGNOSTIC RUNTIME GATE
# ==============================================================
if __name__ == "__main__":
    # Perform cold boot sanity check verification against Neon infrastructure
    try:
        print("⏳ Initiating cold-start credentials trace to Neon Cloud PostgreSQL cluster...")
        db_audit = get_db_connection()
        print("✅ CONNECTION ROOT SECURED: Cloud database cluster online.")
        db_audit.close()
    except Exception as connection_fault:
        print(f"❌ ARCHITECTURAL ERROR: Database handshake failed! Cause: {connection_fault}")
        print("⚠️ Application running on backup mode. Database functions will freeze.")

    app.run(port=5000, debug=True)