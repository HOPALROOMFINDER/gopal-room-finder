from flask import Flask, request, redirect, render_template_string, send_from_directory, session
import sqlite3
import os
import uuid
from werkzeug.utils import secure_filename


app = Flask(__name__)

app.secret_key = "gopal-room-finder-secret-key"

DATABASE = "rooms.db"
UPLOAD_FOLDER = "uploads"

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# =========================================================
# DATABASE
# =========================================================

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():

    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS owners (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            mobile TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_name TEXT NOT NULL,
            mobile TEXT NOT NULL,
            location TEXT NOT NULL,
            room_type TEXT NOT NULL,
            rent INTEGER NOT NULL,
            deposit INTEGER,
            furnished TEXT,
            description TEXT,
            map_link TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS room_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id INTEGER NOT NULL,
            filename TEXT NOT NULL
        )
    """)

    columns = conn.execute(
        "PRAGMA table_info(rooms)"
    ).fetchall()

    column_names = [column["name"] for column in columns]

    if "map_link" not in column_names:

        conn.execute(
            "ALTER TABLE rooms ADD COLUMN map_link TEXT"
        )

    conn.commit()
    conn.close()


def allowed_file(filename):

    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in ALLOWED_EXTENSIONS
    )


# =========================================================
# IMAGE HELPER
# =========================================================

@app.context_processor
def utility_processor():

    def get_images(room_id):

        conn = get_db()

        images = conn.execute("""
            SELECT *
            FROM room_images
            WHERE room_id = ?
            ORDER BY id ASC
        """, (
            room_id,
        )).fetchall()

        conn.close()

        return images

    return dict(get_images=get_images)


# =========================================================
# HOME / SEARCH
# =========================================================

@app.route("/", methods=["GET"])
def home():

    owner = None

    owner_id = session.get("owner_id")

    if owner_id:

        conn = get_db()

        owner = conn.execute("""
            SELECT *
            FROM owners
            WHERE id = ?
        """, (
            owner_id,
        )).fetchone()

        conn.close()

    location = request.args.get(
        "location",
        ""
    ).strip()

    max_rent = request.args.get(
        "max_rent",
        ""
    ).strip()

    room_type = request.args.get(
        "room_type",
        ""
    ).strip()

    conn = get_db()

    query = """
        SELECT *
        FROM rooms
        WHERE 1 = 1
    """

    params = []

    if location:

        query += """
            AND location LIKE ?
        """

        params.append(
            "%" + location + "%"
        )

    if max_rent:

        try:

            max_rent_value = int(max_rent)

            query += """
                AND rent <= ?
            """

            params.append(
                max_rent_value
            )

        except ValueError:

            pass

    if room_type:

        query += """
            AND room_type = ?
        """

        params.append(
            room_type
        )

    query += """
        ORDER BY id DESC
    """

    rooms = conn.execute(
        query,
        params
    ).fetchall()

    conn.close()

    return render_template_string("""
<!DOCTYPE html>

<html lang="hi">

<head>

<meta charset="UTF-8">

<meta name="viewport"
content="width=device-width, initial-scale=1.0">

<title>Gopal Room Finder - Room Rent Search</title>

<meta name="description"
content="Gopal Room Finder पर अपने शहर में Room, 1 BHK, 2 BHK, PG और Hostel खोजें।">

<style>

body {
    font-family: Arial, sans-serif;
    background: #f5f5f5;
    margin: 0;
    padding: 20px;
}

.box {
    max-width: 900px;
    margin: auto;
    background: white;
    padding: 20px;
    border-radius: 10px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
}

h1 {
    text-align: center;
    color: #1565c0;
}

input,
select,
textarea {
    width: 100%;
    padding: 10px;
    margin-top: 6px;
    margin-bottom: 12px;
    box-sizing: border-box;
    border: 1px solid #ccc;
    border-radius: 6px;
}

button,
.button {
    display: inline-block;
    padding: 10px 15px;
    background: #1565c0;
    color: white;
    text-decoration: none;
    border: none;
    border-radius: 6px;
    cursor: pointer;
}

