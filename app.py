import os
from werkzeug.utils import secure_filename
from database.db import get_connection
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_from_directory
from urllib.parse import quote

app = Flask(__name__)
UPLOAD_FOLDER = os.path.join("static", "uploads", "hospitals")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(
        app.config["UPLOAD_FOLDER"],
        filename
    )

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
app.secret_key = "medicompare123"

ADMIN_EMAIL = "krishshinde98@gmail.com"

def admin_required():

    if "user_id" not in session:
        flash("Admin access required.", "danger")
        return redirect("/login")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, role, email
        FROM users
        WHERE id=?
    """, (session["user_id"],))

    user = cursor.fetchone()

    conn.close()

    if not user or not user["email"] or user["email"].strip().lower() != ADMIN_EMAIL.lower():
        flash("Admin access required.", "danger")
        return redirect("/")

    return None

@app.context_processor
def inject_admin_status():
    is_admin = False
    if "user_id" in session:
        user_email = session.get("user_email")
        if user_email:
            is_admin = (user_email.strip().lower() == ADMIN_EMAIL.lower())
        else:
            try:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT email FROM users WHERE id=?", (session["user_id"],))
                row = cursor.fetchone()
                conn.close()
                if row and row["email"] and row["email"].strip().lower() == ADMIN_EMAIL.lower():
                    is_admin = True
                    session["user_email"] = row["email"]
                    session["role"] = "admin"
                    session["is_admin"] = True
            except Exception:
                pass
    return dict(is_admin=is_admin)

@app.route("/", methods=["GET"])
def home():

    search = request.args.get("search", "")
    city = request.args.get("city", "")
    hospital_type = request.args.get("hospital_type", "")
    rating = request.args.get("rating", "")
    sort = request.args.get("sort", "")
    emergency = request.args.get("emergency")
    icu = request.args.get("icu")
    ambulance = request.args.get("ambulance")


    conn = get_connection()
    cursor = conn.cursor()

    query = """
        SELECT *
        FROM hospitals
        WHERE hospital_name LIKE ?
        AND city LIKE ?
    """

    parameters = [
        "%" + search + "%",
        "%" + city + "%"
    ]

    if hospital_type:

        query += " AND hospital_type=?"
        parameters.append(hospital_type)

    if rating:

        query += " AND rating>=?"
        parameters.append(float(rating))
    
    if emergency:
        query += " AND emergency=1"
    
    if icu:
        query += " AND icu=1"
        
    if ambulance:
        query += " AND ambulance=1"

    if sort == "rating_high":
        query += " ORDER BY rating DESC"
    elif sort == "rating_low":
        query += " ORDER BY rating ASC"
    elif sort == "name":
        query += " ORDER BY hospital_name ASC"
    elif sort == "city":
        query += " ORDER BY city ASC"

    cursor.execute(query, tuple(parameters))

    hospitals = cursor.fetchall()

    conn.close()

    return render_template(
        "index.html",
        hospitals=hospitals,
        search=search,
        city=city,
        hospital_type=hospital_type,
        rating=rating,
        sort=sort,
        user_name=session.get("user_name")
    )

@app.route("/hospital/<int:id>")
def hospital_details(id):

    conn = get_connection()
    cursor = conn.cursor()

    # ==========================================
    # HOSPITAL DETAILS
    # ==========================================

    cursor.execute("""
        SELECT *
        FROM hospitals
        WHERE id=?
    """, (id,))

    hospital = cursor.fetchone()

    if not hospital:
        conn.close()
        return "Hospital not found", 404


    # ==========================================
    # DOCTOR DETAILS
    # ==========================================

    cursor.execute("""
        SELECT *
        FROM doctors
        WHERE hospital_id=?
        ORDER BY doctor_name
    """, (id,))

    doctors = cursor.fetchall()


    # ==========================================
    # HOSPITAL SERVICES
    # ==========================================

    cursor.execute("""
        SELECT
            id,
            service_name,
            description,
            cost
        FROM services
        WHERE hospital_id=?
        ORDER BY service_name ASC
    """, (id,))

    services = cursor.fetchall()


    # ==========================================
    # REVIEWS WITH USER NAMES
    # ==========================================

    cursor.execute("""
        SELECT
            reviews.*,
            users.full_name
        FROM reviews

        JOIN users
        ON reviews.user_id = users.id

        WHERE reviews.hospital_id=?

        ORDER BY reviews.id DESC
    """, (id,))

    reviews = cursor.fetchall()


    # ==========================================
    # CHECK FAVORITE
    # ==========================================

    is_favorite = False

    user_id = session.get("user_id")

    if user_id:

        cursor.execute("""
            SELECT id
            FROM favorites
            WHERE user_id=?
            AND hospital_id=?
        """, (
            user_id,
            id
        ))

        favorite = cursor.fetchone()

        if favorite:
            is_favorite = True


    # ==========================================
    # HOSPITAL IMAGE
    # ==========================================

    hospital_image = hospital["image"] if "image" in hospital.keys() else None


    conn.close()


    # ==========================================
    # GOOGLE MAPS LOCATION
    # ==========================================

    import urllib.parse

    hospital_address = hospital["address"] or ""
    hospital_city = hospital["city"] or ""

    location_text = f"{hospital_address}, {hospital_city}"

    map_url = (
        "https://www.google.com/maps/search/?api=1&query="
        + urllib.parse.quote(location_text)
    )


    # ==========================================
    # RENDER HOSPITAL DETAILS PAGE
    # ==========================================

    return render_template(
        "hospital_details.html",

        hospital=hospital,

        doctors=doctors,

        services=services,

        reviews=reviews,

        user_name=session.get("user_name"),

        user_id=user_id,

        is_favorite=is_favorite,

        hospital_image=hospital_image,

        map_url=map_url
    )
 

@app.route("/hospital/<int:id>/review", methods=["POST"])
def add_review(id):

    if "user_id" not in session:
        return redirect("/login")

    rating = request.form.get("rating")
    comment = request.form.get("comment", "").strip()

    if not rating or not comment:
        flash("Please provide a rating and review.", "error")
        return redirect(f"/hospital/{id}")

    conn = get_connection()
    cursor = conn.cursor()

    # Check whether hospital exists
    cursor.execute("""
        SELECT id
        FROM hospitals
        WHERE id=?
    """, (id,))

    hospital = cursor.fetchone()

    if not hospital:
        conn.close()
        return "Hospital not found", 404

    # Add review
    cursor.execute("""
        INSERT INTO reviews(
            hospital_id,
            user_id,
            rating,
            comment,
            review_date
        )
        VALUES(?,?,?,?,DATE('now'))
    """, (
        id,
        session["user_id"],
        rating,
        comment
    ))

    # Calculate new average rating
    cursor.execute("""
        SELECT AVG(rating)
        FROM reviews
        WHERE hospital_id=?
    """, (id,))

    average_rating = cursor.fetchone()[0]

    # Update hospital rating
    cursor.execute("""
        UPDATE hospitals
        SET rating=?
        WHERE id=?
    """, (
        round(average_rating, 1),
        id
    ))

    conn.commit()
    conn.close()

    flash("Review submitted successfully!", "success")

    return redirect(f"/hospital/{id}")

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():

    if request.method == "POST":

        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM users WHERE LOWER(email)=LOWER(?) AND password=?",
            (email, password)
        )

        user = cursor.fetchone()
        conn.close()

        if user and user["email"] and user["email"].strip().lower() == ADMIN_EMAIL.lower():
            session["user_id"] = user["id"]
            session["user_name"] = user["full_name"]
            session["user_email"] = user["email"].strip()
            session["role"] = "admin"
            session["is_admin"] = True
            return redirect(url_for("dashboard"))

        flash("Invalid Admin Credentials", "danger")
        return redirect("/admin/login")

    return render_template("admin/login.html")



@app.route("/admin/dashboard")
def dashboard():

    access_check = admin_required()
    if access_check:
        return access_check

    conn = get_connection()
    cursor = conn.cursor()

    # ==============================
    # HOSPITAL COUNT
    # ==============================

    cursor.execute("SELECT COUNT(*) FROM hospitals")
    total_hospitals = cursor.fetchone()[0]


    # ==============================
    # DOCTOR COUNT
    # ==============================

    cursor.execute("SELECT COUNT(*) FROM doctors")
    total_doctors = cursor.fetchone()[0]


    # ==============================
    # USER COUNT
    # ==============================

    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]


    # ==============================
    # TOTAL APPOINTMENTS
    # ==============================

    cursor.execute("SELECT COUNT(*) FROM appointments")
    total_appointments = cursor.fetchone()[0]


    # ==============================
    # PENDING APPOINTMENTS
    # ==============================

    cursor.execute("""
        SELECT COUNT(*)
        FROM appointments
        WHERE status='Pending'
    """)

    pending = cursor.fetchone()[0]


    # ==============================
    # APPROVED APPOINTMENTS
    # ==============================

    cursor.execute("""
        SELECT COUNT(*)
        FROM appointments
        WHERE status='Approved'
    """)

    approved = cursor.fetchone()[0]


    # ==============================
    # REJECTED APPOINTMENTS
    # ==============================

    cursor.execute("""
        SELECT COUNT(*)
        FROM appointments
        WHERE status='Rejected'
    """)

    rejected = cursor.fetchone()[0]

    cursor.execute("""
    SELECT COUNT(*)
    FROM appointments
    WHERE status='Cancelled'
    """)
    cancelled = cursor.fetchone()[0]

    cursor.execute("""
    SELECT COUNT(*) 
    FROM services
    """)
    total_services = cursor.fetchone()[0]

    cursor.execute("""
    SELECT COUNT(*)
    FROM reviews
    """)
    total_reviews = cursor.fetchone()[0]

    conn.close()


    # ==============================
    # SEND DATA TO DASHBOARD
    # ==============================

    return render_template(
        "admin/dashboard.html",

        total_hospitals=total_hospitals,

        total_doctors=total_doctors,

        total_users=total_users,

        total_appointments=total_appointments,

        pending=pending,

        approved=approved,

        rejected=rejected,
        cancelled=cancelled,
        total_services=total_services,
        total_reviews=total_reviews
    )
@app.route("/admin/users")
def admin_users():

    # Check admin access
    access_check = admin_required()

    if access_check:
        return access_check

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, full_name, email, role
        FROM users
        ORDER BY id DESC
    """)

    users = cursor.fetchall()

    conn.close()

    return render_template(
        "admin/users.html",
        users=users
    )

