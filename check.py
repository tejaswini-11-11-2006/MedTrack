from dotenv import load_dotenv

load_dotenv()
import os, boto3

region = os.environ.get("AWS_REGION")
print("Region from .env :", region)

print("Account          :", boto3.client("sts").get_caller_identity()["Account"])

db = boto3.client("dynamodb", region_name=region)
tables = db.list_tables()["TableNames"]
print("Tables           :", tables)

for t in ["Patients", "Doctors", "Appointments", "Diagnoses"]:
    if t in tables:
        d = db.describe_table(TableName=t)["Table"]
        idx = [
            (i["IndexName"], i["IndexStatus"])
            for i in d.get("GlobalSecondaryIndexes", [])
        ]
        print(t, "->", d["TableStatus"], idx)
    else:
        print(t, "-> MISSING")
