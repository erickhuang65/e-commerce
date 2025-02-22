from flask import Flask
import os
app = Flask(__name__)

app.secret_key = os.environ.get("APP_SECRET_KEY")
app.DB_PASSWORD = os.environ.get("DB_PASSWORD")
app.GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")