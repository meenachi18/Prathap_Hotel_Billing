import json
import sqlite3
from datetime import datetime
from pathlib import Path
from flask import Flask, jsonify, render_template, request
from werkzeug.utils import secure_filename

APP_DIR = Path(__file__).resolve().parent
DB_PATH = APP_DIR / "hotel_billing.db"
SETTINGS_PATH = APP_DIR / "settings.json"
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024  # 8 MB per image
UPLOAD_DIR = APP_DIR / "static" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}

DEFAULT_MENU = [ 
    ("Porata", 20, "Porata", "/static/images/porata.jpeg"),
    ("Ghee Porata", 40, "Porata", "/static/images/ghee porata.jpeg"),
    ("Egg Kuttu Porata", 80, "Porata", "/static/images/egg porata.jpeg"),
    ("Chicken Kuttu Porata", 100, "Porata", "/static/images/chicken kothu porata.jpeg"),
    ("Dosa", 40, "Tiffin", "/static/images/dosai.jpeg"),
    ("Egg Dosa", 60, "Tiffin", "/static/images/egg dosai.jpeg"),
    ("Onion Dosa", 60, "Tiffin", "/static/images/onion dosai.jpeg"),
    ("Podi Dosa", 50, "Tiffin", "/static/images/podi dosai.jpeg"),
    ("Kuska", 40, "Rice", "/static/images/kuska.jpeg"),
    ("Egg Kuska", 50, "Rice", "/static/images/egg kuska.jpeg"),
    ("Meals (Non-veg & Veg)", 90, "Meals", "/static/images/full mealss.jpeg"),
    ("Half Meals (Veg)", 60, "Meals", "/static/images/half meals.jpeg"),
    ("Chicken Biriyani", 140, "Rice", "/static/images/chicken biriyani.jpeg"),
    ("Egg Biriyani", 80, "Rice", "/static/images/egg biriyaniii.jpeg"),
    ("Chicken Fry", 100, "Side Dishes", "/static/images/chicken fry.jpeg"),
    ("vadai", 10, "Side Dishes", "/static/images/boil egg.jpeg"),
     ("Chicken 65", 50, "Side Dishes", "/static/images/65.jpeg"),
    ("Fried Fish", 50, "Side Dishes", "/static/images/fish fry.jpeg"),
    ("Crab Nandu", 60, "Side Dishes", "/static/images/nandu.jpeg"),
    ("Boil Egg Masal", 30, "Side Dishes", "/static/images/masala egg.jpeg"),
    ("Omelete", 20, "Side Dishes", "/static/images/omblete.jpeg"),
    ("Boil Egg", 10, "Side Dishes", "/static/images/boil egg.jpeg"),
]

def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def init_db():
    con = db()

    con.execute("""
        CREATE TABLE IF NOT EXISTS menu (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            category TEXT NOT NULL,
            image_url TEXT NOT NULL,
            active INTEGER NOT NULL DEFAULT 1
        )
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            items_json TEXT NOT NULL,
            subtotal REAL NOT NULL,
            payment_method TEXT NOT NULL,
            amount_received REAL NOT NULL DEFAULT 0,
            change_due REAL NOT NULL DEFAULT 0,
            payment_status TEXT NOT NULL DEFAULT 'paid',
            note TEXT DEFAULT ''
        )
    """)

    count = con.execute(
        "SELECT COUNT(*) FROM menu"
    ).fetchone()[0]

    if count == 0:
        con.executemany(
            """
            INSERT INTO menu (name, price, category, image_url)
            VALUES (?, ?, ?, ?)
            """,
            DEFAULT_MENU
        )

    # Update existing menu items with the correct image paths.
    image_map = {
        "Porata": "/static/images/porata.jpeg",
        "Ghee Porata": "/static/images/ghee porata.jpeg",
        "Egg Kuttu Porata": "/static/images/egg porata.jpeg",
        "Chicken Kuttu Porata": "/static/images/chicken kothu porata.jpeg",
        "Dosa": "/static/images/dosai.jpeg",
        "Egg Dosa": "/static/images/egg dosai.jpeg",
        "Onion Dosa": "/static/images/onion dosai.jpeg",
        "Podi Dosa": "/static/images/podi dosai.jpeg",
        "Kuska": "/static/images/kuska.jpeg",
        "Egg Kuska": "/static/images/egg kuska.jpeg",
        "Meals (Non-veg & Veg)": "/static/images/full mealss.jpeg",
        "Half Meals (Veg)": "/static/images/half meals.jpeg",
        "Chicken Biriyani": "/static/images/chicken biriyani.jpeg",
        "Egg Biriyani": "/static/images/egg biriyaniii.jpeg",
        "Chicken Fry": "/static/images/chicken fry.jpeg",
        "vadai": "/static/images/vadai.jpeg",
        "Chicken 65": "/static/images/65.jpeg",
        "Fried Fish": "/static/images/fish fry.jpeg",
        "Crab Nandu": "/static/images/nandu.jpeg",
        "Boil Egg Masal": "/static/images/masala egg.jpeg",
        "Omelete": "/static/images/omblete.jpeg",
        "Boil Egg": "/static/images/boil egg.jpeg",
    }

    for name, image in image_map.items():
        con.execute(
            "UPDATE menu SET image_url=? WHERE name=?",
            (image, name)
        )
        con.execute(
        "DELETE FROM menu WHERE name = ?",
        ("Egg Veechu Porata",)
    )

    con.commit()
    con.close()