@app.route("/admin/services")
def admin_services():

    # Check admin access
    access_check = admin_required()

    if access_check:
        return access_check

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            services.id,
            services.service_name,
            services.description,
            services.cost,
            hospitals.hospital_name
        FROM services

        LEFT JOIN hospitals
        ON services.hospital_id = hospitals.id

        ORDER BY services.service_name ASC
    """)

    services = cursor.fetchall()

    conn.close()

    return render_template(
        "admin/services.html",
        services=services
    )

# 👇 ADD THIS NEW ROUTE HERE
@app.route("/admin/hospitals")
def hospitals():

    # Check admin access
    access_check = admin_required()

    if access_check:
        return access_check

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM hospitals
        ORDER BY hospital_name ASC
    """)

    hospitals = cursor.fetchall()

    conn.close()

    return render_template(
        "admin/hospitals.html",
        hospitals=hospitals
    )

@app.route("/admin/add-hospital", methods=["GET", "POST"])
def add_hospital():

    # Check admin access
    access_check = admin_required()

    if access_check:
        return access_check

    if request.method == "POST":

        # ----------------------------------------
        # GET FORM DATA
        # ----------------------------------------

        hospital_name = request.form.get(
            "hospital_name",
            ""
        ).strip()

        city = request.form.get(
            "city",
            ""
        ).strip()

        address = request.form.get(
            "address",
            ""
        ).strip()

        phone = request.form.get(
            "phone",
            ""
        ).strip()

        map_link = request.form.get(
            "map_link",
            ""
        ).strip()

        hospital_type = request.form.get(
            "hospital_type",
            ""
        ).strip()

        rating = request.form.get(
            "rating",
            "0"
        ).strip()


        # ----------------------------------------
        # CHECK REQUIRED FIELDS
        # ----------------------------------------

        if not hospital_name or not city:

            flash(
                "Hospital name and city are required.",
                "error"
            )

            return render_template(
                "admin/add_hospital.html"
            )


        # ----------------------------------------
        # HOSPITAL SERVICES
        # ----------------------------------------

        emergency = (
            1
            if "emergency" in request.form
            else 0
        )

        ambulance = (
            1
            if "ambulance" in request.form
            else 0
        )

        icu = (
            1
            if "icu" in request.form
            else 0
        )


        # ----------------------------------------
        # HOSPITAL IMAGE
        # ----------------------------------------

        image = request.files.get("image")

        filename = ""


        if image and image.filename:

            filename = secure_filename(
                image.filename
            )

            image_path = os.path.join(
                app.config["UPLOAD_FOLDER"],
                filename
            )

            image.save(image_path)


        # ----------------------------------------
        # INSERT HOSPITAL
        # ----------------------------------------

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO hospitals (
                hospital_name,
                city,
                address,
                phone,
                map_link,
                hospital_type,
                rating,
                emergency,
                ambulance,
                icu,
                image
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            hospital_name,
            city,
            address,
            phone,
            map_link,
            hospital_type,
            rating,
            emergency,
            ambulance,
            icu,
            filename
        ))

        conn.commit()
        conn.close()


        flash(
            "Hospital added successfully!",
            "success"
        )

        return redirect(
            url_for("hospitals")
        )


    # ----------------------------------------
    # SHOW ADD HOSPITAL PAGE
    # ----------------------------------------

    return render_template(
        "admin/add_hospital.html"
    )

