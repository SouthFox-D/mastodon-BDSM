#!/usr/bin/env python3
from BDSM import db

class Toot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    acct = db.Column(db.Text)
    url = db.Column(db.Text)
    created_at = db.Column(db.DateTime)
    edited_at = db.Column(db.DateTime)
    in_reply_to_id = db.Column(db.Integer)
    in_reply_to_account_id = db.Column(db.Integer)
    reblog_myself = db.Column(db.Boolean)
    reblog_id = db.Column(db.Integer)
    content = db.Column(db.Text)
    media_list = db.Column(db.Text)
    emoji_list = db.Column(db.Text)
    spoiler_text = db.Column(db.Text)
    poll_id = db.Column(db.Integer)
    visibility  = db.Column(db.Text)
    reblogged  = db.Column(db.Boolean)
    favourited = db.Column(db.Boolean)
    bookmarked = db.Column(db.Boolean)
    sensitive = db.Column(db.Boolean)
    replies_count = db.Column(db.Integer)
    reblogs_count = db.Column(db.Integer)
    favourites_count = db.Column(db.Integer)
    language = db.Column(db.Text)

class Tag(db.Model):
    __table_args__ = {'sqlite_autoincrement': True}
    tag_id = db.Column(db.Integer, primary_key=True)
    id = db.Column(db.Integer)
    name = db.Column(db.Text)

class Emoji(db.Model):
    __table_args__ = {'sqlite_autoincrement': True}
    emoji_id = db.Column(db.Integer, primary_key=True)
    shortcode = db.Column(db.Text)
    acct = db.Column(db.Text)
    url = db.Column(db.Text)
    static_url = db.Column(db.Text)
    count = db.Column(db.Integer)

class Media(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.Text)
    url = db.Column(db.Text)
    remote_url = db.Column(db.Text)
    description = db.Column(db.Text)

class Poll(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    expires_at = db.Column(db.DateTime)
    multiple = db.Column(db.Boolean)
    votes_count = db.Column(db.Integer)
    options = db.Column(db.Text)

class Settings(db.Model):
    domain = db.Column(db.Text, primary_key=True)
    account = db.Column(db.Text)
    timezone = db.Column(db.Text)
    setup = db.Column(db.Boolean)
