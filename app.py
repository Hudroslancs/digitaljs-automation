from flask import Flask, render_template, jsonify

app = Flask(__name__)

# ── Health check — used by Docker and load balancers ─────────────────────────
@app.route("/health")
def health():
    return jsonify({"status": "ok"}), 200

# ── Basic Prometheus metrics (no extra library needed for now) ────────────────
# Later: swap this with flask_prometheus_metrics for real counters/histograms
@app.route("/metrics")
def metrics():
    return "# HELP up App is up\n# TYPE up gauge\nup 1\n", 200, {
        "Content-Type": "text/plain; charset=utf-8"
    }

# ── App routes ────────────────────────────────────────────────────────────────
@app.route("/")
def home():
    return "Try,test,tengok!"

@app.route("/create")
def create_jobsheet():
    return render_template("create_jobsheet.html")


if __name__ == "__main__":
    # Only used locally — in Docker we use Gunicorn
    app.run(debug=True, host="0.0.0.0", port=5000)
