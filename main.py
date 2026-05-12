import customtkinter as ctk
from tkinter import messagebox
import os
import re
import json
import shutil
import warnings
import ctypes
import pickle
import sys
from datetime import datetime
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from PIL import Image, ImageDraw, ImageFont

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

warnings.filterwarnings("ignore")

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

APP_BG = "#F1F7FF"
SIDEBAR_BG = "#0B2D4D"
CONTENT_BG = "#F6FAFF"
CARD_BG = "#FFFFFF"
PRIMARY = "#1D4ED8"
PRIMARY_HOVER = "#1E40AF"
TEXT_DARK = "#0F172A"
ACCENT = "#F97316"
ACCENT_HOVER = "#EA580C"
DANGER = "#DC2626"
DANGER_HOVER = "#B91C1C"

LOGIN_BG = "#EAF7FF"
LOGIN_DARK = "#08233B"
LOGIN_CYAN = "#38BDF8"
LOGIN_SOFT = "#F8FAFC"

LIGHT_COLORS = {
    "APP_BG": "#F1F7FF",
    "SIDEBAR_BG": "#0B2D4D",
    "CONTENT_BG": "#F6FAFF",
    "CARD_BG": "#FFFFFF",
    "TEXT_DARK": "#0F172A",
    "LOGIN_BG": "#EAF7FF",
    "LOGIN_SOFT": "#F8FAFC",
}

DARK_COLORS = {
    "APP_BG": "#07111F",
    "SIDEBAR_BG": "#020617",
    "CONTENT_BG": "#0F172A",
    "CARD_BG": "#111827",
    "TEXT_DARK": "#F8FAFC",
    "LOGIN_BG": "#07111F",
    "LOGIN_SOFT": "#0F172A",
}

current_theme = {"mode": "light"}

MARKET_RATE_PER_SQFT = {
    "Rajpur Road": 8111,
    "Prem Nagar": 4800,
    "ISBT": 5600,
    "Clement Town": 6000,
    "Ballupur": 6200,
    "GMS Road": 7455,
    "Sahastradhara": 6214,
    "Dalanwala": 9720,
    "Vasant Vihar": 6500,
    "Race Course": 7600,
    "Patel Nagar": 5250,
    "Haridwar Road": 5405,
    "Mussoorie Road": 7670,
    "Raipur": 4600,
    "Jogiwala": 4500,
    "Majra": 4300,
    "Nehru Colony": 5800,
    "Doiwala": 4200,
    "Kargi Chowk": 4700,
    "Turner Road": 5584,
    "Subhash Nagar": 5000,
}

ALL_CITIES = list(MARKET_RATE_PER_SQFT.keys())

current_user = {
    "name": "",
    "username": "",
    "mobile": "",
}

ml_model_cache = {"model": None, "loaded": False, "error": ""}


def app_path(filename):
    if getattr(sys, "frozen", False):
        return os.path.join(os.path.dirname(sys.executable), filename)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)


def load_ml_model():
    if ml_model_cache["loaded"]:
        return ml_model_cache["model"]

    ml_model_cache["loaded"] = True
    model_paths = [app_path("model_ml.pkl"), app_path("model.pkl")]
    model_path = next((path for path in model_paths if os.path.exists(path)), "")
    if not model_path:
        ml_model_cache["error"] = "model file not found"
        return None

    try:
        with open(model_path, "rb") as file:
            ml_model_cache["model"] = pickle.load(file)
    except Exception as error:
        ml_model_cache["error"] = str(error)
        ml_model_cache["model"] = None

    return ml_model_cache["model"]


def predict_price_with_ml(vals, plot_type, city):
    model = load_ml_model()
    if model is None:
        return None

    sqft, rooms, bathrooms, floors, age = vals
    rate = MARKET_RATE_PER_SQFT.get(city, 5500)
    plot_multiplier = 1.00 if plot_type == "Residential" else 1.25

    feature_values = {
        "sqft": sqft,
        "rooms": rooms,
        "bathrooms": bathrooms,
        "floors": floors,
        "age": age,
        "plot_type": plot_type,
        "city": city,
        "rate": rate,
        "market_rate": rate,
        "market_rate_per_sqft": rate,
        "plot_multiplier": plot_multiplier,
        "size_value": sqft * rate * plot_multiplier,
        "room_value": rooms * 35000,
        "bathroom_value": bathrooms * 30000,
        "floor_value": floors * 50000,
        "age_discount_rate": min(age * 0.006, 0.30),
    }
    before_age = feature_values["size_value"] + feature_values["room_value"] + feature_values["bathroom_value"] + feature_values["floor_value"]
    feature_values["before_age"] = before_age
    feature_values["age_discount"] = before_age * feature_values["age_discount_rate"]
    feature_values["formula_price"] = max(before_age - feature_values["age_discount"], 0)

    if isinstance(model, dict):
        try:
            feature_names = model["feature_names"]
            coefficients = model["coefficients"]
            intercept = model.get("intercept", 0)
            predicted = intercept + sum(float(feature_values.get(name, 0)) * float(coef) for name, coef in zip(feature_names, coefficients))
            return max(float(predicted), 0)
        except Exception as error:
            ml_model_cache["error"] = str(error)
            return None

    feature_names = getattr(model, "feature_names_in_", None)
    try:
        if feature_names is not None:
            ordered_input = [[feature_values.get(str(name), 0) for name in feature_names]]
        else:
            ordered_input = [[sqft, rooms, bathrooms, floors, age, rate, plot_multiplier]]

        predicted = model.predict(ordered_input)[0]
        return max(float(predicted), 0)
    except Exception as error:
        ml_model_cache["error"] = str(error)
        return None


def calculate_price(sqft, rooms, bathrooms, floors, age, plot_type, city):
    rate = MARKET_RATE_PER_SQFT.get(city, 5500)
    plot_multiplier = 1.00 if plot_type == "Residential" else 1.25
    base_price = sqft * rate * plot_multiplier
    feature_addition = rooms * 35000 + bathrooms * 30000 + floors * 50000
    age_discount = min(age * 0.006, 0.30)
    return max((base_price + feature_addition) * (1 - age_discount), 0)


def get_price_parts(vals, plot_type, city):
    sqft, rooms, bathrooms, floors, age = vals
    rate = MARKET_RATE_PER_SQFT.get(city, 5500)
    plot_multiplier = 1.00 if plot_type == "Residential" else 1.25

    size_price = sqft * rate * plot_multiplier
    room_price = rooms * 35000
    bathroom_price = bathrooms * 30000
    floor_price = floors * 50000
    before_age = size_price + room_price + bathroom_price + floor_price
    age_discount_rate = min(age * 0.006, 0.30)
    age_discount = before_age * age_discount_rate

    return {
        "House size value": size_price,
        "Rooms added value": room_price,
        "Bathrooms added value": bathroom_price,
        "Floors added value": floor_price,
        "Old house discount": -age_discount,
        "Final price": before_age - age_discount,
    }


def safe_username(username):
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", username.strip())
    return cleaned or "user"


def history_file():
    return f"history_{safe_username(current_user['username'])}.txt"


def reports_folder():
    folder = f"reports_{safe_username(current_user['username'])}"
    os.makedirs(folder, exist_ok=True)
    return folder


def report_folder_name(username):
    return f"reports_{safe_username(username)}"


def history_file_for(username):
    return f"history_{safe_username(username)}.txt"


def apply_app_theme(mode):
    global APP_BG, SIDEBAR_BG, CONTENT_BG, CARD_BG, TEXT_DARK, LOGIN_BG, LOGIN_SOFT
    colors = DARK_COLORS if mode == "dark" else LIGHT_COLORS
    APP_BG = colors["APP_BG"]
    SIDEBAR_BG = colors["SIDEBAR_BG"]
    CONTENT_BG = colors["CONTENT_BG"]
    CARD_BG = colors["CARD_BG"]
    TEXT_DARK = colors["TEXT_DARK"]
    LOGIN_BG = colors["LOGIN_BG"]
    LOGIN_SOFT = colors["LOGIN_SOFT"]
    current_theme["mode"] = mode
    ctk.set_appearance_mode(mode)


def toggle_theme():
    apply_app_theme("dark" if current_theme["mode"] == "light" else "light")


def save_history_record(prediction):
    with open(history_file(), "a", encoding="utf-8") as file:
        file.write(json.dumps(prediction, ensure_ascii=False) + "\n")


def parse_history_record(line):
    line = line.strip()
    if not line:
        return None

    if line.startswith("{"):
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            return None

    parts = [part.strip() for part in line.split(" | ")]
    if len(parts) >= 5:
        return {
            "date": parts[0],
            "city": parts[1],
            "plot_type": parts[2],
            "sqft_text": parts[3],
            "predicted_price_text": parts[4],
            "legacy": True,
        }

    return {
        "date": "Saved earlier",
        "city": "Previous record",
        "predicted_price_text": line,
        "legacy": True,
    }


def read_history_records():
    if not os.path.exists(history_file()):
        return []

    records = []
    with open(history_file(), "r", encoding="utf-8") as file:
        for line in file:
            record = parse_history_record(line)
            if record:
                records.append(record)
    return records