.top-links {
    text-align: center;
    margin-bottom: 20px;
}

.top-links a {
    margin: 5px;
}

.room {
    border: 1px solid #ddd;
    padding: 15px;
    margin-top: 15px;
    border-radius: 8px;
    background: white;
}

.room img {
    width: 100%;
    max-width: 300px;
    height: 200px;
    object-fit: cover;
    border-radius: 8px;
    margin: 5px;
}

.whatsapp {
    background: #25D366 !important;
}

.map {
    background: #ff9800 !important;
}

</style>

</head>

<body>

<div class="box">

<h1>🏠 Gopal Room Finder</h1>

<div class="top-links">

{% if owner %}

<a class="button"
href="/dashboard">
👤 Owner Dashboard
</a>

<a class="button"
href="/logout"
style="background:#d32f2f;">
🚪 Logout
</a>

{% else %}

<a class="button"
href="/login">
🔐 Owner Login
</a>

<a class="button"
href="/register">
📝 Owner Register
</a>

{% endif %}

</div>

<hr>

<h2>🔎 Room Search</h2>

<form method="GET"
action="/">

<label>📍 Location</label>

<input
type="text"
name="location"
value="{{ location }}"
placeholder="जैसे Dausa, Agra Road"
>

<label>💰 Maximum Rent</label>

<input
type="number"
name="max_rent"
value="{{ max_rent }}"
placeholder="जैसे 5000"
>

<label>🏠 Room Type</label>

<select name="room_type">

<option value="">
सभी Room
</option>

<option value="Single Room"
{% if room_type == "Single Room" %}selected{% endif %}>
Single Room
</option>

<option value="1 BHK"
{% if room_type == "1 BHK" %}selected{% endif %}>
1 BHK
</option>

<option value="2 BHK"
{% if room_type == "2 BHK" %}selected{% endif %}>
2 BHK
</option>

<option value="PG"
{% if room_type == "PG" %}selected{% endif %}>
PG
</option>

<option value="Hostel"
{% if room_type == "Hostel" %}selected{% endif %}>
Hostel
</option>

</select>

<button type="submit">
🔎 Search
</button>

<a
href="/"
class="button"
style="background:#777;">
Reset
</a>

</form>

<hr>

<h2>🏠 Available Rooms</h2>

{% if rooms %}

{% for room in rooms %}

<div class="room">

<h3>
{{ room["room_type"] }}
</h3>

<p>
📍 <b>Location:</b>
{{ room["location"] }}
</p>

<p>
💰 <b>Rent:</b>
₹{{ room["rent"] }}
</p>

{% if room["deposit"] %}

<p>
💵 <b>Deposit:</b>
₹{{ room["deposit"] }}
</p>

{% endif %}

{% if room["furnished"] %}

<p>
🛋 <b>Furnished:</b>
{{ room["furnished"] }}
</p>

{% endif %}

{% if room["description"] %}

<p>
📝 {{ room["description"] }}
</p>

{% endif %}

<div>

{% for image in get_images(room["id"]) %}

<img
src="/uploads/{{ image['filename'] }}"
alt="Room Photo"
>

{% endfor %}

</div>

{% if room["map_link"] %}

<p>

<a
href="{{ room['map_link'] }}"
target="_blank"
class="button map">
📍 Google Map
</a>

</p>

{% endif %}

<a
href="https://wa.me/91{{ room['mobile'] }}?text=Namaste,%20mujhe%20aapke%20Room%20ke%20baare%20mein%20jaankari%20chahiye."
target="_blank"
class="button whatsapp">
💬 WhatsApp Owner
</a>

</div>

{% endfor %}

{% else %}

<p>
❌ कोई Room नहीं मिला।
</p>

{% endif %}

</div>

</body>

