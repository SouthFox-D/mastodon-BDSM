#!/usr/bin/env python3
import os
import pytz

from flask import render_template, request, url_for, redirect, flash
from flask_sqlalchemy import Pagination
from BDSM import app, db
from BDSM.models import Media, Settings, Toot, Emoji, Reblog
from BDSM.toot import app_register, archive_toot
from mastodon import Mastodon
from types import SimpleNamespace
from datetime import timezone

# @app.context_processor
# def inject_setting():
#     settings = Settings.query.first()
#     return settings.__dict__

@app.route('/', methods=['GET', 'POST'])
def index():
    settings = Settings.query.first()
    if settings == None:
        return redirect(url_for('settings'))
    else:
        page = request.args.get('page', 1, type=int)
        toots_ = Toot.query.order_by(Toot.created_at.desc()).paginate(page, per_page=50)
        toots = process_toot(toots_)
        path=SimpleNamespace()
        path.path = "index"
        path.args = {}

        return render_template('view.html', toots=toots, pagination=toots_, path=path)

@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        query = request.form['query']
        return redirect(url_for('search',query=query))

    query = request.args.get('query', "", type=str)
    page = request.args.get('page', 1, type=int)
    toots_ = Toot.query.order_by(Toot.created_at.desc()).filter(Toot.content.like("%"+query+"%")).paginate(page, per_page=50)
    toots = process_toot(toots_)
    path=SimpleNamespace()
    # Rule: /serch
    path.path = str(request.url_rule)[1:] #FIXME
    path.args = {}
    path.args["query"] = query
    return render_template('view.html', toots=toots, pagination=toots_, path=path)


@app.route('/context/<int:toot_id>', methods=['GET', 'POST'])
def context(toot_id):
    def get_reply(reply_id):
        toots = Toot.query.order_by(Toot.created_at.desc()).filter_by(in_reply_to_id=reply_id).all()
        toots = process_toot(toots)

        for i in toots:
            if i.in_reply_to_id != None:
                i.reply = get_reply(i.id)

        return toots

    toots = []
    toots.append(Toot.query.get_or_404(toot_id))
    toots = process_toot(toots)
    toots[0].reply = get_reply(toot_id)

    in_reply_to_id = toots[0].in_reply_to_id
    while(in_reply_to_id != None):
        toot = []
        toot_ = Toot.query.get(toots[0].in_reply_to_id)
        if toot_ == None:
            break

        toot.append(toot_)
        toot = process_toot(toot)
        toots.insert(0,toot[0])
        in_reply_to_id = toot[0].in_reply_to_id

    return render_template('view.html', toots=toots,)

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if request.method == 'POST':
        account = request.form['account']
        timezone = request.form['timezone']

        if not account or len(account) > 30:
            flash('无效输入')
            return redirect(url_for('settings'))

        settings = Settings.query.first()

        if settings == None:
            settings = Settings(account=account, timezone=timezone)
            db.session.add(settings)
        else:
            settings.account = account
            settings.timezone = timezone

        db.session.commit()
        flash('设置已修改')
        return redirect(url_for('settings'))

    settings = Settings.query.first()
    app_init = os.path.isfile('pyBDSM_clientcred.secret') and os.path.isfile('user.secret')
    if settings == None:
        flash('请输入相关设置！')

    return render_template('settings.html',settings=settings, app_init=app_init)

@app.route('/register', methods=['GET', 'POST'])
def register():
    settings = Settings.query.first()
    if settings == None:
        flash('请先输入用户名！')
        return redirect(url_for('settings'))
    else:
        account = settings.account[1:]
        username, domain = account.split("@")
        url = "https://" + domain

        if request.method == 'POST':
            token = request.form['token'].rstrip()
            mastodon = Mastodon(client_id='pyBDSM_clientcred.secret', api_base_url=url)
            mastodon.log_in(code=token, to_file='user.secret', scopes=['read'])

            if os.path.isfile('user.secret'):
                flash('应用已授权！')
                return redirect(url_for('settings'))

        if not os.path.isfile('pyBDSM_clientcred.secret'):
            app_register(url)
        if not os.path.isfile('user.secret'):
            mastodon = Mastodon(client_id='pyBDSM_clientcred.secret', api_base_url=url)
            url = mastodon.auth_request_url(client_id='pyBDSM_clientcred.secret', scopes=['read'])
            return render_template('register.html',url=url)

        flash('已授权过！')
        return redirect(url_for('settings'))

@app.route('/archive', methods=['GET', 'POST'])
def archive():
    settings = Settings.query.first()
    if settings == None:
        return redirect(url_for('settings'))
    elif len(Toot.query.all()) > 0:
        flash('现暂不支持重复存档！') #TODO
        return redirect(url_for('index'))
    else:
        account = settings.account[1:]
        username, domain = account.split("@")
        url = "https://" + domain

        archive_toot(url)

    flash('存档完成……大概！')
    return redirect(url_for('index'))

def process_toot(toots_):
    toots = []
    settings = Settings.query.first()
    user_timezone = pytz.timezone(settings.timezone)
    fmt = '%Y-%m-%d %H:%M:%S'

    if hasattr(toots_, 'items'):
        toots_ = toots_.items

    for toot_ in toots_:
        toot = SimpleNamespace(**toot_.__dict__)

        toot.created_at = toot.created_at.replace(tzinfo=timezone.utc)
        toot.created_at = toot.created_at.astimezone(user_timezone).strftime(fmt)

        if toot.reblog_id != None:
            if toot.reblog_myself:
                toot = Toot.query.get(toot.reblog_id)
                toot = SimpleNamespace(**toot.__dict__)
                toot.is_reblog = True
            else:
                toot = Reblog.query.get(toot.reblog_id)
                toot = SimpleNamespace(**toot.__dict__)
                toot.is_reblog = True

        if toot.media_list != "":
            toot.medias = []
            #media_list "1111,2222,333,"
            media_list = toot.media_list[:-1].split(",")

            for media_id in media_list:
                media = Media.query.get(int(media_id))
                if media != None:
                    toot.medias.append(media)

        if toot.emoji_list != "":
            toot.emojis = []
            #emoji_list "blobfoxaaa,blobcatwww,fox_think,"
            emoji_list = toot.emoji_list[:-1].split(",")

            for emoji_shortcode in emoji_list:
                emoji = Emoji.query.filter_by(shortcode=emoji_shortcode, acct=toot.acct).first()

                if emoji != None:
                    emoji_shortcode = ':' + emoji_shortcode + ':'
                    emoji_url = emoji.url
                    emoji_html = f'''
                    <img class="emojione custom-emoji" alt="{emoji_shortcode}" title="{emoji_shortcode}" src="{emoji.url}" >
                    '''
                    toot.content = toot.content.replace(emoji_shortcode, emoji_html)

        toots.append(toot)
    return toots
