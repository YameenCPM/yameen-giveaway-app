from datetime import datetime
from app import db

class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Giveaway(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    prize = db.Column(db.String(200), nullable=False)
    image = db.Column(db.String(255))
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship with entries
    entries = db.relationship('Entry', backref='giveaway', lazy=True, cascade="all, delete-orphan")
    
    @property
    def is_active(self):
        """Check if the giveaway is currently active."""
        now = datetime.utcnow()
        return self.start_date <= now <= self.end_date
    
    @property
    def entry_count(self):
        """Get the number of entries for this giveaway."""
        return len(self.entries)
    
    @property
    def image_url(self):
        """Get the URL for the giveaway image."""
        if self.image:
            return f"/static/uploads/{self.image}"
        return "/static/img/default-giveaway.svg"

class Entry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    giveaway_id = db.Column(db.Integer, db.ForeignKey('giveaway.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Entry {self.id} - {self.name}>"