@app.route(
    "/admin/edit-hospital/<int:id>",
    methods=["GET", "POST"]
)
def edit_hospital(id):

    # Check admin access
    access_check = admin_required()

    if access_check:
        return access_check

    conn = get_connection()
    cursor = conn.cursor()

    # ----------------------------------------
    # GET HOSPITAL
    # ----------------------------------------

    cursor.execute("""
        SELECT *
        FROM hospitals
        WHERE id=?
    """, (id,))

    hospital = cursor.fetchone()

    if not hospital:

        conn.close()

        flash(
            "Hospital not found.",
            "error"
        )

        return redirect(
            url_for("hospitals")
        )

    # ----------------------------------------
    # UPDATE HOSPITAL
    # ----------------------------------------

    if request.method == "POST":

        hospital_name = request.form.get(
            "hospital_name",
            ""
        ).strip()

        city = request.form.get(
            "city",
            ""
        ).strip()

        address = request.form.get(
            "address",
            ""
        ).strip()

        phone = request.form.get(
            "phone",
            ""
        ).strip()

        map_link = request.form.get(
            "map_link",
            ""
        ).strip()

        hospital_type = request.form.get(
            "hospital_type",
            ""
        ).strip()

        rating = request.form.get(
            "rating",
            "0"
        ).strip()

        # ----------------------------------------
        # BASIC VALIDATION
        # ----------------------------------------

        if not hospital_name or not city:

            conn.close()

            flash(
                "Hospital name and city are required.",
                "error"
            )

            return redirect(
                url_for(
                    "edit_hospital",
                    id=id
                )
            )

        # ----------------------------------------
        # HOSPITAL SERVICES
        # ----------------------------------------

        emergency = (
            1
            if "emergency" in request.form
            else 0
        )

        ambulance = (
            1
            if "ambulance" in request.form
            else 0
        )

        icu = (
            1
            if "icu" in request.form
            else 0
        )

        # ----------------------------------------
        # HOSPITAL IMAGE
        # ----------------------------------------

        image = request.files.get("image")

        # Keep existing image
        filename = hospital["image"] or ""

        # If a new image is uploaded
        if image and image.filename:

            filename = secure_filename(
                image.filename
            )

            image_path = os.path.join(
                app.config["UPLOAD_FOLDER"],
                filename
            )

            image.save(image_path)

        # ----------------------------------------
        # UPDATE HOSPITAL
        # ----------------------------------------

        cursor.execute("""
            UPDATE hospitals
            SET
                hospital_name=?,
                city=?,
                address=?,
                phone=?,
                map_link=?,
                hospital_type=?,
                rating=?,
                emergency=?,
                ambulance=?,
                icu=?,
                image=?
            WHERE id=?
        """, (
            hospital_name,
            city,
            address,
            phone,
            map_link,
            hospital_type,
            rating,
            emergency,
            ambulance,
            icu,
            filename,
            id
        ))

        conn.commit()
        conn.close()

        flash(
            "Hospital updated successfully!",
            "success"
        )

        return redirect(
            url_for("hospitals")
        )

    # ----------------------------------------
    # SHOW EDIT PAGE
    # ----------------------------------------

    conn.close()

    return render_template(
        "admin/edit_hospital.html",
        hospital=hospital
    )

@app.route("/admin/doctors")
def doctors():

    # Check admin access
    access_check = admin_required()

    if access_check:
        return access_check

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT doctors.*,
               hospitals.hospital_name
        FROM doctors
        JOIN hospitals
        ON doctors.hospital_id = hospitals.id
        ORDER BY doctors.id DESC
    """)

    doctors = cursor.fetchall()

    conn.close()

    return render_template(
        "admin/doctors.html",
        doctors=doctors
    )

@app.route("/admin/add-doctor", methods=["GET", "POST"])
def add_doctor():

    access_check = admin_required()

    if access_check:
        return access_check

    conn = get_connection()
    cursor = conn.cursor()

    # Get hospitals for dropdown
    cursor.execute("""
        SELECT id, hospital_name
        FROM hospitals
        ORDER BY hospital_name ASC
    """)

    hospitals = cursor.fetchall()

    if request.method == "POST":

        hospital_id = request.form["hospital_id"]
        doctor_name = request.form["doctor_name"]
        specialization = request.form["specialization"]
        qualification = request.form["qualification"]
        experience = request.form["experience"]
        consultation_fee = request.form["consultation_fee"]

        # Get selected available days
        available_days = request.form.getlist("available_days")

        # Convert list into comma-separated text
        available_days = ", ".join(available_days)

        available_time = request.form["available_time"]

        cursor.execute("""
            INSERT INTO doctors (
                hospital_id,
                doctor_name,
                specialization,
                qualification,
                experience,
                consultation_fee,
                available_days,
                available_time
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            hospital_id,
            doctor_name,
            specialization,
            qualification,
            experience,
            consultation_fee,
            available_days,
            available_time
        ))

        conn.commit()
        conn.close()

        flash(
            "Doctor added successfully!",
            "success"
        )

        return redirect("/admin/doctors")

    conn.close()

    return render_template(
        "admin/add_doctor.html",
        hospitals=hospitals
    )

@app.route("/admin/edit-doctor/<int:id>", methods=["GET", "POST"])
def edit_doctor(id):

    # Check admin access
    access_check = admin_required()

    if access_check:
        return access_check

    conn = get_connection()
    cursor = conn.cursor()

    # Get doctor
    cursor.execute("""
        SELECT *
        FROM doctors
        WHERE id=?
    """, (id,))

    doctor = cursor.fetchone()

    if not doctor:
        conn.close()

        flash(
            "Doctor not found.",
            "error"
        )

        return redirect(url_for("doctors"))

    # Get hospitals for dropdown
    cursor.execute("""
        SELECT id, hospital_name
        FROM hospitals
        ORDER BY hospital_name ASC
    """)

    hospitals = cursor.fetchall()

    if request.method == "POST":

        hospital_id = request.form.get("hospital_id")
        doctor_name = request.form.get("doctor_name", "").strip()
        specialization = request.form.get("specialization", "").strip()
        qualification = request.form.get("qualification", "").strip()
        experience = request.form.get("experience", "").strip()
        consultation_fee = request.form.get("consultation_fee", "").strip()
        available_days = request.form.getlist("available_days")
        available_days = ", ".join(available_days)
        available_time = request.form.get("available_time", "").strip()

        # Basic validation
        if not hospital_id or not doctor_name or not specialization:
            conn.close()

            flash(
                "Hospital, doctor name and specialization are required.",
                "error"
            )

            return redirect(
                url_for("edit_doctor", id=id)
            )

        # Update doctor
        cursor.execute("""
            UPDATE doctors
            SET
                hospital_id=?,
                doctor_name=?,
                specialization=?,
                qualification=?,
                experience=?,
                consultation_fee=?,
                available_days=?,
                available_time=?
            WHERE id=?
        """, (
            hospital_id,
            doctor_name,
            specialization,
            qualification,
            experience or 0,
            consultation_fee or 0,
            available_days,
            available_time,
            id
        ))

        conn.commit()
        conn.close()

        flash(
            "Doctor updated successfully!",
            "success"
        )

        return redirect(url_for("doctors"))

    conn.close()

    return render_template(
        "admin/edit_doctor.html",
        doctor=doctor,
        hospitals=hospitals
    )