init_db()

@app.route("/")
def index():
    con = db()
    menu = con.execute("SELECT * FROM menu WHERE active=1 ORDER BY category,name").fetchall()
    con.close()
    return render_template("index.html", menu=[dict(x) for x in menu])

@app.route("/api/upload-image", methods=["POST"])
def upload_menu_image():
    file = request.files.get("image")
    if not file or not file.filename:
        return jsonify(ok=False, error="Choose a food image first."), 400
    original = secure_filename(file.filename)
    ext = Path(original).suffix.lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        return jsonify(ok=False, error="Use JPG, JPEG, PNG, WEBP, or GIF image files."), 400
    # Unique name avoids overwriting an image already used by another menu item.
    filename = f"food_{datetime.now().strftime('%Y%m%d%H%M%S%f')}{ext}"
    file.save(UPLOAD_DIR / filename)
    return jsonify(ok=True, image_url=f"/static/uploads/{filename}")

@app.route("/api/menu", methods=["GET"])
def get_menu():
    con = db()
    rows = con.execute("SELECT * FROM menu ORDER BY active DESC, category, name").fetchall()
    con.close()
    return jsonify(ok=True, items=[dict(r) for r in rows])

@app.route("/api/menu", methods=["POST"])
def add_menu_item():
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()[:100]
    category = str(data.get("category", "Other")).strip()[:50] or "Other"
    try:
        price = round(float(data.get("price")), 2)
    except (TypeError, ValueError):
        return jsonify(ok=False, error="Enter a valid price."), 400
    if not name or price < 0 or price > 100000:
        return jsonify(ok=False, error="Enter an item name and a valid non-negative price."), 400
    image_url = str(data.get("image_url", "/static/images/food_01.jpg")).strip()
    if not (image_url.startswith("/static/images/") or image_url.startswith("/static/uploads/")):
        image_url = "/static/images/food_01.jpg"
    con = db()
    cur = con.execute("INSERT INTO menu(name,price,category,image_url,active) VALUES(?,?,?,?,1)",
                      (name, price, category, image_url))
    item_id = cur.lastrowid
    con.commit()
    row = con.execute("SELECT * FROM menu WHERE id=?", (item_id,)).fetchone()
    con.close()
    return jsonify(ok=True, item=dict(row))

@app.route("/api/menu/<int:item_id>", methods=["PUT", "DELETE"])
def edit_menu_item(item_id):
    con = db()
    row = con.execute("SELECT * FROM menu WHERE id=?", (item_id,)).fetchone()
    if not row:
        con.close()
        return jsonify(ok=False, error="Menu item not found."), 404
    if request.method == "DELETE":
        # Keep historical sales intact; hide the item from new bills.
        con.execute("UPDATE menu SET active=0 WHERE id=?", (item_id,))
        con.commit()
        con.close()
        return jsonify(ok=True)
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", row["name"])).strip()[:100]
    category = str(data.get("category", row["category"])).strip()[:50] or "Other"
    try:
        price = round(float(data.get("price", row["price"])), 2)
    except (TypeError, ValueError):
        con.close()
        return jsonify(ok=False, error="Enter a valid price."), 400
    if not name or price < 0 or price > 100000:
        con.close()
        return jsonify(ok=False, error="Enter an item name and a valid non-negative price."), 400
    image_url = str(data.get("image_url", row["image_url"])).strip()
    if not (image_url.startswith("/static/images/") or image_url.startswith("/static/uploads/")):
        image_url = row["image_url"]
    con.execute("UPDATE menu SET name=?,price=?,category=?,image_url=?,active=1 WHERE id=?",
                (name, price, category, image_url, item_id))
    con.commit()
    updated = con.execute("SELECT * FROM menu WHERE id=?", (item_id,)).fetchone()
    con.close()
    return jsonify(ok=True, item=dict(updated))

