import stripe
from flask import render_template, request, redirect, session, flash
from flask_app import app
from flask_bcrypt import Bcrypt
import os
import requests
import gspread
from google.oauth2.service_account import Credentials
import boto3
import stripe

# GOOGLE API configuration
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
client = gspread.authorize(creds)
SPREAD_SHEET_ID = os.environ.get("SPREADSHEET_ID")

# S3 IAM configuration
AWS_ACCESS_KEY = os.environ.get("AWS_ACCESS_KEY")
AWS_SECRET_KEY = os.environ.get("AWS_SECRET_KEY")
bucket_name = os.environ.get("BUCKET_NAME")
region_name = os.environ.get("REGION_NAME")

# STRIPE configuration
stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")
LOCAL_DOMAIN = os.environ.get("LOCAL_DOMAIN")

# setting up boto3.resource (boto3.client is also an option)
# can retrieve and interact with objects by iterative over the resource object in the bucket
# setting up boto3.client to generate presigned URL
s3_client = boto3.client('s3',
                         region_name=region_name,
                         aws_access_key_id=AWS_ACCESS_KEY,
                         aws_secret_access_key=AWS_SECRET_KEY
                         )
# access the resource bucket
client_response = s3_client.list_objects_v2(Bucket=bucket_name)

# generate presigned_url with 30 minutes access
def generate_presigned_url():
    s3_data = []
    for obj in client_response['Contents']:
        # print(f"client response: {obj}")
        obj_key = (obj['Key'])
        presigned_url = s3_client.generate_presigned_url(
            ClientMethod='get_object',
            Params={
                'Bucket': bucket_name,
                'Key': obj_key,
            }
        )
        s3_data.append({
            'URL': obj_key,
            'Temp URL': presigned_url
        })
    #print(s3_data)
    return s3_data

def get_gsheet_data():
    sheet = client.open_by_key(SPREAD_SHEET_ID)
    values_list = sheet.sheet1.get_all_values()
    columns = values_list[0]
    rows = values_list[1:]
    gsheet_data = [dict(zip(columns, row)) for row in rows]
    #print(f"GSheet Data: {gsheet_data}")
    return gsheet_data

def combined_data():
    gsheet_data = get_gsheet_data()
    s3_image = generate_presigned_url()
    for obj in gsheet_data:
        for item in s3_image:
            if obj['URL'] == item['URL']:
                obj['Temp URL'] = item['Temp URL']
                break
    print(f"Combined data: {gsheet_data}")
    return gsheet_data

# Routes
@app.route("/theholytrinity")
def marketplace():
    data = combined_data()
    return render_template("marketplace.html", data=data)

@app.route("/profile/reference/<string:reference_id>")
def watch_profile(reference_id):
    print('Reference id:', reference_id)
    data = combined_data()
    #print(f"Combined data: {data}")
    print("\n")
    line_item = []
    for obj in data:
        if obj['Reference'] == reference_id:
            line_item.append(obj)
            print(f"Watch profile data: {line_item }")
            session['watch_id'] = line_item
            break
    return render_template("watch_profile.html", data=line_item)

@app.route("/create-checkout-session/<string:reference_id>")
def checkout(reference_id):
    item = session['watch_id']
    return render_template("checkout.html", data=item)

@app.route('/create-checkout-session/<string:reference_id>/checkout', methods=['POST'])
def create_checkout_session(reference_id):
    #print(f"Session data: {session['watch_id']}")
    item = session['watch_id']
    print(f"check out session data: {item}")
    price = ''
    item_name = ''
    reference = ''
    LOCAL_DOMAIN = ''

    for obj in item:
        item_name = obj['Name']
        price = obj['Price']
        reference = obj['Reference']

    price_str_removed = price.replace('$', '').replace(',', '')
    price_float = float(price_str_removed)
    price = int(price_float * 100)

    try:
        print(f"Price: {type(price)}")
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[
                {
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': item_name,
                        },
                        'unit_amount': price,
                    }
                }
            ],
            mode='payment',
            success_url = LOCAL_DOMAIN + '/success',
            cancel_url = LOCAL_DOMAIN + '/cancel',
        )
    except Exception as e:
        return str(e)

    return redirect(checkout_session.url, code=303)

@app.route("/success")
def checkout_success():
    return render_template("success.html")

@app.route("/cancel")
def checkout_cancel():
    return render_template("cancel.html")