def price_number(record):
    if "predicted_price" in record:
        return float(record["predicted_price"])

    text = record.get("predicted_price_text", "")
    cleaned = re.sub(r"[^0-9.]+", "", text)
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def move_user_files(old_username, new_username):
    old_history = history_file_for(old_username)
    new_history = history_file_for(new_username)
    if os.path.exists(old_history) and old_history != new_history and not os.path.exists(new_history):
        os.rename(old_history, new_history)

    old_reports = report_folder_name(old_username)
    new_reports = report_folder_name(new_username)
    if os.path.exists(old_reports) and old_reports != new_reports and not os.path.exists(new_reports):
        os.rename(old_reports, new_reports)


def format_property_report(data, generated_on=None):
    generated_on = generated_on or data.get("date", datetime.now().strftime("%d-%m-%Y %I:%M %p"))

    if data.get("legacy"):
        return f"""HOUSE PRICE PREDICTION REPORT
================================

Generated On       : {data.get('date', 'Not available')}
Name               : {current_user.get('name', current_user['username'])}
Username           : {current_user['username']}
Mobile Number      : {current_user['mobile']}

PROPERTY DETAILS
--------------------------------
City / Area        : {data.get('city', 'Not available')}
Plot Type          : {data.get('plot_type', 'Not available')}
House Size         : {data.get('sqft_text', 'Not available')}

PRICE RESULT
--------------------------------
Predicted Price    : {data.get('predicted_price_text', 'Not available')}

PRICE BREAKUP
--------------------------------
Complete breakup is not available for this older entry because it was saved
before full house details were stored in history. Make a new prediction and
click its city name to see the full report here.
"""

    parts = data["parts"]
    return f"""HOUSE PRICE PREDICTION REPORT
================================

Generated On       : {generated_on}
Name               : {current_user.get('name', current_user['username'])}
Username           : {current_user['username']}
Mobile Number      : {current_user['mobile']}

PROPERTY DETAILS
--------------------------------
City / Area        : {data['city']}
Plot Type          : {data['plot_type']}
Market Rate        : Rs. {data['rate']:,.0f} per sqft
House Size         : {data['sqft']:,.0f} sqft
Rooms              : {data['rooms']:,.0f}
Bathrooms          : {data['bathrooms']:,.0f}
Floors             : {data['floors']:,.0f}
House Age          : {data['age']:,.0f} years

PRICE RESULT
--------------------------------
Predicted Price    : Rs. {data['predicted_price']:,.2f}

PRICE BREAKUP
--------------------------------
House Size Value   : Rs. {parts['House size value']:,.2f}
Rooms Added Value  : Rs. {parts['Rooms added value']:,.2f}
Bathrooms Value    : Rs. {parts['Bathrooms added value']:,.2f}
Floors Added Value : Rs. {parts['Floors added value']:,.2f}
Age Discount       : Rs. {parts['Old house discount']:,.2f}
Final Price        : Rs. {parts['Final price']:,.2f}

HOW PRICE WAS PREDICTED
--------------------------------
House size value is calculated from square feet, city rate, and plot type.
Rooms, bathrooms, and floors add fixed extra values.
Older houses get an age discount, then the final predicted price is shown.
"""


def read_users():
    users = []
    if not os.path.exists("users.txt"):
        return users

    with open("users.txt", "r", encoding="utf-8") as file:
        for line in file:
            data = line.strip().split(",")
            if len(data) == 3:
                users.append({"name": data[0], "username": data[0], "mobile": data[1], "password": data[2]})
            elif len(data) == 4:
                users.append({"name": data[0], "username": data[1], "mobile": data[2], "password": data[3]})
    return users


def write_users(users):
    with open("users.txt", "w", encoding="utf-8") as file:
        for user in users:
            file.write(f"{user.get('name', user['username'])},{user['username']},{user['mobile']},{user['password']}\n")


app = ctk.CTk()
app.title("House Price Prediction System")
app.configure(fg_color=APP_BG)
app.geometry(f"{app.winfo_screenwidth()}x{app.winfo_screenheight()}+0+0")
app.minsize(1000, 650)
app.after(200, lambda: app.state("zoomed"))
app.bind("<F11>", lambda event: app.state("zoomed"))
app.bind("<Escape>", lambda event: app.state("normal"))


def clear():
    for widget in app.winfo_children():
        widget.destroy()


def bind_enter(widget, command):
    widget.bind("<Return>", lambda event: command())


def bind_focus_keys(widgets):
    for i, widget in enumerate(widgets):
        widget.bind("<Down>", lambda event, i=i: widgets[(i + 1) % len(widgets)].focus_set())
        widget.bind("<Right>", lambda event, i=i: widgets[(i + 1) % len(widgets)].focus_set())
        widget.bind("<Up>", lambda event, i=i: widgets[(i - 1) % len(widgets)].focus_set())
        widget.bind("<Left>", lambda event, i=i: widgets[(i - 1) % len(widgets)].focus_set())


def bind_option_arrows(option_menu, variable, values, on_change=None):
    def move(step):
        current = variable.get()
        index = values.index(current) if current in values else 0
        variable.set(values[(index + step) % len(values)])
        if on_change:
            on_change()

    option_menu.bind("<Right>", lambda event: move(1))
    option_menu.bind("<Down>", lambda event: move(1))
    option_menu.bind("<Left>", lambda event: move(-1))
    option_menu.bind("<Up>", lambda event: move(-1))


def app_font(size, bold=False):
    names = ["arialbd.ttf" if bold else "arial.ttf", "segoeuib.ttf" if bold else "segoeui.ttf"]
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            pass
    return ImageFont.load_default()


def create_dashboard_art(image_path):
    width, height = 1300, 470
    img = Image.new("RGB", (width, height), "#DFF3FF")
    draw = ImageDraw.Draw(img)

    for y in range(height):
        blend = y / height
        draw.line(
            [(0, y), (width, y)],
            fill=(int(232 - 28 * blend), int(246 - 20 * blend), int(255 - 10 * blend)),
        )

    draw.rounded_rectangle((28, 26, 1272, 444), radius=36, fill="#FFFFFF", outline="#BFDBFE", width=3)

    # Distant city skyline.
    skyline_y = 248
    buildings = [
        (70, 142, 70, 126, "#A5D8FF"),
        (156, 116, 92, 152, "#7CC7F7"),
        (268, 158, 72, 110, "#BEE3FF"),
        (362, 104, 105, 164, "#93C5FD"),
        (488, 134, 86, 134, "#60A5FA"),
        (596, 96, 112, 172, "#38BDF8"),
        (734, 132, 80, 136, "#93C5FD"),
        (838, 112, 104, 156, "#7CC7F7"),
        (964, 154, 84, 114, "#BEE3FF"),
    ]
    for x, y, w, h, color in buildings:
        draw.rounded_rectangle((x, y, x + w, y + h), radius=10, fill=color)
        for wx in range(x + 16, x + w - 8, 24):
            for wy in range(y + 18, y + h - 16, 30):
                draw.rectangle((wx, wy, wx + 8, wy + 12), fill="#EAF7FF")

    # Main modern home.
    house_x, house_y = 118, 230
    draw.rounded_rectangle((house_x + 26, house_y + 78, house_x + 360, house_y + 190), radius=18, fill="#F8FAFC", outline="#D9EAFD", width=3)
    draw.polygon([(house_x, house_y + 90), (house_x + 190, house_y - 36), (house_x + 388, house_y + 90)], fill="#F97316")
    draw.rectangle((house_x + 182, house_y + 125, house_x + 238, house_y + 190), fill="#0B2D4D")
    draw.rounded_rectangle((house_x + 72, house_y + 112, house_x + 136, house_y + 158), radius=8, fill="#BFDBFE", outline="#0B2D4D", width=2)
    draw.rounded_rectangle((house_x + 268, house_y + 112, house_x + 326, house_y + 158), radius=8, fill="#BFDBFE", outline="#0B2D4D", width=2)
    draw.rectangle((0, 418, width, height), fill="#C7F9D4")
    draw.ellipse((72, 384, 472, 464), fill="#86EFAC")

    # Clean map route and location pins.
    route = [(540, 372), (626, 322), (732, 342), (830, 288), (930, 304), (1040, 236), (1160, 254)]
    draw.line(route, fill="#1D4ED8", width=8)
    for x, y in route:
        draw.ellipse((x - 12, y - 12, x + 12, y + 12), fill="#FFFFFF", outline="#1D4ED8", width=4)
    for x, y, color in [(626, 322, "#F97316"), (830, 288, "#22C55E"), (1040, 236, "#DC2626")]:
        draw.ellipse((x - 18, y - 32, x + 18, y + 4), fill=color)
        draw.polygon([(x - 10, y - 2), (x + 10, y - 2), (x, y + 20)], fill=color)
        draw.ellipse((x - 6, y - 20, x + 6, y - 8), fill="#FFFFFF")

    # Floating price graph glass panel without repeated captions.
    panel = (780, 70, 1214, 210)
    draw.rounded_rectangle(panel, radius=26, fill="#F8FAFC", outline="#BFDBFE", width=3)
    for y in [108, 140, 172]:
        draw.line([(818, y), (1170, y)], fill="#D9EAFD", width=2)
    curve = [(824, 178), (892, 148), (956, 160), (1028, 118), (1090, 98), (1165, 82)]
    draw.line(curve, fill="#16A34A", width=8)
    for x, y in curve:
        draw.ellipse((x - 9, y - 9, x + 9, y + 9), fill="#F97316", outline="#FFFFFF", width=3)

    # Premium report sheet.
    draw.rounded_rectangle((548, 84, 700, 238), radius=18, fill="#FFFFFF", outline="#D9EAFD", width=3)
    draw.rectangle((574, 116, 674, 126), fill="#1D4ED8")
    draw.rectangle((574, 146, 660, 156), fill="#93C5FD")
    draw.rectangle((574, 176, 680, 186), fill="#FDBA74")
    draw.rectangle((574, 206, 642, 216), fill="#22C55E")

    img.save(image_path)