</html>
""",
        owner=owner,
        rooms=rooms,
        location=location,
        max_rent=max_rent,
        room_type=room_type
    )


# =========================================================
# ADD ROOM
# =========================================================

@app.route("/add_room", methods=["GET", "POST"])
def add_room():

    owner_id = session.get("owner_id")

    if not owner_id:
        return redirect("/login")

    conn = get_db()

    owner = conn.execute("""
        SELECT *
        FROM owners
        WHERE id = ?
    """, (
        owner_id,
    )).fetchone()

    conn.close()

    if not owner:

        session.clear()

        return redirect("/login")

    if request.method == "POST":

        location = request.form.get(
            "location",
            ""
        ).strip()

        room_type = request.form.get(
            "room_type",
            ""
        ).strip()

        rent = request.form.get(
            "rent",
            ""
        ).strip()

        deposit = request.form.get(
            "deposit",
            ""
        ).strip()

        furnished = request.form.get(
            "furnished",
            ""
        ).strip()

        description = request.form.get(
            "description",
            ""
        ).strip()

        map_link = request.form.get(
            "map_link",
            ""
        ).strip()

        if not location or not room_type or not rent:

            return """
            Location, Room Type और Rent जरूरी हैं।
            <br><br>
            <a href="/add_room">Back</a>
            """

        try:

            rent = int(rent)

        except ValueError:

            return """
            Rent सही संख्या में डालें।
            <br><br>
            <a href="/add_room">Back</a>
            """

        if deposit:

            try:

                deposit = int(deposit)

            except ValueError:

                return """
                Deposit सही संख्या में डालें।
                <br><br>
                <a href="/add_room">Back</a>
                """

        else:

            deposit = None

        conn = get_db()

        cursor = conn.execute("""
            INSERT INTO rooms
            (
                owner_name,
                mobile,
                location,
                room_type,
                rent,
                deposit,
                furnished,
                description,
                map_link
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            owner["name"],
            owner["mobile"],
            location,
            room_type,
            rent,
            deposit,
            furnished,
            description,
            map_link
        ))

        room_id = cursor.lastrowid

        files = request.files.getlist(
            "photos"
        )

        photo_count = 0

        for file in files:

            if photo_count >= 10:
                break

            if (
                file
                and file.filename
                and allowed_file(file.filename)
            ):

                original_name = secure_filename(
                    file.filename
                )

                extension = original_name.rsplit(
                    ".",
                    1
                )[1].lower()

                filename = (
                    str(uuid.uuid4())
                    + "."
                    + extension
                )

                filepath = os.path.join(
                    UPLOAD_FOLDER,
                    filename
                )

                file.save(filepath)

                conn.execute("""
                    INSERT INTO room_images
                    (
                        room_id,
                        filename
                    )
                    VALUES (?, ?)
                """, (
                    room_id,
                    filename
                ))

                photo_count += 1

        conn.commit()

        conn.close()

        return redirect("/dashboard")

    return render_template_string("""
<!DOCTYPE html>

<html lang="hi">

<head>

<meta charset="UTF-8">

<meta name="viewport"
content="width=device-width, initial-scale=1.0">

<title>Add Room - Gopal Room Finder</title>

<style>

body {
    font-family: Arial;
    background: #f5f5f5;
    padding: 20px;
}

.box {
    max-width: 700px;
    margin: auto;
    background: white;
    padding: 20px;
    border-radius: 10px;
}

input,
select,
textarea {
    width: 100%;
    padding: 10px;
    margin-top: 6px;
    margin-bottom: 12px;
    box-sizing: border-box;
}

button,
a {
    display: inline-block;
    padding: 10px 15px;
    background: #1565c0;
    color: white;
    text-decoration: none;
    border: none;
    border-radius: 6px;
}

</style>

</head>

<body>

<div class="box">

<h2>➕ नया Room जोड़ें</h2>

<p>
Owner:
<b>{{ owner["name"] }}</b>
</p>

<form method="POST"
enctype="multipart/form-data">

<label>Owner Name</label>

<input
type="text"
value="{{ owner['name'] }}"
readonly
>

<label>Mobile</label>

<input
type="text"
value="{{ owner['mobile'] }}"
readonly
>

<label>📍 Location</label>

<input
type="text"
name="location"
required
placeholder="जैसे Agra Road Dausa"
>

<label>🏠 Room Type</label>

<select name="room_type" required>

<option value="">
Select Room Type
</option>

<option value="Single Room">
Single Room
</option>

<option value="1 BHK">
1 BHK
</option>

<option value="2 BHK">
2 BHK
</option>

<option value="PG">
PG
</option>

<option value="Hostel">
Hostel
</option>

</select>

<label>💰 Rent (₹)</label>

<input
type="number"
name="rent"
required
>

<label>💵 Deposit (₹)</label>

<input
type="number"
name="deposit"
>

<label>🛋 Furnished</label>

<select name="furnished">

<option value="">
Select
</option>

<option value="Fully Furnished">
Fully Furnished
</option>

<option value="Semi Furnished">
Semi Furnished
</option>

<option value="Unfurnished">
Unfurnished
</option>

</select>

<label>📝 Description</label>

<textarea
name="description"
rows="5"
placeholder="Room की जानकारी लिखें">
</textarea>

<label>📍 Google Maps Link</label>

<input
type="url"
name="map_link"
placeholder="https://maps.google.com/...">

<label>📷 Room Photos</label>

<input
type="file"
name="photos"
multiple
accept=".jpg,.jpeg,.png,.webp"
>

<p>
अधिकतम 10 Photos upload कर सकते हैं।
</p>

<button type="submit">
💾 Room Save करें
</button>

<a
href="/dashboard"
style="background:#777;">
Back
</a>

</form>

</div>

</body>

</html>
""",
        owner=owner
    )


