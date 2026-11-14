import boto3, uuid
from werkzeug.security import generate_password_hash

REGION = "ap-southeast-2"
db = boto3.resource("dynamodb", region_name=REGION)


def gsi(name, hash_key, range_key=None):
    ks = [{"AttributeName": hash_key, "KeyType": "HASH"}]
    if range_key:
        ks.append({"AttributeName": range_key, "KeyType": "RANGE"})
    return {"IndexName": name, "KeySchema": ks, "Projection": {"ProjectionType": "ALL"}}


def attrs(*names):
    return [{"AttributeName": n, "AttributeType": "S"} for n in names]


def create(name, pk, attributes, indexes=None):
    kwargs = dict(
        TableName=name,
        KeySchema=[{"AttributeName": pk, "KeyType": "HASH"}],
        AttributeDefinitions=attributes,
        BillingMode="PAY_PER_REQUEST",
    )
    if indexes:
        kwargs["GlobalSecondaryIndexes"] = indexes
    t = db.create_table(**kwargs)
    t.wait_until_exists()
    print("Created", name)


create(
    "Patients", "PatientID", attrs("PatientID", "Email"), [gsi("EmailIndex", "Email")]
)
create("Doctors", "DoctorID", attrs("DoctorID", "Email"), [gsi("EmailIndex", "Email")])
create(
    "Appointments",
    "AppointmentID",
    attrs("AppointmentID", "PatientID", "DoctorID", "AppointmentDate"),
    [
        gsi("PatientIndex", "PatientID"),
        gsi("DoctorIndex", "DoctorID", "AppointmentDate"),
    ],
)
create(
    "Diagnoses",
    "DiagnosisID",
    attrs("DiagnosisID", "PatientID", "CreatedAt"),
    [gsi("PatientIndex", "PatientID", "CreatedAt")],
)

# Seed a doctor (doctors are created by admins, never by self-registration)
db.Table("Doctors").put_item(
    Item={
        "DoctorID": str(uuid.uuid4()),
        "Name": "Dr. Asha Rao",
        "Specialty": "General Medicine",
        "Email": "doctor@medtrack.com",
        "PasswordHash": generate_password_hash("ChangeMe123!"),
    }
)