def load_dashboard_image(parent):
    image_path = "dashboard_auto.png"
    create_dashboard_art(image_path)

    image_card = ctk.CTkFrame(parent, fg_color=CARD_BG, corner_radius=22)
    image_card.pack(pady=10, padx=35)

    img = Image.open(image_path)
    scale = min(1060 / img.size[0], 330 / img.size[1])
    new_size = (int(img.size[0] * scale), int(img.size[1] * scale))
    img = img.resize(new_size, Image.LANCZOS)
    dash_img = ctk.CTkImage(light_image=img, dark_image=img, size=new_size)

    img_label = ctk.CTkLabel(image_card, image=dash_img, text="")
    img_label.image = dash_img
    img_label.pack(padx=15, pady=15)


def create_login_art(image_path):
    width, height = 560, 680
    img = Image.new("RGB", (width, height), "#071B30")
    draw = ImageDraw.Draw(img)

    for y in range(height):
        blend = y / height
        draw.line(
            [(0, y), (width, y)],
            fill=(int(7 + 13 * blend), int(27 + 82 * blend), int(48 + 132 * blend)),
        )

    for x in range(-160, width, 64):
        draw.line([(x, 0), (x + 250, height)], fill="#123C69", width=1)
    for x in range(0, width, 70):
        draw.line([(x, 0), (x - 190, height)], fill="#0E3A61", width=1)

    draw.rounded_rectangle((30, 28, 530, 650), radius=34, fill="#08233B", outline="#38BDF8", width=3)
    draw.rounded_rectangle((58, 56, 502, 146), radius=24, fill="#0E3A61", outline="#1D9BD7", width=2)
    draw.text((84, 78), "HOUSE PRICE", fill="#FFFFFF")
    draw.text((84, 108), "PREDICTION SUITE", fill="#BAE6FD")
    draw.rounded_rectangle((380, 76, 468, 122), radius=18, fill="#16A34A")
    draw.text((403, 91), "LIVE", fill="#FFFFFF")

    panel_x, panel_y = 70, 178
    draw.rounded_rectangle((panel_x, panel_y, panel_x + 420, panel_y + 260), radius=26, fill="#F8FAFC", outline="#D9EAFD", width=2)
    draw.rounded_rectangle((panel_x + 24, panel_y + 24, panel_x + 396, panel_y + 82), radius=16, fill="#EAF7FF")
    draw.text((panel_x + 46, panel_y + 43), "Dehradun Market Analytics", fill="#0B2D4D")

    chart_area = (panel_x + 36, panel_y + 108, panel_x + 390, panel_y + 222)
    draw.rectangle(chart_area, fill="#FFFFFF", outline="#D9EAFD")
    grid_y = chart_area[1] + 24
    while grid_y < chart_area[3]:
        draw.line([(chart_area[0], grid_y), (chart_area[2], grid_y)], fill="#E2E8F0", width=1)
        grid_y += 26
    chart_points = [(118, 360), (178, 330), (238, 345), (302, 292), (380, 274), (445, 236)]
    draw.line(chart_points, fill="#1D4ED8", width=6)
    for x, y in chart_points:
        draw.ellipse((x - 8, y - 8, x + 8, y + 8), fill="#F97316", outline="#FFFFFF", width=2)

    house_x, house_y = 118, 456
    draw.rounded_rectangle((house_x + 28, house_y + 86, house_x + 210, house_y + 186), radius=10, fill="#F8FAFC", outline="#D9EAFD", width=2)
    draw.polygon([(house_x, house_y + 92), (house_x + 120, house_y + 12), (house_x + 240, house_y + 92)], fill="#F97316")
    draw.rectangle((house_x + 102, house_y + 130, house_x + 142, house_y + 186), fill="#0B2D4D")
    draw.rectangle((house_x + 54, house_y + 112, house_x + 92, house_y + 146), fill="#BFDBFE", outline="#0B2D4D", width=2)
    draw.rectangle((house_x + 156, house_y + 112, house_x + 194, house_y + 146), fill="#BFDBFE", outline="#0B2D4D", width=2)

    metric_cards = [
        (332, 468, "21", "Areas", "#38BDF8"),
        (332, 540, "PDF", "Reports", "#F97316"),
    ]
    for x, y, value, label, color in metric_cards:
        draw.rounded_rectangle((x, y, x + 138, y + 56), radius=16, fill="#123C69", outline=color, width=2)
        draw.text((x + 18, y + 12), value, fill=color)
        draw.text((x + 66, y + 18), label, fill="#FFFFFF")

    draw.text((78, 624), "City rates. Plot type. Private history. Clear reports.", fill="#BAE6FD")
    img.save(image_path)


def load_login_art(parent):
    image_path = "login_property_art.png"
    create_login_art(image_path)
    img = Image.open(image_path)
    login_img = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
    img_label = ctk.CTkLabel(parent, image=login_img, text="")
    img_label.image = login_img
    img_label.pack(fill="both", expand=True)


def show_login():
    clear()
    app.configure(fg_color=LOGIN_BG)
    current_user["name"] = ""
    current_user["username"] = ""
    current_user["mobile"] = ""

    bg_band = ctk.CTkFrame(app, fg_color="#DFF3FF", corner_radius=0)
    bg_band.place(relx=0.0, rely=0.0, relwidth=1.0, relheight=0.42)

    shell = ctk.CTkFrame(app, width=1160, height=680, fg_color="#FFFFFF", corner_radius=32)
    shell.place(relx=0.5, rely=0.5, anchor="center")
    shell.pack_propagate(False)

    left = ctk.CTkFrame(shell, width=560, height=680, fg_color=LOGIN_DARK, corner_radius=32)
    left.pack(side="left", fill="y")
    left.pack_propagate(False)

    load_login_art(left)

    right = ctk.CTkFrame(shell, width=600, height=680, fg_color=LOGIN_SOFT, corner_radius=32)
    right.pack(side="right", fill="both", expand=True)
    right.pack_propagate(False)

    badge_row = ctk.CTkFrame(right, fg_color=LOGIN_SOFT)
    badge_row.pack(anchor="e", padx=42, pady=(34, 0))
    for text, color in [("Secure Login", PRIMARY), ("Local Data", "#16A34A")]:
        ctk.CTkLabel(
            badge_row,
            text=text,
            width=110,
            height=30,
            fg_color=color,
            corner_radius=14,
            text_color="white",
            font=("Arial", 12, "bold"),
        ).pack(side="left", padx=5)

    login_card = ctk.CTkFrame(right, width=440, height=500, fg_color="#FFFFFF", corner_radius=28)
    login_card.place(relx=0.5, rely=0.5, anchor="center")
    login_card.pack_propagate(False)

    ctk.CTkLabel(login_card, text="Welcome Back", font=("Arial", 34, "bold"), text_color=TEXT_DARK).pack(pady=(34, 4))
    ctk.CTkLabel(login_card, text="Sign in to your property valuation workspace", font=("Arial", 15), text_color="#64748B").pack(pady=(0, 18))

    ctk.CTkFrame(login_card, width=335, height=3, fg_color=LOGIN_CYAN, corner_radius=10).pack(pady=(0, 22))

    user = ctk.CTkEntry(login_card, placeholder_text="Username", width=345, height=50, corner_radius=14, border_width=2, border_color="#D9EAFD", fg_color="#F8FAFC")
    pwd = ctk.CTkEntry(login_card, placeholder_text="Password", show="*", width=345, height=50, corner_radius=14, border_width=2, border_color="#D9EAFD", fg_color="#F8FAFC")
    user.pack(pady=8)
    pwd.pack(pady=8)

    show_pass = ctk.BooleanVar(value=False)
    show_box = ctk.CTkCheckBox(
        login_card,
        text="Show Password",
        variable=show_pass,
        command=lambda: pwd.configure(show="" if show_pass.get() else "*"),
        text_color=TEXT_DARK,
        fg_color=ACCENT,
        hover_color=ACCENT_HOVER,
        border_color="#475569",
    )
    show_box.pack(anchor="w", padx=48, pady=10)

    def login():
        users = read_users()
        if not users:
            return messagebox.showerror("Error", "No users found")

        for saved_user in users:
            if saved_user["username"] == user.get() and saved_user["password"] == pwd.get():
                current_user["name"] = saved_user.get("name", saved_user["username"])
                current_user["username"] = saved_user["username"]
                current_user["mobile"] = saved_user["mobile"]
                show_dashboard()
                return

        messagebox.showerror("Error", "Invalid Login")

    login_btn = ctk.CTkButton(login_card, text="Login", command=login, width=345, height=48, corner_radius=14, fg_color=PRIMARY, hover_color=PRIMARY_HOVER, font=("Arial", 16, "bold"))
    signup_btn = ctk.CTkButton(login_card, text="Create New Account", command=show_signup, width=345, height=44, corner_radius=14, fg_color=ACCENT, hover_color=ACCENT_HOVER, font=("Arial", 14, "bold"))
    login_btn.pack(pady=(16, 10))
    signup_btn.pack()

    forgot_btn = ctk.CTkButton(
        login_card,
        text="Forgot Password?",
        command=show_forgot_password,
        width=345,
        height=34,
        corner_radius=14,
        fg_color="#EAF7FF",
        hover_color="#D9EAFD",
        text_color=PRIMARY,
        font=("Arial", 13, "bold"),
    )
    forgot_btn.pack(pady=(8, 0))

    ctk.CTkLabel(
        login_card,
        text="Built for city rates, plot comparison, graph insights, and saved reports.",
        font=("Arial", 12),
        text_color="#64748B",
        wraplength=340,
    ).pack(pady=(20, 0))

    widgets = [user, pwd, show_box, login_btn, signup_btn, forgot_btn]
    bind_focus_keys(widgets)
    for widget in widgets:
        if widget == signup_btn:
            bind_enter(widget, show_signup)
        elif widget == forgot_btn:
            bind_enter(widget, show_forgot_password)
        else:
            bind_enter(widget, login)
    user.focus_set()