# =========================================================
# UPLOADS
# =========================================================

@app.route("/uploads/<filename>")
def uploaded_file(filename):

    return send_from_directory(
        UPLOAD_FOLDER,
        filename
    )


# =========================================================
# REGISTER
# =========================================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        mobile = request.form.get(
            "mobile",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        ).strip()

        if not name or not mobile or not password:

            return """
            सभी जानकारी भरें।
            <br><br>
            <a href="/register">Back</a>
            """

        conn = get_db()

        try:

            conn.execute("""
                INSERT INTO owners
                (
                    name,
                    mobile,
                    password
                )
                VALUES (?, ?, ?)
            """, (
                name,
                mobile,
                password
            ))

            conn.commit()

            conn.close()

            return redirect("/login")

        except sqlite3.IntegrityError:

            conn.close()

            return """
            यह Mobile Number पहले से Registered है।
            <br><br>
            <a href="/login">Login करें</a>
            """

    return render_template_string("""
<!DOCTYPE html>

<html lang="hi">

<head>

<meta charset="UTF-8">

<meta name="viewport"
content="width=device-width, initial-scale=1.0">

<title>Owner Register - Gopal Room Finder</title>

<style>

body {
    font-family: Arial;
    background: #f5f5f5;
    padding: 20px;
}

.box {
    max-width: 500px;
    margin: auto;
    background: white;
    padding: 20px;
    border-radius: 10px;
}

input {
    width: 100%;
    padding: 10px;
    margin: 8px 0 15px;
    box-sizing: border-box;
}

button,
a {
    display: inline-block;
    padding: 10px 15px;
    background: #1565c0;
    color: white;
    border: none;
    border-radius: 6px;
    text-decoration: none;
}

</style>

</head>

<body>

<div class="box">

<h2>📝 Owner Registration</h2>

<form method="POST">

<label>Name</label>

<input
type="text"
name="name"
required
>

<label>Mobile</label>

<input
type="text"
name="mobile"
required
>

<label>Password</label>

<input
type="password"
name="password"
required
>

<button type="submit">
Register
</button>

<a
href="/login"
style="background:#777;">
Login
</a>

</form>

</div>

</body>

</html>
""")


