PRATHAP HOTEL BILLING - UPDATED PROJECT

Features:
- Food menu with food photos
- Add menu items from Menu & settings
- Edit item name, category, and price
- Hide items that are no longer sold; restore them later
- Cash billing, cash received and change calculation
- UPI bill flow using your separate physical scanner; verify payment in your bank/UPI app before marking paid
- Sales history with today's paid total, paid bill count, cash total, UPI total, and pending UPI bill count
- Receipt printing
- SQLite database stored in this project folder

RUN ON WINDOWS:
1. Extract the ZIP.
2. Open the inner `prathap_hotel_billing` folder in VS Code (the one containing app.py and requirements.txt).
3. In VS Code Terminal run:
   py -m pip install -r requirements.txt
   py app.py
4. Open http://127.0.0.1:5000 in Chrome.
5. Keep the terminal open while using the website. Press Ctrl+C in terminal to stop.

IMPORTANT:
- First-time run creates hotel_billing.db and inserts the starter menu.
- Existing database files are not overwritten. Back up hotel_billing.db before changing folders.
- The app is intended for local use on this computer. It does not connect to a payment gateway.
- Review menu prices before using it for real sales.
