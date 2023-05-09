#!/usr/bin/env python3
import os
import pytz
import json

from flask import render_template, request, url_for, redirect, flash, abort
from flask_sqlalchemy import Pagination
from sqlalchemy import or_
from BDSM import app, db
from BDSM.models import Media, Poll, Settings, Toot, Emoji
from BDSM.toot import app_login, app_register, archive_toot, get_context
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
        toots_ = Toot.query.order_by(Toot.created_at.desc()).filter(or_(Toot.acct==settings.account, Toot.reblog_id!=None)).paginate(page=page, per_page=50)
        toots = process_toot(toots_)
        path=SimpleNamespace()
        path.path = "index"
        path.args = {}

        return render_template('view.html', toots=toots, pagination=toots_, path=path)


@app.route('/favourited', methods=['GET', 'POST'])
def favourited():
    settings = Settings.query.first()
    if settings == None:
        return redirect(url_for('settings'))
    else:
        page = request.args.get('page', 1, type=int)
        toots_ = Toot.query.order_by(Toot.created_at.desc()).filter_by(favourited=True).paginate(page=page, per_page=50)
        toots = process_toot(toots_)
        path=SimpleNamespace()
        path.path = "favourited"
        path.args = {}

        return render_template('view.html', toots=toots, pagination=toots_, path=path)


@app.route('/bookmarked', methods=['GET', 'POST'])
def bookmarked():
    settings = Settings.query.first()
    if settings == None:
        return redirect(url_for('settings'))
    else:
        page = request.args.get('page', 1, type=int)
        toots_ = Toot.query.order_by(Toot.created_at.desc()).filter_by(bookmarked=True).paginate(page=page, per_page=50)
        toots = process_toot(toots_)
        path=SimpleNamespace()
        path.path = "bookmarked"
        path.args = {}

        return render_template('view.html', toots=toots, pagination=toots_, path=path)


@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        query = request.form['query']
        return redirect(url_for('search',query=query))

    query = request.args.get('query', "", type=str)
    page = request.args.get('page', 1, type=int)
    toots_ = Toot.query.order_by(Toot.created_at.desc()).filter(Toot.content.like("%"+query+"%")).paginate(
        page=page, per_page=50)
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

        for i in toots:
            if i.in_reply_to_id != None:
                i.reply = get_reply(i.id)

        return toots

    toots = []

    toot_ = Toot.query.get(toot_id)
    if toot_ == None:
        abort(404)

    toots.append(toot_)
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


@app.route('/grab/<int:toot_id>', methods=['GET', 'POST'])
def grab(toot_id):
    settings = Settings.query.first()
    domain = settings.domain
    url = "https://" + domain

    get_context(url, toot_id)
    flash('抓取完成……大概！')
    return redirect(url_for('context',toot_id=toot_id))


@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if request.method == 'POST':
        timezone = request.form['timezone']
        settings = Settings.query.first()
        if settings == None:
            domain = request.form['domain']

            if not domain or len(domain) > 50:
                flash('无效输入')
                return redirect(url_for('settings'))

            settings = Settings(domain=domain, timezone=timezone)
            db.session.add(settings)
        else:
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
        flash('请先输入站点地址！')
        return redirect(url_for('settings'))
    else:
        domain = settings.domain
        url = "https://" + domain

        mastodon, _ = app_login(url)
        account = mastodon.me().acct
        settings.account = account
        db.session.commit()

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
    if request.method == 'POST':
        archive_match = request.form.getlist("archive_match")
        domain = settings.domain
        url = "https://" + domain
        archive_toot(url, archive_match)

        flash('存档完成……大概！')
        return redirect(url_for('index'))

    if settings == None:
        return redirect(url_for('settings'))
    else:
        return render_template('archive.html')


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

        if toot.acct == settings.account:
            toot.is_myself = True
        else:
            toot.is_myself = False

        if toot.reblog_id != None:
            toot = Toot.query.get(toot.reblog_id)
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
                    # emoji_url = emoji.url
                    emoji_html = f'''
                    <img class="emojione custom-emoji" alt="{emoji_shortcode}" title="{emoji_shortcode}" src="{emoji.url}" >
                    '''
                    toot.content = toot.content.replace(emoji_shortcode, emoji_html)

        if toot.poll_id != None:
           poll = Poll.query.get(toot.poll_id)
           poll_options = json.loads(poll.options.replace("\'", "\""))
           poll_count = str(poll.votes_count)
           poll_content = '<strong>总票数： ' + poll_count + '</strong><br>'

           for i in poll_options:
               poll_content += i['title'] + " / " + str(i['votes_count']) + '<br>'

           toot.content += poll_content

        toots.append(toot)

    return toots
