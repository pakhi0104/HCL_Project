"""
generate_data.py
Creates expenses_raw.csv: about 110 sample expenses from June to November 2026.

The data is deliberately a little messy, because the cleaning script
(next step) has to fix it. It also contains the 3 test cases:
  1. Uncategorised expenses (shops the categoriser will not know)
  2. Refund entries (negative amounts)
  3. Month-end boundary dates (30th/31st and the 1st of the next month)

Run:  python generate_data.py
"""
import csv
import random
import calendar
from datetime import date, timedelta
random.seed(42)   
MONTHS = [(2026, 6), (2026, 7), (2026, 8), (2026, 9), (2026, 10), (2026, 11)]
LAST_DATE = date(2026, 11, 25)      # November is still running, so data stops here
SHOPS = {
    "Swiggy": (150, 600),
    "Zomato": (150, 650),
    "Dominos": (250, 700),
    "Starbucks": (200, 450),
    "BigBasket": (400, 1800),
    "Blinkit": (200, 900),
    "Uber": (120, 600),
    "Ola": (100, 500),
    "Metro Recharge": (200, 500),
    "Petrol Pump": (500, 2000),
    "Amazon": (300, 3000),
    "Flipkart": (300, 3000),
    "Myntra": (500, 2500),
    "BookMyShow": (250, 900),
    "Apollo Pharmacy": (150, 1200),
    "Udemy": (400, 1200),
}
UNKNOWN_SHOPS = [
    "Rahul Transfer", "Misc Cash Payment", "Ramesh Vendor", "Local Vendor",
    "UPI Payment 8842", "Gift Shop XYZ", "Cash Note",
]
REFUNDS = ["Amazon Refund", "Flipkart Refund", "Swiggy Refund",
           "Uber Refund", "Myntra Refund"]
rows = []  
def add(d, description, amount):
    """Add one expense to the list."""
    rows.append({"date": d, "description": description,
                 "amount": amount, "odd_date": False})
def last_day_of(year, month):
    """Last valid day of a month (November stops at 25)."""
    if (year, month) == (LAST_DATE.year, LAST_DATE.month):
        return LAST_DATE.day
    return calendar.monthrange(year, month)[1]
def random_date():
    """A random valid date inside the 6 months."""
    year, month = random.choice(MONTHS)
    return date(year, month, random.randint(1, last_day_of(year, month)))
def random_amount(low, high):
    """Random amount rounded to a multiple of 10."""
    return random.randint(low // 10, high // 10) * 10
for year, month in MONTHS:
    last_day = last_day_of(year, month)
    add(date(year, month, 1), "House Rent", 8000)
    add(date(year, month, 7), "Netflix", 199)
    add(date(year, month, 12), "Jio Recharge", 299)
    add(date(year, month, 15), "Electricity Bill", random.randint(8, 22) * 100)
    count = 8 if month == 11 else 11
    for _ in range(count):
        shop = random.choice(list(SHOPS))
        low, high = SHOPS[shop]
        day = random.randint(1, last_day)
        add(date(year, month, day), shop, random_amount(low, high))
for year, month in MONTHS[:-1]:
    last_day = calendar.monthrange(year, month)[1]
    last_date = date(year, month, last_day)
    add(last_date, "Zomato", random_amount(150, 600))
    add(last_date + timedelta(days=1), "Uber", random_amount(100, 500))
for shop in UNKNOWN_SHOPS:
    add(random_date(), shop, random_amount(100, 1500))
for text in REFUNDS:
    add(random_date(), text, -random_amount(300, 1500))
rows.sort(key=lambda r: r["date"])
messy_positions = random.sample(range(len(rows)), 6)
for n, i in enumerate(messy_positions):
    text = rows[i]["description"]
    if n % 3 == 0:
        rows[i]["description"] = text.upper()                 # SWIGGY
    elif n % 3 == 1:
        rows[i]["description"] = "  " + text.lower() + "  "   # "  swiggy  "
    else:
        rows[i]["description"] = text.lower() + " "           # "swiggy "
for i in random.sample(range(len(rows)), 2):
    rows[i]["odd_date"] = True
for i in random.sample(range(len(rows)), 4):
    rows.append(dict(rows[i]))
rows.append({"date": date(2026, 9, 18), "description": "Zomato",
             "amount": "", "odd_date": False})
with open("expenses_raw.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["date", "description", "amount"])
    for r in rows:
        if r["odd_date"]:
            date_text = r["date"].strftime("%d %b %Y")   # 12 Aug 2026
        else:
            date_text = r["date"].isoformat()            # 2026-08-12
        writer.writerow([date_text, r["description"], r["amount"]])

print("Done. expenses_raw.csv created with", len(rows), "rows.")