# =========================================================
# LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        mobile = request.form.get(
            "mobile",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        ).strip()

        conn = get_db()

        owner = conn.execute("""
            SELECT *
            FROM owners
            WHERE mobile = ?
            AND password = ?
        """, (
            mobile,
            password
        )).fetchone()

        conn.close()

        if owner:

            session["owner_id"] = owner["id"]

            return redirect("/dashboard")

        return """
        Mobile या Password गलत है।
        <br><br>
        <a href="/login">Back</a>
        """

    return render_template_string("""
<!DOCTYPE html>

<html lang="hi">

<head>

<meta charset="UTF-8">

<meta name="viewport"
content="width=device-width, initial-scale=1.0">

<title>Owner Login - Gopal Room Finder</title>

<style>

body {
    font-family: Arial;
    background: #f5f5f5;
    padding: 20px;
}

.box {
    max-width: 500px;
    margin: auto;
    background: white;
    padding: 20px;
    border-radius: 10px;
}

input {
    width: 100%;
    padding: 10px;
    margin: 8px 0 15px;
    box-sizing: border-box;
}

button,
a {
    display: inline-block;
    padding: 10px 15px;
    background: #1565c0;
    color: white;
    border: none;
    border-radius: 6px;
    text-decoration: none;
}

</style>

</head>

<body>

<div class="box">

<h2>🔐 Owner Login</h2>

<form method="POST">

<label>Mobile</label>

<input
type="text"
name="mobile"
required
>

<label>Password</label>

<input
type="password"
name="password"
required
>

<button type="submit">
Login
</button>

<a
href="/register"
style="background:#43a047;">
Register
</a>

</form>

</div>

</body>

</html>
""")


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")


# =========================================================
# OWNER DASHBOARD
# =========================================================

@app.route("/dashboard")
def dashboard():

    owner_id = session.get(
        "owner_id"
    )

    if not owner_id:

        return redirect("/login")

    conn = get_db()

    owner = conn.execute("""
        SELECT *
        FROM owners
        WHERE id = ?
    """, (
        owner_id,
    )).fetchone()

    if not owner:

        conn.close()

        session.clear()

        return redirect("/login")

    rooms = conn.execute("""
        SELECT *
        FROM rooms
        WHERE mobile = ?
        ORDER BY id DESC
    """, (
        owner["mobile"],
    )).fetchall()

    conn.close()

    return render_template_string("""
<!DOCTYPE html>

<html lang="hi">

<head>

<meta charset="UTF-8">

<meta name="viewport"
content="width=device-width, initial-scale=1.0">

<title>Owner Dashboard - Gopal Room Finder</title>

<style>

body {
    font-family: Arial, sans-serif;
    background: #f5f5f5;
    margin: 0;
    padding: 20px;
}

.box {
    max-width: 900px;
    margin: auto;
    background: white;
    padding: 20px;
    border-radius: 10px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
}

a {
    display: inline-block;
    margin-top: 10px;
    padding: 10px 15px;
    background: #1565c0;
    color: white;
    text-decoration: none;
    border-radius: 6px;
    text-align: center;
}

.room {
    border: 1px solid #ddd;
    padding: 15px;
    margin-top: 15px;
    border-radius: 8px;
}

</style>

</head>

<body>

<div class="box">

<h2>👤 Owner Dashboard</h2>

<br>

<a
href="/logout"
style="background:#d32f2f;">
🚪 Logout
</a>

<p>
स्वागत है,
<b>{{ owner["name"] }}</b>
</p>

<hr>

<h3>🏠 आपके Rooms</h3>

<p>

<a
href="/add_room"
style="background:#1976d2;">
➕ नया Room जोड़ें
</a>

</p>

{% if rooms %}

{% for room in rooms %}

<div class="room">

<h3>
{{ room["room_type"] }}
</h3>

<p>
📍 {{ room["location"] }}
</p>

<p>
💰 Rent: ₹{{ room["rent"] }}
</p>

{% if room["deposit"] %}

<p>
💵 Deposit: ₹{{ room["deposit"] }}
</p>

{% endif %}

{% if room["furnished"] %}

<p>
🛋 {{ room["furnished"] }}
</p>

{% endif %}

{% if room["description"] %}

<p>
📝 {{ room["description"] }}
</p>

{% endif %}

<a
href="/edit_room/{{ room['id'] }}">
✏️ Edit Room
</a>

<br>

<a
href="/delete_room/{{ room['id'] }}"
onclick="return confirm('क्या आप यह Room Delete करना चाहते हैं?');"
style="background:#d32f2f;">
🗑️ Delete Room
</a>

</div>

{% endfor %}

{% else %}

<p>
अभी आपने कोई Room नहीं जोड़ा है।
</p>

{% endif %}

<hr>

<a
href="/"
style="background:#555;">
🏠 Home Page
</a>

</div>

</body>

</html>
""",
        owner=owner,
        rooms=rooms
    )