@app.route("/admin/delete-doctor/<int:id>")
def delete_doctor(id):

    # ==========================================
    # CHECK ADMIN ACCESS
    # ==========================================

    access_check = admin_required()

    if access_check:
        return access_check


    conn = get_connection()
    cursor = conn.cursor()


    # ==========================================
    # CHECK IF DOCTOR EXISTS
    # ==========================================

    cursor.execute("""
        SELECT id, doctor_name
        FROM doctors
        WHERE id=?
    """, (id,))

    doctor = cursor.fetchone()


    if not doctor:

        conn.close()

        flash(
            "Doctor not found.",
            "error"
        )

        return redirect(url_for("doctors"))


    # ==========================================
    # CHECK EXISTING APPOINTMENTS
    # ==========================================

    cursor.execute("""
        SELECT COUNT(*)
        FROM appointments
        WHERE doctor_id=?
        AND status IN ('Pending', 'Approved')
    """, (id,))

    active_appointments = cursor.fetchone()[0]


    if active_appointments > 0:

        conn.close()

        flash(
            "This doctor cannot be deleted because "
            "there are pending or approved appointments.",
            "error"
        )

        return redirect(url_for("doctors"))


    # ==========================================
    # DELETE DOCTOR
    # ==========================================

    cursor.execute("""
        DELETE FROM doctors
        WHERE id=?
    """, (id,))


    conn.commit()
    conn.close()


    flash(
        f"Doctor {doctor['doctor_name']} deleted successfully!",
        "success"
    )


    return redirect(url_for("doctors"))

@app.route("/admin/delete-hospital/<int:id>")
def delete_hospital(id):

    # Check admin access
    access_check = admin_required()

    if access_check:
        return access_check


    conn = get_connection()
    cursor = conn.cursor()


    # ----------------------------------------
    # CHECK HOSPITAL
    # ----------------------------------------

    cursor.execute("""
        SELECT id, hospital_name
        FROM hospitals
        WHERE id=?
    """, (id,))

    hospital = cursor.fetchone()


    if not hospital:

        conn.close()

        flash(
            "Hospital not found.",
            "error"
        )

        return redirect(
            url_for("hospitals")
        )


    # ----------------------------------------
    # CHECK ASSOCIATED DOCTORS
    # ----------------------------------------

    cursor.execute("""
        SELECT COUNT(*)
        FROM doctors
        WHERE hospital_id=?
    """, (id,))

    doctor_count = cursor.fetchone()[0]


    if doctor_count > 0:

        conn.close()

        flash(
            "This hospital cannot be deleted because "
            "doctors are still associated with it. "
            "Please remove or reassign the doctors first.",
            "error"
        )

        return redirect(
            url_for("hospitals")
        )


    # ----------------------------------------
    # CHECK ACTIVE APPOINTMENTS
    # ----------------------------------------

    cursor.execute("""
        SELECT COUNT(*)
        FROM appointments
        WHERE hospital_id=?
        AND status IN ('Pending', 'Approved')
    """, (id,))

    active_appointments = cursor.fetchone()[0]


    if active_appointments > 0:

        conn.close()

        flash(
            "This hospital cannot be deleted because "
            "it has pending or approved appointments.",
            "error"
        )

        return redirect(
            url_for("hospitals")
        )


    # ----------------------------------------
    # DELETE HOSPITAL
    # ----------------------------------------

    cursor.execute("""
        DELETE FROM hospitals
        WHERE id=?
    """, (id,))


    conn.commit()
    conn.close()


    flash(
        f"Hospital '{hospital['hospital_name']}' "
        "deleted successfully!",
        "success"
    )


    return redirect(
        url_for("hospitals")
    )

@app.route("/compare")
def compare():

    conn = get_connection()
    cursor = conn.cursor()

    # Get all hospitals for dropdowns
    cursor.execute("""
        SELECT *
        FROM hospitals
        ORDER BY hospital_name ASC
    """)

    hospitals = cursor.fetchall()

    hospital1 = None
    hospital2 = None

    services1 = []
    services2 = []

    doctors1 = []
    doctors2 = []

    id1 = request.args.get("hospital1")
    id2 = request.args.get("hospital2")

    # ================= HOSPITAL 1 =================

    if id1:

        cursor.execute("""
            SELECT *
            FROM hospitals
            WHERE id=?
        """, (id1,))

        hospital1 = cursor.fetchone()

        if hospital1:

            # Services of Hospital 1
            cursor.execute("""
                SELECT
                    service_name,
                    description,
                    cost
                FROM services
                WHERE hospital_id=?
                ORDER BY service_name ASC
            """, (id1,))

            services1 = cursor.fetchall()

            # Doctors of Hospital 1
            cursor.execute("""
                SELECT
                    id,
                    doctor_name,
                    specialization,
                    experience,
                    consultation_fee
                FROM doctors
                WHERE hospital_id=?
                ORDER BY doctor_name ASC
            """, (id1,))

            doctors1 = cursor.fetchall()

    # ================= HOSPITAL 2 =================

    if id2:

        cursor.execute("""
            SELECT *
            FROM hospitals
            WHERE id=?
        """, (id2,))

        hospital2 = cursor.fetchone()

        if hospital2:

            # Services of Hospital 2
            cursor.execute("""
                SELECT
                    service_name,
                    description,
                    cost
                FROM services
                WHERE hospital_id=?
                ORDER BY service_name ASC
            """, (id2,))

            services2 = cursor.fetchall()

            # Doctors of Hospital 2
            cursor.execute("""
                SELECT
                    id,
                    doctor_name,
                    specialization,
                    experience,
                    consultation_fee
                FROM doctors
                WHERE hospital_id=?
                ORDER BY doctor_name ASC
            """, (id2,))

            doctors2 = cursor.fetchall()

    # ================= COMPARISON SUMMARY =================

    rating1 = hospital1["rating"] if hospital1 and hospital1["rating"] else 0
    rating2 = hospital2["rating"] if hospital2 and hospital2["rating"] else 0

    # Count available facilities
    facilities1 = (
        (1 if hospital1["emergency"] else 0) +
        (1 if hospital1["ambulance"] else 0) +
        (1 if hospital1["icu"] else 0)
    ) if hospital1 else 0

    facilities2 = (
        (1 if hospital2["emergency"] else 0) +
        (1 if hospital2["ambulance"] else 0) +
        (1 if hospital2["icu"] else 0)
    ) if hospital2 else 0

    # Average doctor consultation fee
    doctor_fee1 = 0
    doctor_fee2 = 0

    if doctors1:
        doctor_fee1 = sum(
            doctor["consultation_fee"] or 0
            for doctor in doctors1
        ) / len(doctors1)

    if doctors2:
        doctor_fee2 = sum(
            doctor["consultation_fee"] or 0
            for doctor in doctors2
        ) / len(doctors2)

    # Determine rating winner
    if rating1 > rating2:
        rating_winner = hospital1["hospital_name"]

    elif rating2 > rating1:
        rating_winner = hospital2["hospital_name"]

    else:
        rating_winner = "Both hospitals have the same rating"

    # Determine facility winner
    if facilities1 > facilities2:
        facility_winner = hospital1["hospital_name"]

    elif facilities2 > facilities1:
        facility_winner = hospital2["hospital_name"]

    else:
        facility_winner = "Both hospitals offer the same facilities"

    # Determine consultation fee winner
    if doctor_fee1 and doctor_fee2:

        if doctor_fee1 < doctor_fee2:
            fee_winner = hospital1["hospital_name"]

        elif doctor_fee2 < doctor_fee1:
            fee_winner = hospital2["hospital_name"]

        else:
            fee_winner = "Both hospitals have similar consultation fees"

    else:
        fee_winner = "Not enough doctor fee information"

    conn.close()

    return render_template(
        "compare.html",
        hospitals=hospitals,
        hospital1=hospital1,
        hospital2=hospital2,
        services1=services1,
        services2=services2,
        doctors1=doctors1,
        doctors2=doctors2,
        rating_winner=rating_winner,
        facility_winner=facility_winner,
        fee_winner=fee_winner
    )

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        full_name = request.form["full_name"].strip()
        email = request.form["email"].strip()
        password = request.form["password"]

        conn = get_connection()
        cursor = conn.cursor()

        # Check whether email already exists
        cursor.execute(
            "SELECT id FROM users WHERE email=?",
            (email,)
        )

        existing_user = cursor.fetchone()

        if existing_user:
            conn.close()

            flash(
                "This email is already registered. Please use another email or login.",
                "danger"
            )

            return redirect("/register")

        # Create new user
        assigned_role = "admin" if email.strip().lower() == ADMIN_EMAIL.lower() else "user"
        cursor.execute("""
            INSERT INTO users(
                full_name,
                email,
                password,
                role
            )
            VALUES(?,?,?,?)
        """,
        (
            full_name,
            email,
            password,
            assigned_role
        ))

        conn.commit()
        conn.close()

        flash(
            "Registration Successful! Please login.",
            "success"
        )

        return redirect("/login")

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM users WHERE LOWER(email)=LOWER(?) AND password=?",
            (email.strip(), password)
        )

        user = cursor.fetchone()

        conn.close()

        if user:

            session["user_id"] = user["id"]
            session["user_name"] = user["full_name"]
            user_email = user["email"].strip() if user["email"] else ""
            session["user_email"] = user_email

            if user_email.lower() == ADMIN_EMAIL.lower():
                session["role"] = "admin"
                session["is_admin"] = True
                if user["role"] != "admin":
                    try:
                        c_conn = get_connection()
                        c_cursor = c_conn.cursor()
                        c_cursor.execute("UPDATE users SET role='admin' WHERE id=?", (user["id"],))
                        c_conn.commit()
                        c_conn.close()
                    except Exception:
                        pass
            else:
                session["role"] = "user"
                session["is_admin"] = False

            return redirect(url_for("home"))

        flash("Invalid Email or Password", "danger")
        return redirect("/login")

    return render_template("login.html")

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("home"))




