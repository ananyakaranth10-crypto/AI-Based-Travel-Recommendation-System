import json
import math
import sqlite3
from flask import Flask, render_template, request, redirect, session, url_for
from werkzeug.security import generate_password_hash, check_password_hash
import pandas as pd


df = pd.read_csv("places_with_images.csv")

app = Flask(__name__)
app.secret_key = "journey_through_india_2026"

@app.route("/")
def home():

    conn = sqlite3.connect("travel.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, name, email, message, created_at
        FROM contact_messages
        ORDER BY created_at DESC
    """)

    all_messages = cursor.fetchall()

    replies = {}

    for msg in all_messages:
        cursor.execute("""
            SELECT user_name, reply, created_at
            FROM message_replies
            WHERE message_id = ?
            ORDER BY created_at ASC
        """, (msg[0],))

        replies[msg[0]] = cursor.fetchall()

    conn.close()

    return render_template(
        "home.html",
        messages=all_messages,
        replies=replies
    )

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/contact", methods=["GET", "POST"])
def contact():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        message = request.form["message"]

        conn = sqlite3.connect("travel.db")
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO contact_messages(name, email, message)
            VALUES(?, ?, ?)
        """, (name, email, message))

        conn.commit()
        conn.close()

        return render_template(
            "contact.html",
            success="Thank you! Your message has been received."
        )

    return render_template("contact.html")

@app.route("/reply-message/<int:message_id>", methods=["POST"])
def reply_message(message_id):

    if "user_name" not in session:
        return redirect(url_for("login", next="/"))

    reply = request.form["reply"]

    conn = sqlite3.connect("travel.db")
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO message_replies(message_id, user_name, reply)
        VALUES(?, ?, ?)
    """, (message_id, session["user_name"], reply))

    conn.commit()
    conn.close()

    return redirect("/")
    

@app.route("/login", methods=["GET", "POST"])
def login():

    next_url = request.args.get("next") or request.form.get("next") or "/journey-planner"

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        conn = sqlite3.connect("travel.db")
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM users WHERE email=?",
            (email,)
        )

        user = cursor.fetchone()

        conn.close()

        if user:

            stored_password = user[3]

            if check_password_hash(stored_password, password):

                session["user_id"] = user[0]
                session["user_name"] = user[1]
                session["user_email"] = user[2]

                return redirect(next_url)

        return render_template(
            "login.html",
            message="Invalid Email or Password!",
            next=next_url
        )

    return render_template("login.html", next=next_url)

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        if password != confirm_password:
            return render_template(
                "register.html",
                message="Passwords do not match!"
            )

        conn = sqlite3.connect("travel.db")
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM users WHERE email=?",
            (email,)
        )

        existing_user = cursor.fetchone()

        if existing_user:

            conn.close()

            return render_template(
                "register.html",
                message="Email already registered!"
            )

        hashed_password = generate_password_hash(password)

        cursor.execute(
            "INSERT INTO users(name,email,password) VALUES(?,?,?)",
            (name, email, hashed_password)
        )

        conn.commit()
        conn.close()

        return redirect("/login")

    return render_template("register.html")

@app.route("/journey-planner")
def journey_planner():

    if "user_id" not in session:
        return redirect(url_for("login", next="/journey-planner"))

    states = sorted(df["State_UT"].unique())
    trip_types = sorted(df["Trip_Type"].unique())
    categories = sorted(df["Category"].unique())
    seasons = sorted(df["Best_Season"].unique())

    return render_template(
        "journey_planner.html",
        states=states,
        trip_types=trip_types,
        categories=categories,
        seasons=seasons
    )

@app.route("/recommend", methods=["POST"])
def recommend():

    state = request.form.get("state")
    trip_type = request.form.get("trip_type")
    season = request.form.get("season")
    category = request.form.get("category")
    budget = request.form.get("budget")

    recommendations = df.copy()

    if state:
        recommendations = recommendations[
            recommendations["State_UT"] == state
        ]

    recommendations["Score"] = 0

    if trip_type:
        recommendations.loc[
            recommendations["Trip_Type"] == trip_type,
            "Score"
        ] += 2

    if budget and budget.strip():
        budget = int(budget)

        recommendations.loc[
            recommendations["Min_Budget"] <= budget,
            "Score"
        ] += 1

    recommendations = recommendations[
        recommendations["Score"] >= 1
    ]

    recommendations = recommendations.sort_values(
        by=["Score", "Rating"],
        ascending=False
    )

    recommendations = recommendations.head(10)

    return render_template(
        "recommendations.html",
        recommendations=recommendations.to_dict("records")
    )

@app.route("/place/<place_name>")
def place_details(place_name):

    place = df[df["Place_Name"] == place_name]

    if place.empty:
        return "Place not found"

    place = place.iloc[0]

    more_places = df[
        (df["State_UT"] == place["State_UT"]) &
        (df["Place_Name"] != place["Place_Name"])
    ].head(4)

    conn = sqlite3.connect("travel.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT user_name, rating, review, created_at
        FROM reviews
        WHERE place_name = ?
        ORDER BY created_at DESC
    """, (place_name,))

    reviews = cursor.fetchall()

    conn.close()

    return render_template(
        "place_details.html",
        place=place,
        more_places=more_places.to_dict("records"),
        reviews=reviews
    )

