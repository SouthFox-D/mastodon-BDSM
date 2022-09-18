#!/usr/bin/env python3
import os

from flask import render_template, request, url_for, redirect, flash
from BDSM import app, db
from BDSM.models import Settings, Toot
from BDSM.toot import app_register, archive_toot
from mastodon import Mastodon

@app.route('/', methods=['GET', 'POST'])
def index():
    page = request.args.get('page', 1, type=int)
    toots_ = Toot.query.order_by(Toot.created_at.desc()).paginate(page, per_page=50)
    toots = []

    for toot in toots_.items:
        if toot.content == None:
            continue

        toots.append(toot)

    return render_template('view.html', toots=toots, pagination=toots_)

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
    if settings == None:
        flash('请输入用户名')
        return render_template('settings.html')

    app_init = os.path.isfile('pyBDSM_clientcred.secret') and os.path.isfile('user.secret')

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
