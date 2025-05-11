import os
import logging
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, flash, request, abort, session, g
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import uuid

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Setup database base class
class Base(DeclarativeBase):
    pass

# Initialize SQLAlchemy
db = SQLAlchemy(model_class=Base)

# Create the Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure database
database_url = os.environ.get("DATABASE_URL")
# Ensure database URL starts with postgresql:// not postgres://
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Configure file uploads
app.config["UPLOAD_FOLDER"] = os.path.join(app.root_path, "static/uploads")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max upload
app.config["ALLOWED_EXTENSIONS"] = {"png", "jpg", "jpeg", "gif"}

# Create upload directory if it doesn't exist
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# Initialize the database
db.init_app(app)

# Import models after db initialization to avoid circular imports
from models import Admin, Giveaway, Entry
from forms import GiveawayEntryForm, AdminLoginForm, GiveawayForm
from helpers import admin_required, allowed_file

# Add current datetime to all templates
@app.before_request
def before_request():
    g.now = datetime.now()

# Create all database tables
with app.app_context():
    db.create_all()
    
    # Remove old admin user if exists
    old_admin = Admin.query.filter_by(username="admin").first()
    if old_admin:
        db.session.delete(old_admin)
        db.session.commit()
        logging.info("Removed old admin user")
    
    # Create new admin user if it doesn't exist
    if not Admin.query.filter_by(username="yameenking99").first():
        admin = Admin(
            username="yameenking99",
            password_hash=generate_password_hash("9928288283737838393937647484848")
        )
        db.session.add(admin)
        db.session.commit()
        logging.info("Created admin user with custom credentials")

# Routes
@app.route("/")
def index():
    active_giveaways = Giveaway.query.filter(Giveaway.end_date >= datetime.now()).order_by(Giveaway.end_date).all()
    past_giveaways = Giveaway.query.filter(Giveaway.end_date < datetime.now()).order_by(Giveaway.end_date.desc()).limit(5).all()
    return render_template("index.html", active_giveaways=active_giveaways, past_giveaways=past_giveaways)

@app.route("/giveaway/<int:giveaway_id>", methods=["GET", "POST"])
def giveaway_detail(giveaway_id):
    giveaway = Giveaway.query.get_or_404(giveaway_id)
    form = GiveawayEntryForm()
    
    if form.validate_on_submit():
        # Check if giveaway is still active
        if giveaway.end_date < datetime.now():
            flash("This giveaway has ended.", "danger")
            return redirect(url_for("giveaway_detail", giveaway_id=giveaway_id))
        
        # Check if email already entered this giveaway
        existing_entry = Entry.query.filter_by(
            giveaway_id=giveaway_id, 
            email=form.email.data
        ).first()
        
        if existing_entry:
            flash("You have already entered this giveaway.", "warning")
            return redirect(url_for("giveaway_detail", giveaway_id=giveaway_id))
        
        # Create new entry
        entry = Entry(
            giveaway_id=giveaway_id,
            name=form.name.data,
            email=form.email.data,
            phone=form.phone.data
        )
        db.session.add(entry)
        db.session.commit()
        
        flash("You have successfully entered the giveaway!", "success")
        return redirect(url_for("entry_confirmation", entry_id=entry.id))
    
    return render_template("giveaway.html", giveaway=giveaway, form=form)

@app.route("/confirmation/<int:entry_id>")
def entry_confirmation(entry_id):
    entry = Entry.query.get_or_404(entry_id)
    giveaway = Giveaway.query.get_or_404(entry.giveaway_id)
    return render_template("entry_confirmation.html", entry=entry, giveaway=giveaway)

# Admin routes
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if session.get("admin_logged_in"):
        return redirect(url_for("admin_dashboard"))
    
    form = AdminLoginForm()
    if form.validate_on_submit():
        admin = Admin.query.filter_by(username=form.username.data).first()
        if admin and check_password_hash(admin.password_hash, form.password.data):
            session["admin_logged_in"] = True
            session["admin_id"] = admin.id
            flash("Login successful!", "success")
            return redirect(url_for("admin_dashboard"))
        else:
            flash("Invalid username or password", "danger")
    
    return render_template("admin/login.html", form=form)

@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_logged_in", None)
    session.pop("admin_id", None)
    flash("You have been logged out.", "success")
    return redirect(url_for("index"))

