#!/usr/bin/env python3
import click

from BDSM import app, db
from BDSM.models import Settings, Toot
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
def analysis():
    """Analysis current Year"""
    from BDSM.models import Toot
    from sqlalchemy.sql import extract
    from sqlalchemy import func
    from sqlalchemy import desc
    from . import db
    from wordcloud import WordCloud
    from PIL import Image
    import numpy as np
    import jieba
    import re

    year = input(" 请输入要分析的年份。")
    settings = Settings.query.first()

    year_toots = Toot.query.filter(extract('year', Toot.created_at) == int(year))
    print(f"{year} 总计嘟文" + str(len(year_toots.all())))
    print(f"{year} 年发言最多天数排名" +
        str(db.session.query(func.strftime("%Y-%m-%d", Toot.created_at
                                ).label('date'),func.count('date')
                                ).filter(extract('year', Toot.created_at) == int(year)
                                ).filter(Toot.acct==settings.account
                                ).group_by('date'
                                ).order_by(desc(func.count('date'))
                                ).all()[:3])
    )

    print(f"{year} 年互动最多帐号排名" +
        str(db.session.query(Toot.acct.label('count'),func.count('count')
                                ).filter(extract('year', Toot.created_at) == int(year)
                                ).filter(Toot.acct!=settings.account
                                ).group_by('count'
                                ).order_by(desc(func.count('count'))
                                ).all()[:3])
    )

    toots_counter = 0
    public_counter = 0
    toots_content = ''

    html_pattern = re.compile(r'<[^>]+>',re.S)
    url_pattern = re.compile(r'https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()!@:%_\+.~#?&\/\/=]*)',re.S)
    emoji_pattern = re.compile(r':+?[a-zA-Z0-9_]+:',re.S)
    at_pattern = re.compile(r'@+?[a-zA-Z0-9\._]+ ',re.S)
    mask = np.array(Image.open("misc/mask.png"))

    for i in year_toots:
        if i.content != None:
            toot_content = html_pattern.sub('', i.content)
            toot_content = url_pattern.sub('', toot_content)
            toot_content = emoji_pattern.sub('', toot_content)
            toot_content = at_pattern.sub('', toot_content)
            toots_content += toot_content

            toots_counter += 1
            if i.visibility == 'public':
                public_counter += 1

    print(f"{year} 实际有内容嘟文数量：" + str(toots_counter))
    print(f"{year} 公开嘟文数量" + str(public_counter))

    jieba.load_userdict(r'misc/user_dict.txt')
    wordlist = jieba.lcut(toots_content)
    space_list = ' '.join(wordlist)
    stopwords = set()
    content = [line.strip() for line in open('misc/stopwords.txt','r',
                                             encoding='utf-8').readlines()]
    stopwords.update(content)

    wc = WordCloud(width=1400, height=2200,
                    background_color='white',
                    mask=mask,
                    stopwords=stopwords,
                    mode='RGB',
                    max_words=500,
                    max_font_size=150,
                    #relative_scaling=0.6,
                    font_path="/usr/share/fonts/noto-cjk/NotoSerifCJK-Regular.ttc",
                    random_state=50,
                    scale=2
                ).generate(space_list)
    wc.to_file("output.png")
    print(" 词图统计已生成在根目录，名字为 output.png")

@app.cli.command()
def renderfile():
    """render toot"""
    from BDSM.models import Toot
    from BDSM.views import process_toot
    from jinja2 import Environment, FileSystemLoader

    head = '''<!Doctype html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {
                margin: auto !important;
                padding: 5px;
                max-width: 580px;
                font-size: 14px;
                font-family: Helvetica, Arial, sans-serif;
            }
            @media screen and (max-width:720px){
                body {
                    margin: auto !important;
                    padding: 5px;
                    max-width: 580px;
                    font-size: 14px;
                    font-family: Helvetica, Arial, sans-serif;
                }
            }
            .toot {
                padding-top: 10px;
                padding-bottom: 10px;
            }
            .status {
                border: 1px solid #393f4f;
            }
            .toot-media {
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
    domain = settings.domain
    url = "https://" + domain
    mastodon, _ = app_login(url)
    acct = mastodon.me().acct

    toots = Toot.query.filter(Toot.in_reply_to_id.isnot(None)).all()
    toots_id = []
    for i in toots:
        if (Toot.query.get(i.in_reply_to_id) != None):
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
