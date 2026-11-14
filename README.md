# MedTrack
Cloud-based healthcare management platform built with Flask and AWS (EC2, DynamoDB, SNS, IAM) for appointment booking, diagnosis reports and medical history.
# MedTrack: Cloud-Powered Healthcare Management Platform

MedTrack is a web application that streamlines patient-doctor interactions. Patients can register, book appointments and view their medical history. Doctors can manage appointments and submit diagnosis reports. Email notifications are sent automatically through AWS SNS.

Built with **Flask** and deployed on **AWS EC2** using **DynamoDB**, **SNS**, **IAM** and **CloudWatch**.

## Features

- Patient registration and login (hashed passwords, session-based auth)
- Doctor login with role-based access control
- Appointment booking with double-booking prevention
- Diagnosis, prescription and notes submission by doctors
- Medical history view for patients (own records) and doctors (own patients only)
- Email notifications via AWS SNS for booking confirmations and diagnosis updates
- Per-patient SNS filter policy, so each patient receives only their own messages
- Dashboards with appointment summaries for patients and doctors

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python, Flask |
| Database | AWS DynamoDB |
| Notifications | AWS SNS |
| Access control | AWS IAM (least-privilege role) + Flask role checks |
| Hosting | AWS EC2, Gunicorn, Nginx |
| Monitoring | AWS CloudWatch |
| Frontend | HTML, CSS, JavaScript (Jinja2 templates) |

## Project Structure

```
medtrack/
├── app.py                 # Flask application and routes
├── create_tables.py       # Creates DynamoDB tables and seeds a doctor
├── requirements.txt
├── .env.example           # Names of required environment variables
├── templates/             # HTML pages (Jinja2)
└── static/
    ├── css/style.css
    └── js/main.js
```

## Database Design (DynamoDB)

| Table | Partition key | Index | Purpose |
|---|---|---|---|
| Patients | PatientID | EmailIndex (Email) | Patient accounts and login lookup |
| Doctors | DoctorID | EmailIndex (Email) | Doctor profiles and login |
| Appointments | AppointmentID | PatientIndex, DoctorIndex (DoctorID + AppointmentDate) | Per-user views and slot checks |
| Diagnoses | DiagnosisID | PatientIndex (PatientID + CreatedAt) | Medical history |

## Getting Started (Local)

**Prerequisites:** Python 3.10+, an AWS account, AWS CLI configured (`aws configure`).

```bash
git clone https://github.com/<your-username>/medtrack.git
cd medtrack
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Mac/Linux
pip install -r requirements.txt
```

Create a `.env` file (never commit it):

```
SECRET_KEY=<long random string>
SNS_TOPIC_ARN=arn:aws:sns:<region>:<account-id>:<topic-name>
AWS_REGION=<region>
```

Generate a secret key with:
```bash
python -c "import secrets;print(secrets.token_hex(32))"
```

Create the tables and run the app:

```bash
python create_tables.py
python app.py
```

Open http://127.0.0.1:5000

## Roles and Access

| Role | Can do |
|---|---|
| Patient | Register, book appointments, view own history |
| Doctor | View own appointments, submit diagnoses, view history of own patients |

Doctors are created by an administrator (seeded in `create_tables.py`). Change the seeded password before any real use.

## Deployment (AWS EC2)

1. Launch an EC2 instance (Amazon Linux 2023) with an IAM instance profile.
2. Attach a least-privilege IAM policy (DynamoDB tables, SNS topic, CloudWatch logs).
3. Install dependencies and copy the project to the server.
4. Run the app with Gunicorn as a systemd service, behind Nginx.
5. Open ports 80/443 only, and restrict SSH to your IP.
6. Add HTTPS and set `SESSION_COOKIE_SECURE=True`.

## Security

- Passwords stored as hashes (Werkzeug)
- No AWS keys in code (IAM role on EC2, `.env` locally)
- Role-based and ownership checks on every protected route
- Least-privilege IAM policy for the application
- Secrets excluded from Git via `.gitignore`

## Future Improvements

- Appointment cancellation and rescheduling
- Appointment reminders (EventBridge + Lambda + SNS)
- Report file uploads to S3
- Admin panel for managing doctors
- Automated tests (pytest + moto)

## License

For educational purposes.