@app.route("/admin/add-service", methods=["GET", "POST"])
def add_service():

    # Check admin access
    access_check = admin_required()

    if access_check:
        return access_check

    conn = get_connection()
    cursor = conn.cursor()

    # Get hospitals for the dropdown
    cursor.execute("""
        SELECT id, hospital_name
        FROM hospitals
        ORDER BY hospital_name ASC
    """)

    hospitals = cursor.fetchall()

    if request.method == "POST":

        hospital_id = request.form["hospital_id"]
        service_name = request.form["service_name"]
        description = request.form.get("description", "").strip()
        cost = request.form["cost"]

        cursor.execute("""
            INSERT INTO services (
                hospital_id,
                service_name,
                description,
                cost
            )
            VALUES (?, ?, ?, ?)
        """, (
            hospital_id,
            service_name,
            description,
            cost
        ))

        conn.commit()
        conn.close()

        flash(
            "Service added successfully!",
            "success"
        )

        return redirect(url_for("admin_services"))

    conn.close()

    return render_template(
        "admin/add_service.html",
        hospitals=hospitals
    )

@app.route("/admin/edit-service/<int:id>", methods=["GET", "POST"])
def edit_service(id):

    # Check admin access
    access_check = admin_required()

    if access_check:
        return access_check

    conn = get_connection()
    cursor = conn.cursor()

    # Get hospitals for dropdown
    cursor.execute("""
        SELECT id, hospital_name
        FROM hospitals
        ORDER BY hospital_name ASC
    """)

    hospitals = cursor.fetchall()

    if request.method == "POST":

        hospital_id = request.form["hospital_id"]
        service_name = request.form["service_name"]
        description = request.form.get("description", "").strip()
        cost = request.form["cost"]

        cursor.execute("""
            UPDATE services
            SET
                hospital_id=?,
                service_name=?,
                description=?,
                cost=?
            WHERE id=?
        """, (
            hospital_id,
            service_name,
            description,
            cost,
            id
        ))

        conn.commit()
        conn.close()

        flash(
            "Service updated successfully!",
            "success"
        )

        return redirect(url_for("admin_services"))

    # Get existing service
    cursor.execute("""
        SELECT *
        FROM services
        WHERE id=?
    """, (id,))

    service = cursor.fetchone()

    conn.close()

    if service is None:
        return "Service not found", 404

    return render_template(
        "admin/edit_service.html",
        service=service,
        hospitals=hospitals
    )


@app.route("/admin/delete-service/<int:id>")
def delete_service(id):

    # Check admin access
    access_check = admin_required()

    if access_check:
        return access_check

    conn = get_connection()
    cursor = conn.cursor()

    # Check whether the service exists
    cursor.execute("""
        SELECT id
        FROM services
        WHERE id=?
    """, (id,))

    service = cursor.fetchone()

    if service is None:
        conn.close()

        flash(
            "Service not found.",
            "error"
        )

        return redirect(url_for("admin_services"))

    # Delete service
    cursor.execute("""
        DELETE FROM services
        WHERE id=?
    """, (id,))

    conn.commit()
    conn.close()

    flash(
        "Service deleted successfully!",
        "success"
    )

    return redirect(url_for("admin_services"))


# =========================================================
# ADMIN REVIEW MODERATION ROUTES
# =========================================================

