import os, uuid
from datetime import datetime
from functools import wraps
from dotenv import load_dotenv

load_dotenv()

import boto3
from boto3.dynamodb.conditions import Key
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    abort,
)
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ["SECRET_KEY"]
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")

REGION = os.environ.get("AWS_REGION", "ap-southeast-2")
TOPIC_ARN = os.environ["SNS_TOPIC_ARN"]

dynamodb = boto3.resource("dynamodb", region_name=REGION)
sns = boto3.client("sns", region_name=REGION)
patients = dynamodb.Table("Patients")
doctors = dynamodb.Table("Doctors")
appointments = dynamodb.Table("Appointments")
diagnoses = dynamodb.Table("Diagnoses")


# ---------- helpers ----------
def login_required(role):
    def deco(f):
        @wraps(f)
        def wrapper(*a, **kw):
            if session.get("role") != role:
                flash("Please log in.")
                return redirect(
                    url_for("login" if role == "patient" else "doctor_login")
                )
            return f(*a, **kw)

        return wrapper

    return deco


def find_by_email(table, email):
    r = table.query(
        IndexName="EmailIndex", KeyConditionExpression=Key("Email").eq(email)
    )
    return r["Items"][0] if r["Items"] else None


def subscribe_patient(email, patient_id):
    """Each patient subscribes with a filter so they only get their own messages."""
    try:
        sns.subscribe(
            TopicArn=TOPIC_ARN,
            Protocol="email",
            Endpoint=email,
            Attributes={"FilterPolicy": f'{{"patient_id": ["{patient_id}"]}}'},
        )
    except Exception as e:
        app.logger.error("SNS subscribe failed: %s", e)


def notify(patient_id, subject, message):
    try:
        sns.publish(
            TopicArn=TOPIC_ARN,
            Subject=subject[:99],
            Message=message,
            MessageAttributes={
                "patient_id": {"DataType": "String", "StringValue": patient_id}
            },
        )
    except Exception as e:
        app.logger.error("SNS publish failed: %s", e)  # never break the workflow


