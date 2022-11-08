#!/usr/bin/env python3
import click

from BDSM import app, db
from BDSM.models import Settings, Toot, Other
from BDSM.toot import app_login, toot_process
from mastodon import MastodonNotFoundError


@app.cli.command()
@click.option('--drop', is_flag=True, help='Create after drop.')
def initdb(drop):
    """Initialize the database."""
    if drop:
        db.drop_all()
    db.create_all()
    click.echo('Initialized database.')

@app.cli.command()
def graball():
    """Grab all toots context"""
    settings = Settings.query.first()
    account = settings.account[1:]
    username, domain = account.split("@")
    url = "https://" + domain
    mastodon, user = app_login(url)
    acct = mastodon.me().acct

    toots = Toot.query.filter(Toot.in_reply_to_id.isnot(None)).all()
    toots_id = []
    for i in toots:
        if (Toot.query.get(i.in_reply_to_id) != None
            or Other.query.get(i.in_reply_to_id) != None):
            continue
        #context api excluding itself
        toots_id.append(i.id)

    while(toots_id != []):
        toot_id = toots_id.pop(0)

        try:
            context = mastodon.status_context(toot_id)
        except MastodonNotFoundError:
            print('NotFound!')
            continue

        statuses = []
        statuses= context['ancestors'] + context['descendants']

        for i in statuses:
            if i['id'] in toots_id:
                toots_id.remove(i['id'])

        toot_process(statuses, acct)
        db.session.commit()

        print(len(toots_id))