@app.route("/admin/reviews")
def admin_reviews():

    # Check admin access
    access_check = admin_required()
    if access_check:
        return access_check

    conn = get_connection()
    cursor = conn.cursor()

    hospital_filter = request.args.get("hospital_id", "").strip()

    query = """
        SELECT
            reviews.*,
            users.full_name as user_name,
            users.email as user_email,
            hospitals.hospital_name,
            hospitals.city as hospital_city
        FROM reviews
        JOIN users ON reviews.user_id = users.id
        JOIN hospitals ON reviews.hospital_id = hospitals.id
    """
    params = []

    if hospital_filter:
        query += " WHERE reviews.hospital_id=?"
        params.append(hospital_filter)

    query += " ORDER BY reviews.id DESC"

    cursor.execute(query, tuple(params))
    reviews = cursor.fetchall()

    # Get list of hospitals for filter dropdown
    cursor.execute("SELECT id, hospital_name FROM hospitals ORDER BY hospital_name ASC")
    hospitals = cursor.fetchall()

    cursor.execute("SELECT COUNT(*) FROM reviews")
    total_reviews = cursor.fetchone()[0]

    conn.close()

    return render_template(
        "admin/reviews.html",
        reviews=reviews,
        hospitals=hospitals,
        selected_hospital=hospital_filter,
        total_reviews=total_reviews,
        user_name=session.get("user_name")
    )


@app.route("/admin/delete-review/<int:id>", methods=["GET", "POST"])
def delete_review(id):

    # Check admin access
    access_check = admin_required()
    if access_check:
        return access_check

    conn = get_connection()
    cursor = conn.cursor()

    # Check whether the review exists
    cursor.execute("""
        SELECT id, hospital_id
        FROM reviews
        WHERE id=?
    """, (id,))

    review = cursor.fetchone()

    if review is None:
        conn.close()
        flash("Review not found.", "danger")
        return redirect(request.referrer or url_for("admin_reviews"))

    hospital_id = review["hospital_id"]

    # Delete the review
    cursor.execute("""
        DELETE FROM reviews
        WHERE id=?
    """, (id,))

    # Recalculate average rating for this hospital
    cursor.execute("""
        SELECT AVG(rating)
        FROM reviews
        WHERE hospital_id=?
    """, (hospital_id,))

    avg_row = cursor.fetchone()
    average_rating = avg_row[0] if avg_row and avg_row[0] is not None else 0.0

    # Update hospital rating
    cursor.execute("""
        UPDATE hospitals
        SET rating=?
        WHERE id=?
    """, (round(average_rating, 1), hospital_id))

    conn.commit()
    conn.close()

    flash("Review deleted successfully! Hospital average rating has been recalculated.", "success")
    return redirect(request.referrer or f"/hospital/{hospital_id}")


@app.route("/service-comparison")
def service_comparison():

    conn = get_connection()
    cursor = conn.cursor()

    # Get all available services
    cursor.execute("""
        SELECT DISTINCT service_name
        FROM services
        ORDER BY service_name ASC
    """)

    services = cursor.fetchall()

    selected_service = request.args.get("service")

    results = []

    if selected_service:

        cursor.execute("""
            SELECT
                hospitals.id as hospital_id,
                hospitals.hospital_name,
                hospitals.city,
                services.service_name,
                services.description,
                services.cost
            FROM services

            JOIN hospitals
            ON hospitals.id = services.hospital_id

            WHERE services.service_name=?

            ORDER BY services.cost ASC
        """, (selected_service,))

        results = cursor.fetchall()

    conn.close()

    return render_template(
        "service_comparison.html",
        services=services,
        results=results,
        selected_service=selected_service
    )


@app.route("/profile")
def profile():

    if "user_id" not in session:
        return redirect("/login")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, full_name, email
        FROM users
        WHERE id=?
    """, (session["user_id"],))

    user = cursor.fetchone()

    cursor.execute("""
        SELECT COUNT(*)
        FROM favorites
        WHERE user_id=?
    """, (session["user_id"],))

    total_favorites = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM appointments
        WHERE user_id=?
    """, (session["user_id"],))

    total_appointments = cursor.fetchone()[0]

    conn.close()

    return render_template(
        "profile.html",
        user=user,
        total_favorites=total_favorites,
        total_appointments=total_appointments,
        user_name=session.get("user_name")
    )



