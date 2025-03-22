from app import app
from models import db, User, Admin


with app.app_context():
   print(Admin.query.all())
   
