from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

    email = db.Column(db.String(150), unique=True, nullable=True)
    name = db.Column(db.String(150), nullable=True)
    unit_number = db.Column(db.String(50), nullable=True)  # now nullable
    role = db.Column(db.String(50), nullable=False, default='Pending')  # default role
    phone_number = db.Column(db.String(20), nullable=True)  # new field

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == 'admin'

    @property
    def is_board(self):
        return self.role == 'board'

    @property
    def is_owner(self):
        return self.role == 'owner'

    @property
    def is_renter(self):
        return self.role == 'renter'

    @property
    def is_maintenance(self):
        return self.role == 'maintenance'

class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    notes = db.Column(db.Text)
    filesize = db.Column(db.Integer)
    mimetype = db.Column(db.String(120))  # ✅ for previews
    archived = db.Column(db.Boolean, default=False)  # ✅ soft delete
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    uploader_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    uploader = db.relationship('User', backref='documents')


class DownloadLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey('document.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    document = db.relationship('Document', backref='downloads')
    user = db.relationship('User', backref='downloads')


    


