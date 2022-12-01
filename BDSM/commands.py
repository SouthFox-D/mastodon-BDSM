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
def renderfile():
    """render toot"""
    from BDSM.models import Toot
    from BDSM.views import process_toot
    from jinja2 import Environment, FileSystemLoader

    head = '''<!Doctype html>
    <html>
    <head>
        <style>
            body {
                margin: auto !important;
                padding: 5px;
                max-width: 580px;
                font-size: 14px;
                font-family: Helvetica, Arial, sans-serif;
            }
            .toot {
                padding-top: 10px;
                padding-bottom: 10px;
            }
            .status {
                border: 1px solid #393f4f;
            }
            .toot-media{
                width: 100%;
            }
            .meta .time {
                float: right;
                text-decoration: underline;
                color: #606984;
            }
            .emojione {
                width: 20px;
                height: 20px;
                margin: -3px 0 0;
            }
            .emojione:hover {
                z-index: 11;
                /* Scale up 2.3 times */
                transform: scale(2.3);
                /* shadows around image edges */
                filter: drop-shadow(0 0 1px #282c37);
            }
            .icon-bar {
                display: block ruby;
            }
            .icon-bar span {
                padding-right: 10px;
            }

        </style>
    </head>
    </body>
    '''
    def render_toot(toot_id):
        _toot = []
        toot = Toot.query.get(toot_id)

        if toot == None:
            return "None"

        _toot.append(toot)
        _toot = process_toot(_toot)
        env = Environment(loader=FileSystemLoader("./BDSM/templates"))
        jinja_template = env.get_template("toot.html")
        template_string = jinja_template.render(toots=_toot)
        return template_string

    def _render(input_file):
        env = Environment(loader=FileSystemLoader("./"))
        jinja_template = env.get_template(input_file)
        jinja_template.globals.update(render_toot=render_toot)
        template_string = jinja_template.render()

        with open('./output.html', 'w') as f:
            f.write(head + template_string + '</body></html>')

    _render("input.txt")
    print("Done?")

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