def show_forgot_password():
    clear()
    app.configure(fg_color=LOGIN_BG)

    frame = ctk.CTkFrame(app, width=460, height=500, fg_color=CARD_BG, corner_radius=24)
    frame.place(relx=0.5, rely=0.5, anchor="center")
    frame.pack_propagate(False)

    ctk.CTkLabel(frame, text="Reset Password", font=("Arial", 30, "bold"), text_color=TEXT_DARK).pack(pady=(32, 6))
    ctk.CTkLabel(frame, text="Verify username and mobile number", font=("Arial", 14), text_color="#64748B").pack(pady=(0, 20))

    username = ctk.CTkEntry(frame, placeholder_text="Username", width=320, height=42)
    mobile = ctk.CTkEntry(frame, placeholder_text="Registered Mobile Number", width=320, height=42)
    new_pwd = ctk.CTkEntry(frame, placeholder_text="New Password", show="*", width=320, height=42)
    confirm_pwd = ctk.CTkEntry(frame, placeholder_text="Repeat New Password", show="*", width=320, height=42)

    for entry in [username, mobile, new_pwd, confirm_pwd]:
        entry.pack(pady=6)

    def reset_password():
        if not all([username.get(), mobile.get(), new_pwd.get(), confirm_pwd.get()]):
            return messagebox.showerror("Error", "Fill all fields")
        if new_pwd.get() != confirm_pwd.get():
            return messagebox.showerror("Error", "New passwords do not match")

        users = read_users()
        for saved_user in users:
            if saved_user["username"] == username.get() and saved_user["mobile"] == mobile.get():
                saved_user["password"] = new_pwd.get()
                write_users(users)
                messagebox.showinfo("Success", "Password reset successfully")
                show_login()
                return

        messagebox.showerror("Error", "Username and mobile number do not match")

    reset_btn = ctk.CTkButton(frame, text="Reset Password", command=reset_password, width=320, height=42, fg_color=PRIMARY, hover_color=PRIMARY_HOVER)
    back_btn = ctk.CTkButton(frame, text="Back to Login", command=show_login, width=320, height=38, fg_color=ACCENT, hover_color=ACCENT_HOVER)
    reset_btn.pack(pady=(16, 8))
    back_btn.pack()

    widgets = [username, mobile, new_pwd, confirm_pwd, reset_btn, back_btn]
    bind_focus_keys(widgets)
    for widget in widgets:
        bind_enter(widget, show_login if widget == back_btn else reset_password)
    username.focus_set()


def show_signup():
    clear()
    app.configure(fg_color=LOGIN_BG)

    frame = ctk.CTkFrame(app, width=430, height=540, fg_color=CARD_BG, corner_radius=24)
    frame.place(relx=0.5, rely=0.5, anchor="center")
    frame.pack_propagate(False)

    ctk.CTkLabel(frame, text="Create Account", font=("Arial", 28, "bold"), text_color=TEXT_DARK).pack(pady=(30, 6))
    ctk.CTkLabel(frame, text="Start predicting property prices", font=("Arial", 14), text_color="#64748B").pack(pady=(0, 18))

    name = ctk.CTkEntry(frame, placeholder_text="Full Name", width=300, height=40)
    username = ctk.CTkEntry(frame, placeholder_text="Username", width=300, height=40)
    mobile = ctk.CTkEntry(frame, placeholder_text="Mobile", width=300, height=40)
    password = ctk.CTkEntry(frame, placeholder_text="Password", show="*", width=300, height=40)
    confirm = ctk.CTkEntry(frame, placeholder_text="Confirm Password", show="*", width=300, height=40)

    for entry in [name, username, mobile, password, confirm]:
        entry.pack(pady=6)

    def signup():
        if not all([name.get(), username.get(), mobile.get(), password.get(), confirm.get()]):
            return messagebox.showerror("Error", "Fill all fields")
        if password.get() != confirm.get():
            return messagebox.showerror("Error", "Passwords mismatch")

        users = read_users()
        if any(saved_user["username"] == username.get() for saved_user in users):
            return messagebox.showerror("Error", "Username already exists")

        users.append({"name": name.get(), "username": username.get(), "mobile": mobile.get(), "password": password.get()})
        write_users(users)
        messagebox.showinfo("Success", "Account created")
        show_login()

    create_btn = ctk.CTkButton(frame, text="Create Account", command=signup, width=300, height=42, fg_color=PRIMARY, hover_color=PRIMARY_HOVER)
    back_btn = ctk.CTkButton(frame, text="Back to Login", command=show_login, width=300, height=38, fg_color=ACCENT, hover_color=ACCENT_HOVER)
    create_btn.pack(pady=(16, 8))
    back_btn.pack()

    widgets = [name, username, mobile, password, confirm, create_btn, back_btn]
    bind_focus_keys(widgets)
    for widget in widgets:
        bind_enter(widget, signup if widget != back_btn else show_login)
    name.focus_set()