@app.route("/category/<category>")
def category_places(category):

    places = df[
        df["Category"].str.lower() == category.lower()
    ]

    return render_template(
        "recommendations.html",
        recommendations=places.to_dict("records")
    )

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")

@app.route("/add-favorite/<place_name>")
def add_favorite(place_name):

    if "user_email" not in session:
        return redirect(url_for("login", next=url_for("place_details", place_name=place_name)))

    conn = sqlite3.connect("travel.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM favorites WHERE user_email=? AND place_name=?",
        (session["user_email"], place_name)
    )

    already_exists = cursor.fetchone()

    if not already_exists:

        cursor.execute(
            "INSERT INTO favorites(user_email, place_name) VALUES(?, ?)",
            (session["user_email"], place_name)
        )

        conn.commit()

    conn.close()

    return redirect(f"/place/{place_name}")

@app.route("/favorites")
def favorites():

    if "user_email" not in session:
        return redirect(url_for("login", next="/favorites"))

    conn = sqlite3.connect("travel.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT place_name FROM favorites WHERE user_email=?",
        (session["user_email"],)
    )

    favorite_places = cursor.fetchall()

    conn.close()

    places = []

    for fav in favorite_places:

        place = df[df["Place_Name"] == fav[0]]

        if not place.empty:
            places.append(place.iloc[0])

    return render_template(
        "favorites.html",
        favorites=places
    )

@app.route("/remove-favorite/<place_name>")
def remove_favorite(place_name):

    if "user_email" not in session:
        return redirect(url_for("login", next="/favorites"))

    conn = sqlite3.connect("travel.db")
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM favorites WHERE user_email=? AND place_name=?",
        (session["user_email"], place_name)
    )

    conn.commit()
    conn.close()

    return redirect("/favorites")

@app.route("/add-review/<place_name>", methods=["POST"])
def add_review(place_name):

    if "user_name" not in session:
        return redirect(url_for("login", next=url_for("place_details", place_name=place_name)))

    rating = request.form["rating"]
    review = request.form["review"]

    conn = sqlite3.connect("travel.db")
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO reviews(place_name,user_name,rating,review)
        VALUES(?,?,?,?)
        """,
        (
            place_name,
            session["user_name"],
            rating,
            review
        )
    )

    conn.commit()
    conn.close()

    return redirect(f"/place/{place_name}")

@app.route("/trip-planner")
def trip_planner_page():

    if "user_id" not in session:
        return redirect(url_for("login", next="/trip-planner"))

    states = sorted(df["State_UT"].unique())

    return render_template("trip_planner_page.html", states=states)


@app.route("/get-places-by-state")
def get_places_by_state():

    state = request.args.get("state")

    places = df[df["State_UT"] == state]["Place_Name"].tolist()

    return {"places": places}


@app.route("/generate-itinerary", methods=["POST"])
def generate_itinerary():

    if "user_id" not in session:
        return redirect(url_for("login", next="/trip-planner"))

    selected_places = request.form.getlist("places")

    if not selected_places:
        return redirect("/trip-planner")

    itinerary = []

    for i in range(0, len(selected_places), 2):

        day_places = selected_places[i:i+2]
        day_num = (i // 2) + 1
        places_data = []

        for p in day_places:
            place = df[df["Place_Name"] == p]
            if not place.empty:
                places_data.append(place.iloc[0].to_dict())

        itinerary.append({
            "day": day_num,
            "places": places_data
        })

    return render_template(
        "itinerary.html",
        itinerary=itinerary,
        selected_places=selected_places,
        num_days=len(itinerary)
    )


@app.route("/save-itinerary", methods=["POST"])
def save_itinerary():

    if "user_email" not in session:
        return redirect(url_for("login", next="/my-trips"))

    trip_name = request.form.get("trip_name") or "My Trip"
    places = request.form.getlist("places")
    num_days = math.ceil(len(places) / 2)

    conn = sqlite3.connect("travel.db")
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO trip_plans(user_email, trip_name, places, num_days)
        VALUES(?, ?, ?, ?)
    """, (
        session["user_email"],
        trip_name,
        json.dumps(places),
        num_days
    ))

    conn.commit()
    conn.close()

    return redirect("/my-trips")


@app.route("/my-trips")
def my_trips():

    if "user_email" not in session:
        return redirect(url_for("login", next="/my-trips"))

    conn = sqlite3.connect("travel.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, trip_name, places, num_days, created_at
        FROM trip_plans
        WHERE user_email = ?
        ORDER BY created_at DESC
    """, (session["user_email"],))

    trips = cursor.fetchall()
    conn.close()

    trips_data = []

    for trip in trips:
        trips_data.append({
            "id": trip[0],
            "trip_name": trip[1],
            "places": json.loads(trip[2]),
            "num_days": trip[3],
            "created_at": trip[4]
        })

    return render_template("my_trips.html", trips=trips_data)

if __name__ == "__main__":
    app.run(debug=True)