# =========================================================
# EDIT ROOM
# =========================================================

@app.route(
    "/edit_room/<int:room_id>",
    methods=["GET", "POST"]
)
def edit_room(room_id):

    owner_id = session.get(
        "owner_id"
    )

    if not owner_id:

        return redirect("/login")

    conn = get_db()

    owner = conn.execute("""
        SELECT *
        FROM owners
        WHERE id = ?
    """, (
        owner_id,
    )).fetchone()

    if not owner:

        conn.close()

        session.clear()

        return redirect("/login")

    room = conn.execute("""
        SELECT *
        FROM rooms
        WHERE id = ?
        AND mobile = ?
    """, (
        room_id,
        owner["mobile"]
    )).fetchone()

    if not room:

        conn.close()

        return """
        Room नहीं मिला।
        <br><br>
        <a href="/dashboard">Dashboard</a>
        """

    images = conn.execute("""
        SELECT *
        FROM room_images
        WHERE room_id = ?
        ORDER BY id ASC
    """, (
        room_id,
    )).fetchall()

    conn.close()

    if request.method == "POST":

        location = request.form.get(
            "location",
            ""
        ).strip()

        room_type = request.form.get(
            "room_type",
            ""
        ).strip()

        rent = request.form.get(
            "rent",
            ""
        ).strip()

        deposit = request.form.get(
            "deposit",
            ""
        ).strip()

        furnished = request.form.get(
            "furnished",
            ""
        ).strip()

        description = request.form.get(
            "description",
            ""
        ).strip()

        map_link = request.form.get(
            "map_link",
            ""
        ).strip()

        if not location or not room_type or not rent:

            return """
            Location, Room Type और Rent जरूरी हैं।
            """

        try:

            rent = int(rent)

        except ValueError:

            return """
            Rent सही संख्या में डालें।
            """

        if deposit:

            try:

                deposit = int(deposit)

            except ValueError:

                return """
                Deposit सही संख्या में डालें।
                """

        else:

            deposit = None

        conn = get_db()

        conn.execute("""
            UPDATE rooms
            SET
                location = ?,
                room_type = ?,
                rent = ?,
                deposit = ?,
                furnished = ?,
                description = ?,
                map_link = ?
            WHERE id = ?
            AND mobile = ?
        """, (
            location,
            room_type,
            rent,
            deposit,
            furnished,
            description,
            map_link,
            room_id,
            owner["mobile"]
        ))

        current_count = conn.execute("""
            SELECT COUNT(*)
            FROM room_images
            WHERE room_id = ?
        """, (
            room_id,
        )).fetchone()[0]

        files = request.files.getlist(
            "photos"
        )

        for file in files:

            if current_count >= 10:

                break

            if (
                file
                and file.filename
                and allowed_file(file.filename)
            ):

                original_name = secure_filename(
                    file.filename
                )

                extension = original_name.rsplit(
                    ".",
                    1
                )[1].lower()

                filename = (
                    str(uuid.uuid4())
                    + "."
                    + extension
                )

                filepath = os.path.join(
                    UPLOAD_FOLDER,
                    filename
                )

                file.save(filepath)

                conn.execute("""
                    INSERT INTO room_images
                    (
                        room_id,
                        filename
                    )
                    VALUES (?, ?)
                """, (
                    room_id,
                    filename
                ))

                current_count += 1

        conn.commit()

        conn.close()

        return redirect(
            "/edit_room/" + str(room_id)
        )

    return render_template_string("""
<!DOCTYPE html>

<html lang="hi">

<head>

<meta charset="UTF-8">

<meta name="viewport"
content="width=device-width, initial-scale=1.0">

<title>Edit Room - Gopal Room Finder</title>

<style>

body {
    font-family: Arial;
    background: #f5f5f5;
    padding: 20px;
}

.box {
    max-width: 700px;
    margin: auto;
    background: white;
    padding: 20px;
    border-radius: 10px;
}

input,
select,
textarea {
    width: 100%;
    padding: 10px;
    margin-top: 6px;
    margin-bottom: 12px;
    box-sizing: border-box;
}

button,
a {
    display: inline-block;
    padding: 10px 15px;
    background: #1565c0;
    color: white;
    text-decoration: none;
    border: none;
    border-radius: 6px;
}

.photos {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
}

.photo-box {
    width: 150px;
    border: 1px solid #ddd;
    padding: 5px;
    border-radius: 6px;
}

.photo-box img {
    width: 150px;
    height: 110px;
    object-fit: cover;
    border-radius: 5px;
}

.delete-photo {
    width: 100%;
    background: #d32f2f !important;
    margin-top: 5px;
}

</style>

</head>

<body>

<div class="box">

<h2>✏️ Edit Room</h2>

<form method="POST"
enctype="multipart/form-data">

<label>Owner Name</label>

<input
type="text"
value="{{ owner['name'] }}"
readonly
>

<label>Mobile</label>

<input
type="text"
value="{{ owner['mobile'] }}"
readonly
>

<label>📍 Location</label>

<input
type="text"
name="location"
value="{{ room['location'] }}"
required
>

<label>🏠 Room Type</label>

<select name="room_type" required>

<option value="Single Room"
{% if room["room_type"] == "Single Room" %}selected{% endif %}>
Single Room
</option>

<option value="1 BHK"
{% if room["room_type"] == "1 BHK" %}selected{% endif %}>
1 BHK
</option>

<option value="2 BHK"
{% if room["room_type"] == "2 BHK" %}selected{% endif %}>
2 BHK
</option>

<option value="PG"
{% if room["room_type"] == "PG" %}selected{% endif %}>
PG
</option>

<option value="Hostel"
{% if room["room_type"] == "Hostel" %}selected{% endif %}>
Hostel
</option>

</select>

<label>💰 Rent (₹)</label>

<input
type="number"
name="rent"
value="{{ room['rent'] }}"
required
>

<label>💵 Deposit (₹)</label>

<input
type="number"
name="deposit"
value="{{ room['deposit'] if room['deposit'] else '' }}"
>

<label>🛋 Furnished</label>

<select name="furnished">

<option value="">
Select
</option>

<option value="Fully Furnished"
{% if room["furnished"] == "Fully Furnished" %}selected{% endif %}>
Fully Furnished
</option>

<option value="Semi Furnished"
{% if room["furnished"] == "Semi Furnished" %}selected{% endif %}>
Semi Furnished
</option>

<option value="Unfurnished"
{% if room["furnished"] == "Unfurnished" %}selected{% endif %}>
Unfurnished
</option>

</select>

<label>📝 Description</label>

<textarea
name="description"
rows="5">{{ room["description"] if room["description"] else "" }}</textarea>

<label>📍 Google Maps Link</label>

<input
type="url"
name="map_link"
value="{{ room['map_link'] if room['map_link'] else '' }}"
>

<hr>

<h3>📷 Existing Photos</h3>

<div class="photos">

{% if images %}

{% for image in images %}

<div class="photo-box">

<img
src="/uploads/{{ image['filename'] }}"
alt="Room Photo"
>

<a
href="/delete_photo/{{ image['id'] }}"
class="delete-photo"
onclick="return confirm('क्या आप यह Photo Delete करना चाहते हैं?');">
🗑️ Delete Photo
</a>

</div>

{% endfor %}

{% else %}

<p>
अभी कोई Photo नहीं है।
</p>

{% endif %}

</div>

<hr>

<label>📷 नई Photos जोड़ें</label>

<input
type="file"
name="photos"
multiple
accept=".jpg,.jpeg,.png,.webp"
>

<p>
कुल अधिकतम 10 Photos रखी जा सकती हैं।
</p>

<button type="submit">
💾 Update Room
</button>

<a
href="/dashboard"
style="background:#777;">
Dashboard
</a>

</form>

</div>

</body>

</html>
""",
        owner=owner,
        room=room,
        images=images
    )