def show_dashboard():
    clear()
    app.configure(fg_color=APP_BG)

    sidebar = ctk.CTkFrame(app, width=230, fg_color=SIDEBAR_BG, corner_radius=0)
    sidebar.pack(side="left", fill="y")
    sidebar.pack_propagate(False)

    content = ctk.CTkFrame(app, fg_color=CONTENT_BG, corner_radius=0)
    content.pack(side="right", expand=True, fill="both")

    def clear_content():
        for widget in content.winfo_children():
            widget.destroy()

    def switch_theme():
        toggle_theme()
        show_dashboard()

    def home():
        clear_content()
        page = ctk.CTkFrame(content, fg_color=CONTENT_BG, corner_radius=0)
        page.pack(expand=True, fill="both")

        title_row = ctk.CTkFrame(page, fg_color=CONTENT_BG)
        title_row.pack(fill="x", padx=34, pady=(18, 2))
        ctk.CTkLabel(
            title_row,
            text="House Price Intelligence Dashboard",
            font=("Arial", 30, "bold"),
            text_color=TEXT_DARK,
        ).pack(side="left")
        ctk.CTkLabel(
            title_row,
            text="PREMIUM MODE",
            width=140,
            height=34,
            fg_color=SIDEBAR_BG,
            corner_radius=16,
            text_color="white",
            font=("Arial", 12, "bold"),
        ).pack(side="right", padx=10)

        ctk.CTkLabel(
            page,
            text="A rare visual workspace for city rates, plot comparison, prediction graphs, and saved property reports.",
            font=("Arial", 14),
            text_color="#52616B",
        ).pack(anchor="w", padx=36, pady=(0, 8))

        stats = ctk.CTkFrame(page, fg_color=CONTENT_BG)
        stats.pack(fill="x", padx=30, pady=(0, 6))
        stat_items = [
            ("21", "Areas", LOGIN_CYAN),
            ("2", "Plot Types", ACCENT),
            ("4", "Graphs", "#22C55E"),
            ("PDF", "Reports", PRIMARY),
            ("Live", "History", "#A855F7"),
        ]
        for value, label, color in stat_items:
            item = ctk.CTkFrame(stats, width=176, height=76, fg_color=CARD_BG, corner_radius=14, border_width=1, border_color="#D9EAFD")
            item.pack(side="left", padx=6, pady=2)
            item.pack_propagate(False)
            ctk.CTkLabel(item, text=value, font=("Arial", 21, "bold"), text_color=color).pack(pady=(9, 0))
            ctk.CTkLabel(item, text=label, font=("Arial", 11), text_color="#52616B", wraplength=148).pack()

        load_dashboard_image(page)

        quick_panel = ctk.CTkFrame(page, fg_color=CONTENT_BG)
        quick_panel.pack(fill="x", padx=34, pady=(4, 10))
        for title, detail, color in [
            ("Predict", "Enter details and get a city-aware price.", PRIMARY),
            ("Compare", "View rates across areas and plot types.", ACCENT),
            ("Report", "Open saved history as colorful reports.", "#16A34A"),
        ]:
            tile = ctk.CTkFrame(quick_panel, height=72, fg_color=CARD_BG, corner_radius=14, border_width=1, border_color="#D9EAFD")
            tile.pack(side="left", expand=True, fill="x", padx=8)
            tile.pack_propagate(False)
            ctk.CTkLabel(tile, text=title, font=("Arial", 17, "bold"), text_color=color).pack(anchor="w", padx=18, pady=(10, 0))
            ctk.CTkLabel(tile, text=detail, font=("Arial", 12), text_color="#52616B", wraplength=260).pack(anchor="w", padx=18, pady=(2, 0))

    def locations():
        clear_content()
        ctk.CTkLabel(content, text="Dehradun Location Rates", font=("Arial", 30, "bold"), text_color=TEXT_DARK).pack(pady=(20, 4))
        ctk.CTkLabel(content, text="Current rate per square foot used by the prediction system.", font=("Arial", 14), text_color="#52616B").pack(pady=(0, 10))

        search_area = ctk.CTkFrame(content, fg_color=CARD_BG, corner_radius=14)
        search_area.pack(pady=(0, 10))
        ctk.CTkLabel(search_area, text="Search City", font=("Arial", 14, "bold"), text_color=TEXT_DARK).pack(side="left", padx=(16, 8), pady=10)
        city_search_var = ctk.StringVar()
        city_search = ctk.CTkEntry(search_area, placeholder_text="Type city or area name", textvariable=city_search_var, width=300, height=36)
        city_search.pack(side="left", padx=(0, 16), pady=10)

        table = ctk.CTkScrollableFrame(content, width=760, height=560, fg_color=CARD_BG, corner_radius=16)
        table.pack(pady=8)

        def draw_locations():
            for widget in table.winfo_children():
                widget.destroy()

            headers = ["City / Area", "Residential Rate", "Industrial Rate"]
            for column, header in enumerate(headers):
                ctk.CTkLabel(table, text=header, font=("Arial", 15, "bold"), text_color="white", fg_color=SIDEBAR_BG, corner_radius=8, width=210, height=36).grid(row=0, column=column, padx=8, pady=(12, 8), sticky="ew")

            query = city_search_var.get().strip().lower()
            cities = [city for city in ALL_CITIES if query in city.lower()]
            if not cities:
                ctk.CTkLabel(table, text="No matching city found", font=("Arial", 15), text_color=TEXT_DARK).grid(row=1, column=0, columnspan=3, padx=70, pady=25)
                return

            for row, city in enumerate(cities, start=1):
                rate = MARKET_RATE_PER_SQFT[city]
                industrial_rate = rate * 1.25
                row_bg = "#F8FAFC" if row % 2 else "#EAF7FF"
                values = [city, f"Rs. {rate:,.0f} / sqft", f"Rs. {industrial_rate:,.0f} / sqft"]
                for column, value in enumerate(values):
                    ctk.CTkLabel(table, text=value, font=("Arial", 14), text_color="#0F172A", fg_color=row_bg, corner_radius=8, width=210, height=34).grid(row=row, column=column, padx=8, pady=4, sticky="ew")

        city_search.bind("<KeyRelease>", lambda event: draw_locations())
        bind_enter(city_search, draw_locations)
        draw_locations()

    def predict():
        clear_content()
        form = ctk.CTkScrollableFrame(content, width=850, height=650, fg_color=CARD_BG, corner_radius=18)
        form.pack(pady=14)

        ctk.CTkLabel(form, text="Predict Price", font=("Arial", 26, "bold"), text_color=TEXT_DARK).pack(pady=(16, 12))

        labels = ["Sqft", "Rooms", "Bathrooms", "Floors", "Age (Years)"]
        entries = []
        for label in labels:
            ctk.CTkLabel(form, text=label, text_color=TEXT_DARK).pack()
            entry = ctk.CTkEntry(form, width=320, height=34)
            entry.pack(pady=4)
            entries.append(entry)

        ctk.CTkLabel(form, text="Select Plot Type", text_color=TEXT_DARK).pack(pady=(6, 0))
        plot_values = ["Select Plot Type", "Residential", "Industrial"]
        plot_var = ctk.StringVar(value="Select Plot Type")
        plot_menu = ctk.CTkOptionMenu(form, values=plot_values, variable=plot_var, width=320)
        plot_menu.pack(pady=4)

        ctk.CTkLabel(form, text="Select City", text_color=TEXT_DARK).pack(pady=(6, 0))
        city_values = ["Select City"] + ALL_CITIES
        city_var = ctk.StringVar(value="Select City")
        city_menu = ctk.CTkOptionMenu(form, values=city_values, variable=city_var, width=320)
        city_menu.pack(pady=4)

        result = ctk.CTkLabel(form, text="", font=("Arial", 22, "bold"), text_color=PRIMARY)
        result.pack(pady=10)

        graph_area = ctk.CTkFrame(form, fg_color=CARD_BG, corner_radius=12, width=790)
        graph_area.pack(pady=8)
        graph_area.pack_propagate(False)

        last_prediction = {}

        def save_report():
            if not last_prediction:
                return messagebox.showerror("Error", "Please predict price first")

            report_time = datetime.now()
            filename = f"property_report_{report_time.strftime('%Y%m%d_%H%M%S')}.txt"
            path = os.path.join(reports_folder(), filename)
            data = last_prediction
            report = format_property_report(data, report_time.strftime("%d-%m-%Y %I:%M %p"))
            with open(path, "w", encoding="utf-8") as file:
                file.write(report)

            messagebox.showinfo("Report Saved", f"Report saved successfully:\n{path}")

        save_report_btn = ctk.CTkButton(form, text="Save Report", command=save_report, width=320, height=40, fg_color="#16A34A", hover_color="#15803D")

        def show_prediction_graph():
            for widget in graph_area.winfo_children():
                widget.destroy()

            if not last_prediction:
                return messagebox.showerror("Error", "Please predict price first")

            graph_area.configure(width=790, height=500)

            parts = last_prediction["parts"]
            display_names = {
                "House size value": "House size",
                "Rooms added value": "Rooms",
                "Bathrooms added value": "Bathrooms",
                "Floors added value": "Floors",
                "Old house discount": "Age discount",
                "Final price": "Final price",
            }
            names = [display_names[name] for name in parts.keys()]
            values = [parts[name] / 100000 for name in parts.keys()]
            colors = [DANGER if name == "Old house discount" else "#16A34A" if name == "Final price" else PRIMARY for name in parts.keys()]

            fig = Figure(figsize=(8.8, 4.4), facecolor="white")
            ax = fig.add_subplot(111)
            bars = ax.bar(names, values, color=colors)
            ax.set_title("Predicted Price in Simple Parts", fontsize=12, pad=10)
            ax.set_ylabel("Amount in Lakhs", fontsize=10)
            ax.tick_params(axis="x", labelrotation=15, labelsize=9)
            ax.tick_params(axis="y", labelsize=9)
            ax.grid(axis="y", alpha=0.3)

            for bar, value in zip(bars, values):
                ax.text(bar.get_x() + bar.get_width() / 2, value + (1 if value >= 0 else -1), f"{value:.1f}L", ha="center", va="bottom" if value >= 0 else "top", fontsize=9)

            fig.subplots_adjust(left=0.10, right=0.97, top=0.86, bottom=0.20)
            canvas = FigureCanvasTkAgg(fig, master=graph_area)
            canvas.draw()
            canvas.get_tk_widget().pack(padx=20, pady=10)

        show_graph_btn = ctk.CTkButton(form, text="Show Graph", command=show_prediction_graph, width=320, height=40, fg_color=ACCENT, hover_color=ACCENT_HOVER)

        def do_predict(event=None):
            if plot_var.get() == "Select Plot Type":
                return messagebox.showerror("Error", "Please select plot type")
            if city_var.get() == "Select City":
                return messagebox.showerror("Error", "Please select city")

            vals = []
            for i, entry in enumerate(entries):
                value = entry.get().strip()
                if value == "":
                    return messagebox.showerror("Error", f"Please enter {labels[i]}")
                try:
                    vals.append(float(value))
                except ValueError:
                    return messagebox.showerror("Error", f"{labels[i]} must contain only numbers")

            if vals[0] <= 0:
                return messagebox.showerror("Error", "Sqft must be greater than 0")

            parts = get_price_parts(vals, plot_var.get(), city_var.get())
            predicted_price = predict_price_with_ml(vals, plot_var.get(), city_var.get())
            if predicted_price is None:
                predicted_price = parts["Final price"]
            else:
                parts["Final price"] = predicted_price
            result.configure(text=f"Rs. {predicted_price:,.2f}")

            for widget in graph_area.winfo_children():
                widget.destroy()
            graph_area.configure(height=1)

            last_prediction.clear()
            last_prediction.update({
                "sqft": vals[0],
                "rooms": vals[1],
                "bathrooms": vals[2],
                "floors": vals[3],
                "age": vals[4],
                "city": city_var.get(),
                "plot_type": plot_var.get(),
                "rate": MARKET_RATE_PER_SQFT[city_var.get()],
                "parts": parts,
                "predicted_price": predicted_price,
                "date": datetime.now().strftime("%d-%m-%Y %I:%M %p"),
            })

            if not save_report_btn.winfo_ismapped():
                save_report_btn.pack(pady=(0, 8))
            if not show_graph_btn.winfo_ismapped():
                show_graph_btn.pack(pady=(4, 12))

            save_history_record(last_prediction)

        predict_btn = ctk.CTkButton(form, text="Predict Price", command=do_predict, width=320, height=40, fg_color=PRIMARY, hover_color=PRIMARY_HOVER)
        predict_btn.pack(pady=(6, 10))

        widgets = entries + [plot_menu, city_menu, predict_btn, save_report_btn, show_graph_btn]
        bind_focus_keys(widgets)
        bind_option_arrows(plot_menu, plot_var, plot_values)
        bind_option_arrows(city_menu, city_var, city_values)
        for widget in entries + [plot_menu, city_menu, predict_btn]:
            bind_enter(widget, do_predict)
        bind_enter(save_report_btn, save_report)
        bind_enter(show_graph_btn, show_prediction_graph)
        entries[0].focus_set()

    def graph():
        clear_content()
        page = ctk.CTkScrollableFrame(content, fg_color=CONTENT_BG, corner_radius=0)
        page.pack(expand=True, fill="both")
        ctk.CTkLabel(page, text="Price Graphs", font=("Arial", 30, "bold"), text_color=TEXT_DARK).pack(pady=(14, 4))
        ctk.CTkLabel(page, text="Select city and plot type. Move your cursor over graph points to see prices.", font=("Arial", 14), text_color="#52616B").pack(pady=(0, 10))

        control_card = ctk.CTkFrame(page, fg_color=CARD_BG, corner_radius=16)
        control_card.pack(pady=4)
        selected_city = ctk.StringVar(value="Select City")
        selected_plot = ctk.StringVar(value="Select Plot Type")
        city_values = ["Select City"] + ALL_CITIES
        plot_values = ["Select Plot Type", "Residential", "Industrial"]

        ctk.CTkLabel(control_card, text="City", text_color=TEXT_DARK).grid(row=0, column=0, padx=10, pady=(10, 4))
        ctk.CTkLabel(control_card, text="Plot Type", text_color=TEXT_DARK).grid(row=0, column=1, padx=10, pady=(10, 4))
        city_menu = ctk.CTkOptionMenu(control_card, values=city_values, variable=selected_city, width=220)
        plot_menu = ctk.CTkOptionMenu(control_card, values=plot_values, variable=selected_plot, width=220)
        city_menu.grid(row=1, column=0, padx=10, pady=(0, 10))
        plot_menu.grid(row=1, column=1, padx=10, pady=(0, 10))

        caption = ctk.CTkLabel(page, text="Please select both city and plot type to view graphs.", font=("Arial", 14), text_color="#52616B")
        caption.pack(pady=8)
        graphs_frame = ctk.CTkFrame(page, fg_color=CONTENT_BG, corner_radius=0)
        graphs_frame.pack(pady=8, fill="x")

        def make_graph(title, x_values, y_values, x_label, y_label):
            card = ctk.CTkFrame(graphs_frame, fg_color=CARD_BG, corner_radius=16)
            card.pack(padx=30, pady=12, fill="x")
            ctk.CTkLabel(card, text=title, font=("Arial", 18, "bold"), text_color=TEXT_DARK).pack(pady=(12, 4))

            fig = Figure(figsize=(8.6, 3.6), facecolor="white")
            ax = fig.add_subplot(111)
            ax.plot(x_values, y_values, color=PRIMARY, linewidth=2.8, marker="o", markersize=7)
            ax.set_xlabel(x_label, fontsize=9)
            ax.set_ylabel(y_label, fontsize=9)
            ax.tick_params(axis="both", labelsize=8)
            ax.grid(True, alpha=0.3)
            fig.subplots_adjust(left=0.10, right=0.97, top=0.92, bottom=0.20)
            canvas = FigureCanvasTkAgg(fig, master=card)
            canvas.draw()
            canvas.get_tk_widget().pack(padx=14, pady=(0, 14), fill="x")

        def draw_graphs():
            for widget in graphs_frame.winfo_children():
                widget.destroy()

            city = selected_city.get()
            plot_type = selected_plot.get()
            if city == "Select City" or plot_type == "Select Plot Type":
                caption.configure(text="Please select both city and plot type to view graphs.")
                return

            caption.configure(text=f"Graphs for {city} and {plot_type} plot using market rate: Rs. {MARKET_RATE_PER_SQFT[city]:,.0f} per sqft.")
            sqft_values = list(range(500, 5000, 500))
            room_values = list(range(1, 7))
            floor_values = list(range(1, 5))
            age_values = list(range(0, 31, 5))
            make_graph("Price by Square Feet", sqft_values, [calculate_price(s, 3, 2, 1, 5, plot_type, city) / 100000 for s in sqft_values], "Square Feet", "Price in Lakhs")
            make_graph("Price by Rooms", room_values, [calculate_price(1500, r, 2, 1, 5, plot_type, city) / 100000 for r in room_values], "Rooms", "Price in Lakhs")
            make_graph("Price by Floors", floor_values, [calculate_price(1500, 3, 2, f, 5, plot_type, city) / 100000 for f in floor_values], "Floors", "Price in Lakhs")
            make_graph("Price by Age", age_values, [calculate_price(1500, 3, 2, 1, a, plot_type, city) / 100000 for a in age_values], "Age in Years", "Price in Lakhs")

        city_menu.configure(command=lambda value: draw_graphs())
        plot_menu.configure(command=lambda value: draw_graphs())
        bind_focus_keys([city_menu, plot_menu])
        bind_option_arrows(city_menu, selected_city, city_values, draw_graphs)
        bind_option_arrows(plot_menu, selected_plot, plot_values, draw_graphs)
        bind_enter(city_menu, draw_graphs)
        bind_enter(plot_menu, draw_graphs)
        city_menu.focus_set()
        draw_graphs()

    def price_text(record):
        if "predicted_price" in record:
            return f"Rs. {record['predicted_price']:,.2f}"
        return record.get("predicted_price_text", "Price unavailable")

    def show_report_page(record):
        clear_content()

        page = ctk.CTkScrollableFrame(content, fg_color=CONTENT_BG, corner_radius=0)
        page.pack(expand=True, fill="both")

        top_bar = ctk.CTkFrame(page, fg_color=CONTENT_BG)
        top_bar.pack(fill="x", padx=36, pady=(18, 8))

        back_btn = ctk.CTkButton(
            top_bar,
            text="Back to History",
            command=history,
            width=150,
            height=38,
            fg_color=SIDEBAR_BG,
            hover_color="#164B78",
            font=("Arial", 14, "bold"),
        )
        back_btn.pack(side="left")

        ctk.CTkLabel(
            top_bar,
            text=f"Property Report - {record.get('city', 'Property')}",
            font=("Arial", 30, "bold"),
            text_color=TEXT_DARK,
        ).pack(side="left", padx=26)

        report = ctk.CTkFrame(page, width=940, fg_color=CARD_BG, corner_radius=18)
        report.pack(padx=36, pady=(8, 22))

        header = ctk.CTkFrame(report, fg_color=SIDEBAR_BG, corner_radius=18)
        header.pack(fill="x", padx=18, pady=(18, 12))
        ctk.CTkLabel(header, text="HOUSE PRICE PREDICTION REPORT", font=("Arial", 24, "bold"), text_color="white").pack(anchor="w", padx=24, pady=(18, 2))
        ctk.CTkLabel(
            header,
            text=f"Generated On: {record.get('date', 'Not available')}    |    Name: {current_user.get('name', current_user['username'])}    |    User: {current_user['username']}    |    Mobile: {current_user['mobile']}",
            font=("Arial", 14),
            text_color="#BAE6FD",
        ).pack(anchor="w", padx=24, pady=(0, 18))

        def section(title, color):
            frame = ctk.CTkFrame(report, fg_color="#F8FAFC", corner_radius=14, border_width=1, border_color="#D9EAFD")
            frame.pack(fill="x", padx=18, pady=10)
            ctk.CTkLabel(frame, text=title, font=("Arial", 20, "bold"), text_color=color).pack(anchor="w", padx=22, pady=(16, 8))
            body = ctk.CTkFrame(frame, fg_color="#F8FAFC")
            body.pack(fill="x", padx=0, pady=(0, 14))
            return body

        def add_row(parent, label, value, row, value_color=TEXT_DARK):
            ctk.CTkLabel(parent, text=label, font=("Arial", 15, "bold"), text_color="#334155", width=210, anchor="w").grid(row=row, column=0, padx=(24, 10), pady=6, sticky="w")
            ctk.CTkLabel(parent, text=value, font=("Arial", 15), text_color=value_color, width=540, anchor="w", wraplength=540).grid(row=row, column=1, padx=(8, 24), pady=6, sticky="w")

        details = section("PROPERTY DETAILS", PRIMARY)
        if record.get("legacy"):
            rows = [
                ("City / Area", record.get("city", "Not available")),
                ("Plot Type", record.get("plot_type", "Not available")),
                ("House Size", record.get("sqft_text", "Not available")),
            ]
        else:
            rows = [
                ("City / Area", record["city"]),
                ("Plot Type", record["plot_type"]),
                ("Market Rate", f"Rs. {record['rate']:,.0f} per sqft"),
                ("House Size", f"{record['sqft']:,.0f} sqft"),
                ("Rooms", f"{record['rooms']:,.0f}"),
                ("Bathrooms", f"{record['bathrooms']:,.0f}"),
                ("Floors", f"{record['floors']:,.0f}"),
                ("House Age", f"{record['age']:,.0f} years"),
            ]
        for row, (label, value) in enumerate(rows):
            add_row(details, label, value, row)

        price = section("PRICE RESULT", ACCENT)
        add_row(price, "Predicted Price", price_text(record), 0, value_color="#16A34A")

        breakup = section("PRICE BREAKUP", "#16A34A")
        if record.get("legacy"):
            add_row(
                breakup,
                "Available Details",
                "This older history entry was saved before full details were stored. New predictions will show the complete colorful report here.",
                0,
            )
        else:
            parts = record["parts"]
            breakup_rows = [
                ("House Size Value", f"Rs. {parts['House size value']:,.2f}"),
                ("Rooms Added Value", f"Rs. {parts['Rooms added value']:,.2f}"),
                ("Bathrooms Value", f"Rs. {parts['Bathrooms added value']:,.2f}"),
                ("Floors Added Value", f"Rs. {parts['Floors added value']:,.2f}"),
                ("Age Discount", f"Rs. {parts['Old house discount']:,.2f}"),
                ("Final Price", f"Rs. {parts['Final price']:,.2f}"),
            ]
            for row, (label, value) in enumerate(breakup_rows):
                color = DANGER if label == "Age Discount" else "#16A34A" if label == "Final Price" else TEXT_DARK
                add_row(breakup, label, value, row, value_color=color)

        bind_enter(back_btn, history)
        back_btn.focus_set()

    def history():
        clear_content()
        ctk.CTkLabel(content, text=f"Prediction History - {current_user['username']}", font=("Arial", 30, "bold"), text_color=TEXT_DARK).pack(pady=(18, 8))

        def clear_history():
            path = history_file()
            if not os.path.exists(path):
                return messagebox.showinfo("History", "Your history is already empty")
            if messagebox.askyesno("Clear History", "Are you sure you want to clear your prediction history?"):
                open(path, "w", encoding="utf-8").close()
                messagebox.showinfo("Success", "History cleared successfully")
                history()

        clear_btn = ctk.CTkButton(content, text="Clear My History", command=clear_history, width=180, height=38, fg_color=DANGER, hover_color=DANGER_HOVER, font=("Arial", 14, "bold"))
        clear_btn.pack(pady=(0, 10))

        controls = ctk.CTkFrame(content, fg_color=CARD_BG, corner_radius=16)
        controls.pack(pady=(0, 8), padx=40)

        search_var = ctk.StringVar()
        city_var = ctk.StringVar(value="All Cities")
        plot_var = ctk.StringVar(value="All Plot Types")
        price_var = ctk.StringVar(value="All Prices")

        ctk.CTkLabel(controls, text="Search", font=("Arial", 13, "bold"), text_color=TEXT_DARK).pack(side="left", padx=(14, 4), pady=12)
        search_entry = ctk.CTkEntry(controls, placeholder_text="City, date, or price", textvariable=search_var, width=220, height=34)
        ctk.CTkLabel(controls, text="City", font=("Arial", 13, "bold"), text_color=TEXT_DARK).pack(side="left", padx=(10, 4), pady=12)
        city_filter = ctk.CTkOptionMenu(controls, values=["All Cities"] + ALL_CITIES, variable=city_var, width=160)
        ctk.CTkLabel(controls, text="Plot", font=("Arial", 13, "bold"), text_color=TEXT_DARK).pack(side="left", padx=(10, 4), pady=12)
        plot_filter = ctk.CTkOptionMenu(controls, values=["All Plot Types", "Residential", "Industrial"], variable=plot_var, width=160)
        ctk.CTkLabel(controls, text="Price", font=("Arial", 13, "bold"), text_color=TEXT_DARK).pack(side="left", padx=(10, 4), pady=12)
        price_filter = ctk.CTkOptionMenu(
            controls,
            values=["All Prices", "Below 50 Lakh", "50 Lakh - 1 Crore", "Above 1 Crore"],
            variable=price_var,
            width=170,
        )
        apply_btn = ctk.CTkButton(controls, text="Apply", width=80, height=34, fg_color=PRIMARY, hover_color=PRIMARY_HOVER)

        for widget in [search_entry, city_filter, plot_filter, price_filter, apply_btn]:
            widget.pack(side="left", padx=6, pady=12)

        history_card = ctk.CTkScrollableFrame(content, width=940, height=500, fg_color=CARD_BG, corner_radius=16)
        history_card.pack(pady=(0, 14), padx=40)

        def filtered_records():
            records = list(reversed(read_history_records()))
            query = search_var.get().strip().lower()
            selected_city = city_var.get()
            selected_plot = plot_var.get()
            selected_price = price_var.get()

            result = []
            for record in records:
                searchable = " ".join([
                    record.get("date", ""),
                    record.get("city", ""),
                    record.get("plot_type", ""),
                    price_text(record),
                ]).lower()
                value = price_number(record)
                if query and query not in searchable:
                    continue
                if selected_city != "All Cities" and record.get("city") != selected_city:
                    continue
                if selected_plot != "All Plot Types" and record.get("plot_type") != selected_plot:
                    continue
                if selected_price == "Below 50 Lakh" and value >= 5000000:
                    continue
                if selected_price == "50 Lakh - 1 Crore" and not (5000000 <= value <= 10000000):
                    continue
                if selected_price == "Above 1 Crore" and value <= 10000000:
                    continue
                result.append(record)
            return result

        def draw_history_table():
            for widget in history_card.winfo_children():
                widget.destroy()

            ctk.CTkLabel(
                history_card,
                text="Click a city name to open the full colorful property report.",
                font=("Arial", 14),
                text_color="#52616B",
            ).grid(row=0, column=0, columnspan=3, padx=18, pady=(14, 8))

            headers = [("Date & Time", 260), ("City Name", 250), ("Predicted Price", 250)]
            for column, (header, width) in enumerate(headers):
                ctk.CTkLabel(
                    history_card,
                    text=header,
                    font=("Arial", 15, "bold"),
                    text_color="white",
                    fg_color=SIDEBAR_BG,
                    corner_radius=8,
                    width=width,
                    height=36,
                ).grid(row=1, column=column, padx=8, pady=(8, 8), sticky="ew")

            records = filtered_records()
            if not records:
                ctk.CTkLabel(
                    history_card,
                    text="No matching history found",
                    font=("Arial", 15),
                    text_color=TEXT_DARK,
                ).grid(row=2, column=0, columnspan=3, padx=70, pady=25)
                return

            for row, record in enumerate(records, start=2):
                row_bg = "#F8FAFC" if row % 2 else "#EAF7FF"
                ctk.CTkLabel(
                    history_card,
                    text=record.get("date", "Not available"),
                    font=("Arial", 14),
                    text_color="#0F172A",
                    fg_color=row_bg,
                    corner_radius=8,
                    width=260,
                    height=38,
                ).grid(row=row, column=0, padx=8, pady=4, sticky="ew")
                ctk.CTkButton(
                    history_card,
                    text=record.get("city", "View details"),
                    command=lambda selected=record: show_report_page(selected),
                    font=("Arial", 14, "bold"),
                    fg_color=row_bg,
                    hover_color="#D9EAFD",
                    text_color=PRIMARY,
                    width=250,
                    height=38,
                    corner_radius=8,
                ).grid(row=row, column=1, padx=8, pady=4, sticky="ew")
                ctk.CTkLabel(
                    history_card,
                    text=price_text(record),
                    font=("Arial", 14),
                    text_color="#0F172A",
                    fg_color=row_bg,
                    corner_radius=8,
                    width=250,
                    height=38,
                ).grid(row=row, column=2, padx=8, pady=4, sticky="ew")

        apply_btn.configure(command=draw_history_table)
        for widget in [search_entry, apply_btn]:
            bind_enter(widget, draw_history_table)
        city_filter.configure(command=lambda value: draw_history_table())
        plot_filter.configure(command=lambda value: draw_history_table())
        price_filter.configure(command=lambda value: draw_history_table())
        draw_history_table()

    def profile():
        clear_content()
        page = ctk.CTkFrame(content, fg_color=CONTENT_BG, corner_radius=0)
        page.pack(expand=True, fill="both")
        ctk.CTkLabel(page, text="My Profile", font=("Arial", 32, "bold"), text_color=TEXT_DARK).pack(pady=(30, 12))

        card = ctk.CTkFrame(page, width=600, height=620, fg_color=CARD_BG, corner_radius=18)
        card.pack(pady=10)
        card.pack_propagate(False)
        ctk.CTkLabel(card, text="User Details", font=("Arial", 24, "bold"), text_color=TEXT_DARK).pack(pady=(26, 12))
        name_label = ctk.CTkLabel(card, text=f"Name: {current_user.get('name', current_user['username'])}", font=("Arial", 17), text_color=TEXT_DARK)
        username_label = ctk.CTkLabel(card, text=f"Username: {current_user['username']}", font=("Arial", 17), text_color=TEXT_DARK)
        mobile_label = ctk.CTkLabel(card, text=f"Mobile Number: {current_user['mobile']}", font=("Arial", 17), text_color=TEXT_DARK)
        name_label.pack(pady=5)
        username_label.pack(pady=5)
        mobile_label.pack(pady=5)

        ctk.CTkFrame(card, width=420, height=2, fg_color="#D9EAFD").pack(pady=18)

        edit_area = ctk.CTkFrame(card, fg_color=CARD_BG)
        edit_area.pack(fill="x")
        edit_fields = ctk.CTkFrame(edit_area, fg_color=CARD_BG)

        edit_name = ctk.CTkEntry(edit_fields, placeholder_text="Full Name", width=320, height=38)
        edit_username = ctk.CTkEntry(edit_fields, placeholder_text="New Username", width=320, height=38)
        edit_mobile = ctk.CTkEntry(edit_fields, placeholder_text="New Mobile Number", width=320, height=38)

        def save_profile_changes():
            new_name = edit_name.get().strip()
            new_username = edit_username.get().strip()
            new_mobile = edit_mobile.get().strip()
            if not new_name or not new_username or not new_mobile:
                return messagebox.showerror("Error", "Enter name, username, and mobile number")

            users = read_users()
            old_username = current_user["username"]
            if new_username != old_username and any(user["username"] == new_username for user in users):
                return messagebox.showerror("Error", "Username already exists")

            for saved_user in users:
                if saved_user["username"] == old_username:
                    saved_user["name"] = new_name
                    saved_user["username"] = new_username
                    saved_user["mobile"] = new_mobile
                    write_users(users)
                    move_user_files(old_username, new_username)
                    current_user["name"] = new_name
                    current_user["username"] = new_username
                    current_user["mobile"] = new_mobile
                    messagebox.showinfo("Success", "Profile updated successfully")
                    show_dashboard()
                    return

            messagebox.showerror("Error", "User not found")

        save_profile_btn = ctk.CTkButton(edit_fields, text="Save Profile", command=save_profile_changes, width=320, height=38, fg_color=PRIMARY, hover_color=PRIMARY_HOVER)

        def show_edit_fields():
            open_edit_btn.pack_forget()
            edit_name.insert(0, current_user.get("name", current_user["username"]))
            edit_username.insert(0, current_user["username"])
            edit_mobile.insert(0, current_user["mobile"])
            ctk.CTkLabel(edit_fields, text="Edit Profile", font=("Arial", 20, "bold"), text_color=PRIMARY).pack(pady=(0, 8))
            edit_name.pack(pady=5)
            edit_username.pack(pady=5)
            edit_mobile.pack(pady=5)
            save_profile_btn.pack(pady=(10, 12))
            edit_fields.pack(fill="x")
            edit_name.focus_set()

        open_edit_btn = ctk.CTkButton(
            edit_area,
            text="Edit Profile",
            command=show_edit_fields,
            width=320,
            height=40,
            fg_color=PRIMARY,
            hover_color=PRIMARY_HOVER,
            font=("Arial", 15, "bold"),
        )
        open_edit_btn.pack(pady=(0, 10))

        password_area = ctk.CTkFrame(card, fg_color=CARD_BG)
        password_area.pack(fill="x")
        password_fields = ctk.CTkFrame(password_area, fg_color=CARD_BG)

        old_pwd = ctk.CTkEntry(password_fields, placeholder_text="Current Password", show="*", width=320, height=38)
        new_pwd = ctk.CTkEntry(password_fields, placeholder_text="New Password", show="*", width=320, height=38)
        confirm_pwd = ctk.CTkEntry(password_fields, placeholder_text="Repeat New Password", show="*", width=320, height=38)

        def change_password():
            if not all([old_pwd.get(), new_pwd.get(), confirm_pwd.get()]):
                return messagebox.showerror("Error", "Fill all password fields")
            if new_pwd.get() != confirm_pwd.get():
                return messagebox.showerror("Error", "New passwords do not match")

            users = read_users()
            for saved_user in users:
                if saved_user["username"] == current_user["username"]:
                    if saved_user["password"] != old_pwd.get():
                        return messagebox.showerror("Error", "Current password is wrong")
                    saved_user["password"] = new_pwd.get()
                    write_users(users)
                    old_pwd.delete(0, "end")
                    new_pwd.delete(0, "end")
                    confirm_pwd.delete(0, "end")
                    return messagebox.showinfo("Success", "Password changed successfully")

            messagebox.showerror("Error", "User not found")

        update_btn = ctk.CTkButton(password_fields, text="Update Password", command=change_password, width=320, height=40, fg_color=PRIMARY, hover_color=PRIMARY_HOVER)

        def show_password_fields():
            open_change_btn.pack_forget()
            ctk.CTkLabel(password_fields, text="Change Password", font=("Arial", 22, "bold"), text_color=PRIMARY).pack(pady=(0, 10))
            for entry in [old_pwd, new_pwd, confirm_pwd]:
                entry.pack(pady=5)
            update_btn.pack(pady=(12, 10))
            password_fields.pack(fill="x")
            old_pwd.focus_set()

        open_change_btn = ctk.CTkButton(
            password_area,
            text="Change Password",
            command=show_password_fields,
            width=320,
            height=42,
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            font=("Arial", 15, "bold"),
        )
        open_change_btn.pack(pady=(14, 10))

        def delete_account():
            if not messagebox.askyesno("Delete Account", "Delete this account, history, and saved reports permanently?"):
                return
            if not messagebox.askyesno("Confirm Delete", "This cannot be undone. Are you completely sure?"):
                return

            username = current_user["username"]
            users = [user for user in read_users() if user["username"] != username]
            write_users(users)

            path = history_file_for(username)
            if os.path.exists(path):
                os.remove(path)
            folder = report_folder_name(username)
            if os.path.exists(folder):
                shutil.rmtree(folder)

            messagebox.showinfo("Deleted", "Account deleted successfully")
            show_login()

        delete_btn = ctk.CTkButton(
            card,
            text="Delete Account",
            command=delete_account,
            width=320,
            height=40,
            fg_color=DANGER,
            hover_color=DANGER_HOVER,
            font=("Arial", 15, "bold"),
        )
        delete_btn.pack(pady=(4, 0))

        widgets = [open_edit_btn, edit_name, edit_username, edit_mobile, save_profile_btn, open_change_btn, old_pwd, new_pwd, confirm_pwd, update_btn, delete_btn]
        bind_focus_keys(widgets)
        bind_enter(open_edit_btn, show_edit_fields)
        for widget in [edit_name, edit_username, edit_mobile, save_profile_btn]:
            bind_enter(widget, save_profile_changes)
        bind_enter(open_change_btn, show_password_fields)
        for widget in [old_pwd, new_pwd, confirm_pwd, update_btn]:
            bind_enter(widget, change_password)
        bind_enter(delete_btn, delete_account)
        open_edit_btn.focus_set()

    ctk.CTkLabel(sidebar, text="HOUSE PRICE", font=("Arial", 20, "bold"), text_color="white").pack(pady=(28, 4))
    ctk.CTkLabel(sidebar, text="Prediction System", font=("Arial", 12), text_color="#D9EAFD").pack(pady=(0, 10))
    ctk.CTkLabel(sidebar, text=f"User: {current_user['username']}", font=("Arial", 12, "bold"), text_color="#FDBA74").pack(pady=(0, 14))

    theme_btn = ctk.CTkButton(
        sidebar,
        text="Dark Mode" if current_theme["mode"] == "light" else "Light Mode",
        command=switch_theme,
        height=34,
        corner_radius=10,
        fg_color=ACCENT,
        hover_color=ACCENT_HOVER,
        text_color="white",
        font=("Arial", 13, "bold"),
    )
    theme_btn.pack(pady=(0, 12), padx=16, fill="x")

    sidebar_buttons = [theme_btn]
    for text, command in [
        ("Home", home),
        ("Predict Price", predict),
        ("Locations", locations),
        ("History", history),
        ("Graph", graph),
        ("Profile", profile),
        ("Logout", show_login),
    ]:
        button = ctk.CTkButton(sidebar, text=text, command=command, height=40, corner_radius=10, fg_color="#FFFFFF", hover_color="#D9EAFD", text_color=SIDEBAR_BG, font=("Arial", 14, "bold"))
        button.pack(pady=6, padx=16, fill="x")
        bind_enter(button, command)
        sidebar_buttons.append(button)

    bind_focus_keys(sidebar_buttons)
    home()


show_login()
app.mainloop()