# ---------- public / auth ----------
@app.route("/")
def home():
    return render_template("home.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        if find_by_email(patients, email):
            flash("Email already registered.")
            return redirect(url_for("register"))
        pid = str(uuid.uuid4())
        patients.put_item(
            Item={
                "PatientID": pid,
                "Name": request.form["name"],
                "Email": email,
                "Age": request.form["age"],
                "Gender": request.form["gender"],
                "PasswordHash": generate_password_hash(request.form["password"]),
                "CreatedAt": datetime.utcnow().isoformat(),
            }
        )
        subscribe_patient(email, pid)
        flash("Registered! Confirm the SNS subscription email, then log in.")
        return redirect(url_for("login"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = find_by_email(patients, request.form["email"].strip().lower())
        if user and check_password_hash(user["PasswordHash"], request.form["password"]):
            session.clear()
            session.update(role="patient", user_id=user["PatientID"], name=user["Name"])
            return redirect(url_for("patient_dashboard"))
        flash("Invalid credentials.")
    return render_template("login.html", role="patient")


@app.route("/doctor/login", methods=["GET", "POST"])
def doctor_login():
    if request.method == "POST":
        doc = find_by_email(doctors, request.form["email"].strip().lower())
        if doc and check_password_hash(doc["PasswordHash"], request.form["password"]):
            session.clear()
            session.update(role="doctor", user_id=doc["DoctorID"], name=doc["Name"])
            return redirect(url_for("doctor_dashboard"))
        flash("Invalid credentials.")
    return render_template("login.html", role="doctor")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


# ---------- patient ----------
@app.route("/dashboard")
@login_required("patient")
def patient_dashboard():
    r = appointments.query(
        IndexName="PatientIndex",
        KeyConditionExpression=Key("PatientID").eq(session["user_id"]),
    )
    items = sorted(
        r["Items"], key=lambda x: (x["AppointmentDate"], x["AppointmentTime"])
    )
    return render_template("patient_dashboard.html", appointments=items)


@app.route("/book", methods=["GET", "POST"])
@login_required("patient")
def book():
    docs = doctors.scan(
        ProjectionExpression="DoctorID, #n, Specialty",
        ExpressionAttributeNames={"#n": "Name"},
    )["Items"]
    if request.method == "POST":
        doctor_id, date, time = (
            request.form["doctor_id"],
            request.form["date"],
            request.form["time"],
        )
        # prevent double-booking
        taken = appointments.query(
            IndexName="DoctorIndex",
            KeyConditionExpression=Key("DoctorID").eq(doctor_id)
            & Key("AppointmentDate").eq(date),
        )["Items"]
        if any(
            a["AppointmentTime"] == time and a["Status"] != "Cancelled" for a in taken
        ):
            flash("That slot is already booked.")
            return redirect(url_for("book"))
        doctor = next(d for d in docs if d["DoctorID"] == doctor_id)
        appt_id = str(uuid.uuid4())
        appointments.put_item(
            Item={
                "AppointmentID": appt_id,
                "PatientID": session["user_id"],
                "PatientName": session["name"],
                "DoctorID": doctor_id,
                "DoctorName": doctor["Name"],
                "AppointmentDate": date,
                "AppointmentTime": time,
                "Reason": request.form["reason"],
                "Status": "Booked",
                "CreatedAt": datetime.utcnow().isoformat(),
            }
        )
        notify(
            session["user_id"],
            "MedTrack: Appointment confirmed",
            f"Hi {session['name']}, your appointment with {doctor['Name']} is on {date} at {time}.",
        )
        flash("Appointment booked.")
        return redirect(url_for("patient_dashboard"))
    return render_template("book.html", doctors=docs)


@app.route("/history")
@login_required("patient")
def history():
    r = diagnoses.query(
        IndexName="PatientIndex",
        KeyConditionExpression=Key("PatientID").eq(session["user_id"]),
        ScanIndexForward=False,
    )
    return render_template(
        "history.html", records=r["Items"], patient_name=session["name"]
    )


# ---------- doctor ----------
@app.route("/doctor/dashboard")
@login_required("doctor")
def doctor_dashboard():
    r = appointments.query(
        IndexName="DoctorIndex",
        KeyConditionExpression=Key("DoctorID").eq(session["user_id"]),
    )
    return render_template("doctor_dashboard.html", appointments=r["Items"])


@app.route("/doctor/diagnose/<appointment_id>", methods=["GET", "POST"])
@login_required("doctor")
def diagnose(appointment_id):
    appt = appointments.get_item(Key={"AppointmentID": appointment_id}).get("Item")
    if not appt or appt["DoctorID"] != session["user_id"]:
        abort(403)  # role + ownership check
    if request.method == "POST":
        diagnoses.put_item(
            Item={
                "DiagnosisID": str(uuid.uuid4()),
                "AppointmentID": appointment_id,
                "PatientID": appt["PatientID"],
                "DoctorID": session["user_id"],
                "DoctorName": session["name"],
                "Diagnosis": request.form["diagnosis"],
                "Prescription": request.form["prescription"],
                "Notes": request.form["notes"],
                "CreatedAt": datetime.utcnow().isoformat(),
            }
        )
        appointments.update_item(
            Key={"AppointmentID": appointment_id},
            UpdateExpression="SET #s = :s",
            ExpressionAttributeNames={"#s": "Status"},
            ExpressionAttributeValues={":s": "Completed"},
        )
        notify(
            appt["PatientID"],
            "MedTrack: New diagnosis report",
            f"{session['name']} has submitted your diagnosis. Log in to view it.",
        )
        flash("Diagnosis submitted.")
        return redirect(url_for("doctor_dashboard"))
    return render_template("diagnose.html", appt=appt)


@app.route("/doctor/patient/<patient_id>")
@login_required("doctor")
def patient_history_for_doctor(patient_id):
    # doctor may view only patients they have an appointment with
    mine = appointments.query(
        IndexName="DoctorIndex",
        KeyConditionExpression=Key("DoctorID").eq(session["user_id"]),
    )["Items"]
    match = next((a for a in mine if a["PatientID"] == patient_id), None)
    if not match:
        abort(403)
    r = diagnoses.query(
        IndexName="PatientIndex",
        KeyConditionExpression=Key("PatientID").eq(patient_id),
        ScanIndexForward=False,
    )
    return render_template(
        "history.html", records=r["Items"], patient_name=match["PatientName"]
    )


if __name__ == "__main__":
    app.run(debug=False)
