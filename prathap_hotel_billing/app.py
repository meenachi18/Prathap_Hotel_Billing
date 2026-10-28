
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