@app.route("/api/sales", methods=["POST"])
def create_sale():
    data = request.get_json(silent=True) or {}
    items = data.get("items", [])
    if not items:
        return jsonify(ok=False, error="Add at least one item."), 400
    try:
        menu_ids = [int(i.get("id", 0)) for i in items]
    except (TypeError, ValueError):
        return jsonify(ok=False, error="Invalid menu item."), 400
    if any(i <= 0 for i in menu_ids):
        return jsonify(ok=False, error="Invalid menu item."), 400
    con = db()
    placeholders = ",".join("?" for _ in menu_ids)
    rows = con.execute(f"SELECT id,name,price FROM menu WHERE active=1 AND id IN ({placeholders})", menu_ids).fetchall()
    lookup = {r["id"]: r for r in rows}
    normalized, total = [], 0.0
    for item in items:
        try:
            item_id, qty = int(item["id"]), int(item.get("qty", 1))
        except (KeyError, TypeError, ValueError):
            con.close()
            return jsonify(ok=False, error="Invalid item or quantity."), 400
        if item_id not in lookup or qty < 1 or qty > 99:
            con.close()
            return jsonify(ok=False, error="Invalid item or quantity."), 400
        row = lookup[item_id]
        line = round(float(row["price"]) * qty, 2)
        normalized.append({"id":item_id,"name":row["name"],"price":float(row["price"]),"qty":qty,"line_total":line})
        total += line
    total = round(total, 2)
    method = data.get("payment_method", "Cash")
    if method not in ("Cash", "UPI"):
        con.close()
        return jsonify(ok=False, error="Unsupported payment method."), 400
    status = "paid" if method == "Cash" else "pending"
    try:
        received = float(data.get("amount_received", 0) or 0) if method == "Cash" else 0
    except (TypeError, ValueError):
        con.close()
        return jsonify(ok=False, error="Invalid cash amount."), 400
    if method == "Cash" and received < total:
        con.close()
        return jsonify(ok=False, error="Cash received is less than the bill total."), 400
    change = round(received-total, 2) if method == "Cash" else 0
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    cur = con.execute("""INSERT INTO sales(created_at,items_json,subtotal,payment_method,amount_received,change_due,payment_status,note)
        VALUES(?,?,?,?,?,?,?,?)""", (now,json.dumps(normalized,ensure_ascii=False),total,method,received,change,status,""))
    sale_id = cur.lastrowid
    con.commit()
    con.close()
    return jsonify(ok=True,sale_id=sale_id,total=total,amount_received=received,change_due=change,
                   payment_method=method,payment_status=status,created_at=now,items=normalized)

@app.route("/api/sales/<int:sale_id>/confirm-upi", methods=["POST"])
def confirm_upi(sale_id):
    con = db()
    row = con.execute("SELECT id,payment_method,payment_status FROM sales WHERE id=?", (sale_id,)).fetchone()
    if not row:
        con.close()
        return jsonify(ok=False,error="Bill not found."),404
    if row["payment_method"] != "UPI":
        con.close()
        return jsonify(ok=False,error="This bill is not a UPI bill."),400
    con.execute("UPDATE sales SET payment_status='paid' WHERE id=?", (sale_id,))
    con.commit()
    con.close()
    return jsonify(ok=True)

@app.route("/api/sales")
def sales_history():
    con = db()
    rows = con.execute("SELECT * FROM sales ORDER BY id DESC LIMIT 500").fetchall()
    # Compare using local date from Python, avoiding UTC/local SQLite date mismatches.
    today = datetime.now().astimezone().date().isoformat()
    today_rows = con.execute("SELECT created_at,subtotal,payment_method,payment_status FROM sales").fetchall()
    total_today = cash_today = upi_today = 0.0
    bills_today = pending_today = 0
    for r in today_rows:
        try:
            sale_date = datetime.fromisoformat(r["created_at"]).astimezone().date().isoformat()
        except (ValueError, TypeError):
            continue
        if sale_date != today:
            continue
        if r["payment_status"] == "paid":
            total_today += float(r["subtotal"])
            bills_today += 1
            if r["payment_method"] == "Cash": cash_today += float(r["subtotal"])
            else: upi_today += float(r["subtotal"])
        else:
            pending_today += 1
    con.close()
    result=[]
    for r in rows:
        d=dict(r); d["items"]=json.loads(d.pop("items_json")); result.append(d)
    return jsonify(ok=True,sales=result,total_today=round(total_today,2),cash_today=round(cash_today,2),
                   upi_today=round(upi_today,2),bills_today=bills_today,pending_today=pending_today)

@app.route("/settings", methods=["GET","POST"])
def settings():
    if request.method == "POST":
        data=request.get_json(silent=True) or {}
        settings_data={"hotel_name":str(data.get("hotel_name","Prathap Hotel")).strip()[:80] or "Prathap Hotel","currency":"₹"}
        SETTINGS_PATH.write_text(json.dumps(settings_data,ensure_ascii=False,indent=2),encoding="utf-8")
        return jsonify(ok=True,settings=settings_data)
    if SETTINGS_PATH.exists():
        try: settings_data=json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError,OSError): settings_data={"hotel_name":"Prathap Hotel","currency":"₹"}
    else: settings_data={"hotel_name":"Prathap Hotel","currency":"₹"}
    return jsonify(settings_data)

@app.route("/manifest.json")
def manifest():
    return jsonify({"name":"Prathap Hotel Billing","short_name":"Prathap Bill","start_url":"/","display":"standalone",
                    "background_color":"#f7f2e9","theme_color":"#4b2e20","icons":[]})

if __name__ == "__main__":
    init_db()
    print("Prathap Hotel Billing running at http://127.0.0.1:5000")
    app.run(host="127.0.0.1",port=5000,debug=False)