# =========================================================
# DELETE SINGLE PHOTO
# =========================================================

@app.route("/delete_photo/<int:image_id>")
def delete_photo(image_id):

    owner_id = session.get(
        "owner_id"
    )

    if not owner_id:

        return redirect("/login")

    conn = get_db()

    owner = conn.execute("""
        SELECT *
        FROM owners
        WHERE id = ?
    """, (
        owner_id,
    )).fetchone()

    if not owner:

        conn.close()

        session.clear()

        return redirect("/login")

    image = conn.execute("""
        SELECT
            room_images.*,
            rooms.mobile
        FROM room_images
        INNER JOIN rooms
            ON room_images.room_id = rooms.id
        WHERE room_images.id = ?
    """, (
        image_id,
    )).fetchone()

    if not image:

        conn.close()

        return """
        Photo नहीं मिली।
        <br><br>
        <a href="/dashboard">Dashboard</a>
        """

    if image["mobile"] != owner["mobile"]:

        conn.close()

        return """
        आपको यह Photo Delete करने की अनुमति नहीं है।
        <br><br>
        <a href="/dashboard">Dashboard</a>
        """

    filename = image["filename"]

    room_id = image["room_id"]

    conn.execute("""
        DELETE FROM room_images
        WHERE id = ?
    """, (
        image_id,
    ))

    conn.commit()

    conn.close()

    filepath = os.path.join(
        UPLOAD_FOLDER,
        filename
    )

    if os.path.exists(filepath):

        try:

            os.remove(filepath)

        except OSError:

            pass

    return redirect(
        "/edit_room/" + str(room_id)
    )