@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    active_giveaways = Giveaway.query.filter(Giveaway.end_date >= datetime.now()).order_by(Giveaway.end_date).all()
    past_giveaways = Giveaway.query.filter(Giveaway.end_date < datetime.now()).order_by(Giveaway.end_date.desc()).all()
    return render_template("admin/dashboard.html", active_giveaways=active_giveaways, past_giveaways=past_giveaways)

@app.route("/admin/giveaway/add", methods=["GET", "POST"])
@admin_required
def add_giveaway():
    form = GiveawayForm()
    
    if form.validate_on_submit():
        # Handle image upload
        image_filename = None
        if form.image.data:
            image = form.image.data
            if image and allowed_file(image.filename):
                # Generate unique filename
                filename = secure_filename(image.filename)
                unique_filename = f"{uuid.uuid4().hex}_{filename}"
                image_path = os.path.join(app.config["UPLOAD_FOLDER"], unique_filename)
                image.save(image_path)
                image_filename = unique_filename
        
        # Create new giveaway
        giveaway = Giveaway(
            title=form.title.data,
            description=form.description.data,
            prize=form.prize.data,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            image=image_filename
        )
        db.session.add(giveaway)
        db.session.commit()
        
        flash("Giveaway created successfully!", "success")
        return redirect(url_for("admin_dashboard"))
    
    return render_template("admin/add_giveaway.html", form=form)

@app.route("/admin/giveaway/<int:giveaway_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_giveaway(giveaway_id):
    giveaway = Giveaway.query.get_or_404(giveaway_id)
    form = GiveawayForm(obj=giveaway)
    
    if form.validate_on_submit():
        # Handle image upload
        if form.image.data:
            image = form.image.data
            if image and allowed_file(image.filename):
                # Delete old image if it exists
                if giveaway.image:
                    old_image_path = os.path.join(app.config["UPLOAD_FOLDER"], giveaway.image)
                    if os.path.exists(old_image_path):
                        os.remove(old_image_path)
                
                # Generate unique filename
                filename = secure_filename(image.filename)
                unique_filename = f"{uuid.uuid4().hex}_{filename}"
                image_path = os.path.join(app.config["UPLOAD_FOLDER"], unique_filename)
                image.save(image_path)
                giveaway.image = unique_filename
        
        # Update giveaway details
        giveaway.title = form.title.data
        giveaway.description = form.description.data
        giveaway.prize = form.prize.data
        giveaway.start_date = form.start_date.data
        giveaway.end_date = form.end_date.data
        
        db.session.commit()
        flash("Giveaway updated successfully!", "success")
        return redirect(url_for("admin_dashboard"))
    
    return render_template("admin/add_giveaway.html", form=form, giveaway=giveaway)

@app.route("/admin/giveaway/<int:giveaway_id>/delete", methods=["POST"])
@admin_required
def delete_giveaway(giveaway_id):
    giveaway = Giveaway.query.get_or_404(giveaway_id)
    
    # Delete associated image if it exists
    if giveaway.image:
        image_path = os.path.join(app.config["UPLOAD_FOLDER"], giveaway.image)
        if os.path.exists(image_path):
            os.remove(image_path)
    
    # Delete all entries for this giveaway
    Entry.query.filter_by(giveaway_id=giveaway_id).delete()
    
    # Delete the giveaway
    db.session.delete(giveaway)
    db.session.commit()
    
    flash("Giveaway deleted successfully!", "success")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/giveaway/<int:giveaway_id>/entries")
@admin_required
def giveaway_entries(giveaway_id):
    giveaway = Giveaway.query.get_or_404(giveaway_id)
    entries = Entry.query.filter_by(giveaway_id=giveaway_id).order_by(Entry.created_at.desc()).all()
    return render_template("admin/entries.html", giveaway=giveaway, entries=entries)

@app.route("/admin/entry/<int:entry_id>/delete", methods=["POST"])
@admin_required
def delete_entry(entry_id):
    entry = Entry.query.get_or_404(entry_id)
    giveaway_id = entry.giveaway_id
    
    db.session.delete(entry)
    db.session.commit()
    
    flash("Entry deleted successfully!", "success")
    return redirect(url_for("giveaway_entries", giveaway_id=giveaway_id))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