@app.route("/my-appointments")
def my_appointments():

    if "user_id" not in session:
        return redirect("/login")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            appointments.id,
            appointments.appointment_date,
            appointments.appointment_time,
            appointments.reason,
            appointments.status,

            hospitals.hospital_name,
            hospitals.city,

            doctors.doctor_name,
            doctors.specialization,
            doctors.consultation_fee

        FROM appointments

        JOIN hospitals
            ON appointments.hospital_id = hospitals.id

        JOIN doctors
            ON appointments.doctor_id = doctors.id

        WHERE appointments.user_id=?

        ORDER BY appointments.appointment_date DESC,
                 appointments.appointment_time ASC
    """, (session["user_id"],))

    appointments = cursor.fetchall()

    conn.close()

    return render_template(
        "my_appointments.html",
        appointments=appointments
    )
@app.route("/cancel-appointment/<int:appointment_id>")
def cancel_appointment(appointment_id):

    if "user_id" not in session:
        return redirect("/login")

    conn = get_connection()
    cursor = conn.cursor()

    # Make sure this appointment belongs to the logged-in user
    cursor.execute("""
        SELECT id, status
        FROM appointments
        WHERE id=? AND user_id=?
    """, (
        appointment_id,
        session["user_id"]
    ))

    appointment = cursor.fetchone()

    if not appointment:
        conn.close()

        flash(
            "Appointment not found.",
            "error"
        )

        return redirect("/my-appointments")


    # Only Pending or Approved appointments can be cancelled
    if appointment["status"] not in ["Pending", "Approved"]:

        conn.close()

        flash(
            "This appointment cannot be cancelled.",
            "error"
        )

        return redirect("/my-appointments")


    # Cancel appointment
    cursor.execute("""
        UPDATE appointments
        SET status='Cancelled'
        WHERE id=? AND user_id=?
    """, (
        appointment_id,
        session["user_id"]
    ))

    conn.commit()
    conn.close()

    flash(
        "Appointment cancelled successfully.",
        "success"
    )

    return redirect("/my-appointments")

@app.route("/book-appointment/<int:hospital_id>", methods=["GET", "POST"])
def book_appointment(hospital_id):

    # ==========================================
    # USER MUST BE LOGGED IN
    # ==========================================

    if "user_id" not in session:
        return redirect("/login")


    conn = get_connection()
    cursor = conn.cursor()


    # ==========================================
    # GET HOSPITAL
    # ==========================================

    cursor.execute("""
        SELECT *
        FROM hospitals
        WHERE id=?
    """, (hospital_id,))

    hospital = cursor.fetchone()


    if not hospital:

        conn.close()

        flash(
            "Hospital not found.",
            "error"
        )

        return redirect("/")


    # ==========================================
    # GET DOCTORS
    # ==========================================

    cursor.execute("""
        SELECT *
        FROM doctors
        WHERE hospital_id=?
        ORDER BY doctor_name ASC
    """, (hospital_id,))

    doctors = cursor.fetchall()


    # ==========================================
    # SELECTED DOCTOR
    # ==========================================

    selected_doctor_id = request.args.get("doctor_id")

    selected_doctor = None


    if selected_doctor_id:

        cursor.execute("""
            SELECT *
            FROM doctors
            WHERE id=?
            AND hospital_id=?
        """, (
            selected_doctor_id,
            hospital_id
        ))

        selected_doctor = cursor.fetchone()


    # ==========================================
    # POST - BOOK APPOINTMENT
    # ==========================================

    if request.method == "POST":

        doctor_id = request.form.get("doctor_id")

        appointment_date = request.form.get(
            "appointment_date"
        )

        appointment_time = request.form.get(
            "appointment_time"
        )

        reason = request.form.get(
            "reason",
            ""
        ).strip()


        # ======================================
        # VALIDATION
        # ======================================

        if (
            not doctor_id
            or not appointment_date
            or not appointment_time
        ):

            flash(
                "Please select a doctor, appointment date and appointment time.",
                "error"
            )

            conn.close()

            return render_template(
                "book_appointment.html",
                hospital=hospital,
                doctors=doctors,
                selected_doctor_id=doctor_id,
                selected_doctor=selected_doctor,
                booked_times=[]
            )


        # ======================================
        # GET SELECTED DOCTOR
        # ======================================

        cursor.execute("""
            SELECT *
            FROM doctors
            WHERE id=?
            AND hospital_id=?
        """, (
            doctor_id,
            hospital_id
        ))

        selected_doctor = cursor.fetchone()


        if not selected_doctor:

            flash(
                "Invalid doctor selected.",
                "error"
            )

            conn.close()

            return render_template(
                "book_appointment.html",
                hospital=hospital,
                doctors=doctors,
                selected_doctor_id=doctor_id,
                selected_doctor=None,
                booked_times=[]
            )


        # ======================================
        # CHECK DOCTOR AVAILABLE DAY
        # ======================================

        available_days = (
            selected_doctor["available_days"]
            or ""
        )


        if available_days:

            from datetime import datetime

            try:

                selected_date = datetime.strptime(
                    appointment_date,
                    "%Y-%m-%d"
                )

            except ValueError:

                flash(
                    "Invalid appointment date.",
                    "error"
                )

                conn.close()

                return render_template(
                    "book_appointment.html",
                    hospital=hospital,
                    doctors=doctors,
                    selected_doctor_id=doctor_id,
                    selected_doctor=selected_doctor,
                    booked_times=[]
                )


            selected_day = (
                selected_date.strftime("%A")
            )


            allowed_days = [
                day.strip().lower()
                for day in available_days.split(",")
            ]


            if selected_day.lower() not in allowed_days:

                flash(
                    f"{selected_doctor['doctor_name']} is not available on "
                    f"{selected_day}. "
                    f"Available days: {available_days}",
                    "error"
                )

                conn.close()

                return render_template(
                    "book_appointment.html",
                    hospital=hospital,
                    doctors=doctors,
                    selected_doctor_id=doctor_id,
                    selected_doctor=selected_doctor,
                    booked_times=[]
                )


        # ======================================
        # GET ALREADY BOOKED TIMES
        # ======================================

        cursor.execute("""
            SELECT appointment_time
            FROM appointments
            WHERE doctor_id=?
            AND appointment_date=?
            AND status NOT IN ('Rejected', 'Cancelled')
            AND appointment_time IS NOT NULL
        """, (
            doctor_id,
            appointment_date
        ))


        booked_rows = cursor.fetchall()


        booked_times = [
            row["appointment_time"]
            for row in booked_rows
            if row["appointment_time"]
        ]


        # ======================================
        # CHECK DOUBLE BOOKING
        # ======================================

        if appointment_time in booked_times:

            flash(
                f"{appointment_time} is already booked for "
                f"{selected_doctor['doctor_name']} on "
                f"{appointment_date}. Please select another time.",
                "error"
            )

            conn.close()

            return render_template(
                "book_appointment.html",
                hospital=hospital,
                doctors=doctors,
                selected_doctor_id=doctor_id,
                selected_doctor=selected_doctor,
                booked_times=booked_times
            )


        # ======================================
        # CREATE APPOINTMENT
        # ======================================

        cursor.execute("""
            INSERT INTO appointments (
                user_id,
                hospital_id,
                doctor_id,
                appointment_date,
                appointment_time,
                reason,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?, 'Pending')
        """, (
            session["user_id"],
            hospital_id,
            doctor_id,
            appointment_date,
            appointment_time,
            reason
        ))


        conn.commit()
        conn.close()


        flash(
            "Appointment booked successfully! "
            "Waiting for admin approval.",
            "success"
        )


        return redirect("/my-appointments")


    # ==========================================
    # GET ALREADY BOOKED TIMES
    # ==========================================

    booked_times = []


    if selected_doctor_id:

        # No date selected yet, so we cannot
        # determine booked slots for a particular date.

        booked_times = []


    # ==========================================
    # SHOW BOOKING PAGE
    # ==========================================

    conn.close()


    return render_template(
        "book_appointment.html",
        hospital=hospital,
        doctors=doctors,
        selected_doctor_id=selected_doctor_id,
        selected_doctor=selected_doctor,
        booked_times=booked_times
    )
   


@app.route("/admin/appointments")
def admin_appointments():

    # ==========================================
    # CHECK ADMIN ACCESS
    # ==========================================

    access_check = admin_required()

    if access_check:
        return access_check


    # ==========================================
    # DATABASE CONNECTION
    # ==========================================

    conn = get_connection()
    cursor = conn.cursor()


    # ==========================================
    # GET STATUS FILTER
    # ==========================================

    status_filter = request.args.get("status")


    # ==========================================
    # GET APPOINTMENTS
    # ==========================================

    query = """
        SELECT
            appointments.id,
            appointments.appointment_date,
            appointments.appointment_time,
            appointments.reason,
            appointments.status,

            users.full_name,

            hospitals.hospital_name,

            doctors.doctor_name,
            doctors.specialization

        FROM appointments

        JOIN users
            ON appointments.user_id = users.id

        JOIN hospitals
            ON appointments.hospital_id = hospitals.id

        JOIN doctors
            ON appointments.doctor_id = doctors.id
    """


    # ==========================================
    # APPLY STATUS FILTER
    # ==========================================

    if status_filter in [
        "Pending",
        "Approved",
        "Rejected",
        "Cancelled"
    ]:

        query += """
            WHERE appointments.status=?
        """

        query += """
            ORDER BY
                appointments.appointment_date DESC,
                appointments.appointment_time ASC
        """

        cursor.execute(
            query,
            (status_filter,)
        )

    else:

        query += """
            ORDER BY
                appointments.appointment_date DESC,
                appointments.appointment_time ASC
        """

        cursor.execute(query)


    appointments = cursor.fetchall()


    # ==========================================
    # APPOINTMENT COUNTS
    # ==========================================

    cursor.execute("""
        SELECT COUNT(*)
        FROM appointments
    """)

    total = cursor.fetchone()[0]


    cursor.execute("""
        SELECT COUNT(*)
        FROM appointments
        WHERE status='Pending'
    """)

    pending = cursor.fetchone()[0]


    cursor.execute("""
        SELECT COUNT(*)
        FROM appointments
        WHERE status='Approved'
    """)

    approved = cursor.fetchone()[0]


    cursor.execute("""
        SELECT COUNT(*)
        FROM appointments
        WHERE status='Rejected'
    """)

    rejected = cursor.fetchone()[0]


    cursor.execute("""
        SELECT COUNT(*)
        FROM appointments
        WHERE status='Cancelled'
    """)

    cancelled = cursor.fetchone()[0]


    # ==========================================
    # CREATE COUNTS DICTIONARY
    # ==========================================

    appointment_counts = {

        "total": total,

        "pending": pending,

        "approved": approved,

        "rejected": rejected,

        "cancelled": cancelled

    }


    # ==========================================
    # CLOSE DATABASE
    # ==========================================

    conn.close()


    # ==========================================
    # SHOW PAGE
    # ==========================================

    return render_template(

        "admin/appointments.html",

        appointments=appointments,

        status_filter=status_filter,

        appointment_counts=appointment_counts

    )

@app.route("/admin/approve/<int:appointment_id>")
def approve_appointment(appointment_id):

    access_check = admin_required()

    if access_check:
        return access_check

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE appointments
        SET status='Approved'
        WHERE id=?
    """, (appointment_id,))

    conn.commit()
    conn.close()

    flash(
        "Appointment approved successfully!",
        "success"
    )

    return redirect("/admin/appointments")