# =========================================================
# DELETE ROOM
# =========================================================

@app.route("/delete_room/<int:room_id>")
def delete_room(room_id):

    owner_id = session.get(
        "owner_id"
    )

    if not owner_id:

        return redirect("/login")

    conn = get_db()

    owner = conn.execute("""
        SELECT *
        FROM owners
        WHERE id = ?
    """, (
        owner_id,
    )).fetchone()

    if not owner:

        conn.close()

        session.clear()

        return redirect("/login")

    room = conn.execute("""
        SELECT *
        FROM rooms
        WHERE id = ?
        AND mobile = ?
    """, (
        room_id,
        owner["mobile"]
    )).fetchone()

    if not room:

        conn.close()

        return """
        Room नहीं मिला।
        <br><br>
        <a href="/dashboard">Dashboard</a>
        """

    images = conn.execute("""
        SELECT *
        FROM room_images
        WHERE room_id = ?
    """, (
        room_id,
    )).fetchall()

    conn.execute("""
        DELETE FROM room_images
        WHERE room_id = ?
    """, (
        room_id,
    ))

    conn.execute("""
        DELETE FROM rooms
        WHERE id = ?
        AND mobile = ?
    """, (
        room_id,
        owner["mobile"]
    ))

    conn.commit()

    conn.close()

    for image in images:

        filename = image["filename"]

        filepath = os.path.join(
            UPLOAD_FOLDER,
            filename
        )

        if os.path.exists(filepath):

            try:

                os.remove(filepath)

            except OSError:

                pass

    return redirect("/dashboard")


# =========================================================
# START APP
# =========================================================

if __name__ == "__main__":

    init_db()

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )