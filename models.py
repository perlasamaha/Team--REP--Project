"""Database models. The only data your app stores: user accounts and favorites.
You may add fields to Favorite to match your topic (e.g. a price, a year)."""
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    favorites = db.relationship("Favorite", backref="user",
                                cascade="all, delete-orphan")
    watchlist = db.relationship("Watchlist", backref="user",
                                cascade="all, delete-orphan")                            
    reports = db.relationship("HazardReport", backref="user",
                              cascade="all, delete-orphan")
    notes = db.relationship("Note", backref="user",
                            cascade="all, delete-orphan")

class Favorite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    item_id = db.Column(db.String(50), nullable=False)     # the API's id for the item
    item_title = db.Column(db.String(255))
    item_image = db.Column(db.String(500))
    __table_args__ = (db.UniqueConstraint("user_id", "item_id",
                                          name="uniq_user_item"),)

class Road(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    osm_id = db.Column(db.BigInteger, nullable=False)
    element_type = db.Column(db.String(10), nullable=False)   # "way"
    name = db.Column(db.String(255))                          # may be empty
    watchlist_entries = db.relationship("Watchlist", backref="road",
                                        cascade="all, delete-orphan")
    __table_args__ = (db.UniqueConstraint("osm_id", "element_type",
                                          name="uniq_osm_element"),)


class Watchlist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    road_id = db.Column(db.Integer, db.ForeignKey("road.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    __table_args__ = (db.UniqueConstraint("user_id", "road_id",
                                          name="uniq_user_road"),)
                                          
class HazardReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    road_id = db.Column(db.Integer, db.ForeignKey("road.id"), nullable=True)
    region = db.Column(db.String(50), nullable=False)
    type = db.Column(db.String(30), nullable=False, default="pothole")
    description = db.Column(db.Text, nullable=False)
    severity = db.Column(db.String(10), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="unverified")
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow,
                           onupdate=datetime.utcnow)
    road = db.relationship("Road", backref="reports")
    notes = db.relationship("Note", backref="report",
                            cascade="all, delete-orphan")
    images = db.relationship("ReportImage", backref="report",
                             cascade="all, delete-orphan")                        


class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.Integer, db.ForeignKey("hazard_report.id"),
                          nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow,
                           onupdate=datetime.utcnow)                                          

class ReportImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.Integer, db.ForeignKey("hazard_report.id"),
                          nullable=False)
    image_url = db.Column(db.String(500), nullable=False)
    file_id = db.Column(db.String(100), nullable=False)
    uploaded_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