@app.route("/admin/reject/<int:appointment_id>")
def reject_appointment(appointment_id):

    access_check = admin_required()

    if access_check:
        return access_check

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE appointments
        SET status='Rejected'
        WHERE id=?
    """, (appointment_id,))

    conn.commit()
    conn.close()

    flash(
        "Appointment rejected successfully.",
        "success"
    )

    return redirect("/admin/appointments")

@app.route("/admin/appointment/<int:id>/<status>")
def update_appointment_status(id, status):

    access_check = admin_required()
    if access_check:
        return access_check

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE appointments
        SET status=?
        WHERE id=?
    """,(status,id))

    conn.commit()
    conn.close()

    return redirect("/admin/appointments")

@app.route("/admin/complete/<int:id>")
def complete_appointment(id):

    access_check = admin_required()
    if access_check:
        return access_check

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE appointments
        SET status='Completed'
        WHERE id=?
    """, (id,))

    conn.commit()
    conn.close()

    return redirect("/admin/appointments")


# =========================================================
# FAVORITES
# =========================================================

@app.route("/add-favorite/<int:hospital_id>")
def add_hospital_favorite(hospital_id):

    if "user_id" not in session:
        return redirect("/login")

    conn = get_connection()
    cursor = conn.cursor()

    # Check whether hospital exists
    cursor.execute(
        "SELECT id FROM hospitals WHERE id=?",
        (hospital_id,)
    )

    hospital = cursor.fetchone()

    if not hospital:
        conn.close()
        return "Hospital not found", 404

    # Check whether already a favorite
    cursor.execute("""
        SELECT id
        FROM favorites
        WHERE user_id=? AND hospital_id=?
    """, (
        session["user_id"],
        hospital_id
    ))

    existing = cursor.fetchone()

    # Add only if it is not already a favorite
    if not existing:

        cursor.execute("""
            INSERT INTO favorites
            (user_id, hospital_id)
            VALUES (?, ?)
        """, (
            session["user_id"],
            hospital_id
        ))

        conn.commit()

    conn.close()

    return redirect("/hospital/" + str(hospital_id))


@app.route("/remove-favorite/<int:hospital_id>")
def remove_hospital_favorite(hospital_id):

    if "user_id" not in session:
        return redirect("/login")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM favorites
        WHERE user_id=? AND hospital_id=?
    """, (
        session["user_id"],
        hospital_id
    ))

    conn.commit()
    conn.close()

    return redirect("/hospital/" + str(hospital_id))


@app.route("/favorites")
def favorites():

    if "user_id" not in session:
        return redirect("/login")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT hospitals.*
        FROM favorites
        JOIN hospitals
        ON favorites.hospital_id = hospitals.id
        WHERE favorites.user_id=?
        ORDER BY favorites.id DESC
    """, (
        session["user_id"],
    ))

    favorites = cursor.fetchall()

    conn.close()

    return render_template(
        "favorites.html",
        favorites=favorites,
        user_id=session.get("user_id"),
        user_name=session.get("user_name")
    )


@app.route("/admin")
def admin_dashboard():

    # Check admin access
    access_check = admin_required()

    if access_check:
        return access_check

    conn = get_connection()
    cursor = conn.cursor()

    # Total hospitals
    cursor.execute("SELECT COUNT(*) FROM hospitals")
    total_hospitals = cursor.fetchone()[0]

    # Total doctors
    cursor.execute("SELECT COUNT(*) FROM doctors")
    total_doctors = cursor.fetchone()[0]

    # Total users
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]

    # Total appointments
    cursor.execute("SELECT COUNT(*) FROM appointments")
    total_appointments = cursor.fetchone()[0]

    # Pending appointments
    cursor.execute("""
        SELECT COUNT(*)
        FROM appointments
        WHERE status='Pending'
    """)
    pending_appointments = cursor.fetchone()[0]

    # Approved appointments
    cursor.execute("""
        SELECT COUNT(*)
        FROM appointments
        WHERE status='Approved'
    """)
    approved_appointments = cursor.fetchone()[0]

    # Rejected appointments
    cursor.execute("""
        SELECT COUNT(*)
        FROM appointments
        WHERE status='Rejected'
    """)
    rejected_appointments = cursor.fetchone()[0]

    conn.close()

    return render_template(
        "admin/dashboard.html",
        total_hospitals=total_hospitals,
        total_doctors=total_doctors,
        total_users=total_users,
        total_appointments=total_appointments,
        pending_appointments=pending_appointments,
        approved_appointments=approved_appointments,
        rejected_appointments=rejected_appointments
    )

@app.route("/api/booked-times/<int:doctor_id>")
def booked_times(doctor_id):

    # User must be logged in
    if "user_id" not in session:
        return jsonify({
            "error": "Login required"
        }), 401

    appointment_date = request.args.get("date")

    if not appointment_date:
        return jsonify({
            "booked_times": []
        })

    conn = get_connection()
    cursor = conn.cursor()

    # Make sure doctor exists
    cursor.execute("""
        SELECT id
        FROM doctors
        WHERE id=?
    """, (doctor_id,))

    doctor = cursor.fetchone()

    if not doctor:
        conn.close()

        return jsonify({
            "error": "Doctor not found"
        }), 404

    # Get already booked times
    cursor.execute("""
        SELECT appointment_time
        FROM appointments
        WHERE doctor_id=?
        AND appointment_date=?
        AND status NOT IN ('Rejected', 'Cancelled')
        AND appointment_time IS NOT NULL
    """, (
        doctor_id,
        appointment_date
    ))

    rows = cursor.fetchall()

    booked = [
        row["appointment_time"]
        for row in rows
        if row["appointment_time"]
    ]

    conn.close()

    return jsonify({
        "booked_times": booked
    })

if __name__ == "__main__":
    app.run(debug=True)

