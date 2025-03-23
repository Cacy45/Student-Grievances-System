from app import app
from models import db, User, Admin


with app.app_context():
   new_admin = Admin(user_id=2, dept_id=1)
   db.session.add(new_admin)
   db.session.commit()
   print("Admin added successfully!")



   

   
