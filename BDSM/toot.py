#!/usr/bin/env python3

from mastodon import Mastodon
from tenacity import *
from BDSM import db
from BDSM.models import Toot, Tag, Media, Emoji, Poll, Settings
import sys
import dateutil.parser



def app_register(url):
    print("Registering app")
    Mastodon.create_app(
        'pyBDSM',
        api_base_url = url,
        to_file = 'data/pyBDSM_clientcred.secret',
        scopes=["read"]
    )


def app_login(url):
    mastodon = Mastodon(
        client_id='data/pyBDSM_clientcred.secret',
        access_token='data/user.secret',
        api_base_url=url
    )

    try:
        user = mastodon.account_verify_credentials()
    except Exception as e:
        if "access token was revoked" in str(e):
            print("revoked token")
            sys.exit(0)
        elif "Name or service not known" in str(e):
            print("Error: the instance name is either misspelled or offline",
                file=sys.stderr)
        else:
            print(e, file=sys.stderr)
        # exit in either case
        sys.exit(1)

    return mastodon, user


def get_context(url, toot_id):
    mastodon, _ = app_login(url)
    settings = Settings.query.first()
    acct = settings.account
    context = mastodon.status_context(toot_id)
    statuses = []
    statuses= context['ancestors'] + context['descendants']
    toot_process(statuses, acct)

    db.session.commit()


def toot_process(statuses, my_acct, duplicates_counter=0):
    for status in statuses:
        is_reblog = False
        if status['reblog'] != None:
            if my_acct == status['reblog']['account']['acct']:
                reblog_myself = True
            else:
                reblog_myself = False

            is_reblog = True

            reblog_id = status['reblog']['id']
            id = status['id']
            created_at = status['created_at']

            toot = Toot(id=id, created_at=created_at, reblog_myself=reblog_myself, reblog_id=reblog_id)
            db.session.merge(toot)
            # cur.execute('''INSERT OR REPLACE INTO TOOT (id,created_at,reblog_myself,reblog_id) \
            #     VALUES (?,?,?,?)''',(id, created_at, reblog_myself, reblog_id))

            if reblog_myself:
                continue

            status = status['reblog']

        id = status['id']

        acct = status['account']['acct']
        url = status['url']
        created_at = status['created_at']

        if 'edited_at' in status:
            edited_at = status['edited_at']
            if isinstance(edited_at, str):
                edited_at = dateutil.parser.parse(status['edited_at'])
        else:
            edited_at = None

        in_reply_to_id = status['in_reply_to_id']
        in_reply_to_account_id = status['in_reply_to_account_id']
        content = status['content']

        if status['media_attachments'] != []:
            media_list = ""
            for media_dict in status['media_attachments']:
                media_list += str(media_dict['id']) + ","

                media = Media(id=media_dict['id'], type=media_dict['type'], url=media_dict['url'],
                                remote_url=media_dict['remote_url'], description=media_dict['description'])
                db.session.merge(media)
                # cur.execute('''INSERT OR REPLACE INTO MEDIA (id,type,url,remote_url,description) \
                #     VALUES (?,?,?,?,?)''',(media_dict['id'], media_dict['type'], media_dict['url'], \
                #         media_dict['remote_url'], media_dict['description']))
        else:
            media_list = ""

        spoiler_text = status['spoiler_text']

        if status['poll'] != None:
            poll_dict = status['poll']
            poll_id = poll_dict['id']
            expires_at = poll_dict['expires_at']
            options = str(poll_dict['options'])

            poll = Poll(id=poll_dict['id'], expires_at=expires_at, multiple=poll_dict['multiple'], \
                    votes_count=poll_dict['votes_count'], options=options)
            db.session.merge(poll)
            # cur.execute('''INSERT OR REPLACE INTO POLL (id,expires_at,multiple,votes_count,options) \
            #     VALUES (?,?,?,?,?)''',(poll_dict['id'], expires_at, poll_dict['multiple'], \
            #         poll_dict['votes_count'], options))
        else:
            poll_id = None

        if status['emojis'] != []:
            emoji_list = ""

            for emoji in status['emojis']:
                shortcode = emoji['shortcode']
                emoji_list += shortcode + ","
                counter = ':' + shortcode + ':'
                count = content.count(counter)

                if not is_reblog:
                    data=Emoji.query.filter_by(shortcode=shortcode, acct=acct).first()
                    if data == None:
                        emoji_data = Emoji(shortcode=shortcode,
                                        acct=acct,
                                        url=emoji['url'],
                                        static_url=emoji['static_url'],
                                        count=count)
                        db.session.merge(emoji_data)
                        # cur.execute('''INSERT INTO EMOJI (shortcode,url,static_url,count) \
                        #     VALUES (?,?,?,?)''', (shortcode, emoji['url'], emoji['static_url'], count))
                    else:
                        if data.count == None:
                            data.count = count
                        else:
                            data.count += count
                        # cur.execute("UPDATE EMOJI SET count = ? WHERE shortcode = ?",(count, shortcode))
                else:
                    emoji_data = Emoji(shortcode=shortcode,
                                    acct=acct,
                                    url=emoji['url'],
                                    static_url=emoji['static_url'])

                    db.session.merge(emoji_data)
        else:
            emoji_list = ""

        if status['tags'] != []:
            for tag in status['tags']:
                tag_data = Tag(id=id, name=tag['name'])
                db.session.merge(tag_data)
                # cur.execute('''INSERT OR REPLACE INTO TAG (id,name) \
                #     VALUES (?,?)''',(id, tag['name']))

        visibility = status['visibility']
        reblogged = status['reblogged']
        favourited = status['favourited']
        bookmarked = status['bookmarked']
        sensitive = status['sensitive']
        replies_count = status['replies_count']
        reblogs_count = status['reblogs_count']
        favourites_count = status['favourites_count']
        language = status['language']

        table = Toot()

        table.id=id
        table.acct = acct
        table.url=url
        table.created_at=created_at
        table.edited_at=edited_at
        table.in_reply_to_id=in_reply_to_id
        table.in_reply_to_account_id=in_reply_to_account_id
        table.content=content
        table.media_list=media_list
        table.spoiler_text=spoiler_text
        table.poll_id=poll_id
        table.emoji_list=emoji_list
        table.visibility=visibility
        table.reblogged=reblogged
        table.favourited=favourited
        table.bookmarked=bookmarked
        table.sensitive=sensitive
        table.replies_count=replies_count
        table.reblogs_count=reblogs_count
        table.favourites_count=favourites_count
        table.language=language

        if Toot.query.get(id) != None:
            duplicates_counter += 1

        db.session.merge(table)
        # sql = f'''INSERT OR REPLACE INTO {table} (id,url,created_at,edited_at,in_reply_to_id,in_reply_to_account_id,content,\
        #     media_list,spoiler_text,poll_id,emoji_list,visibility,reblogged,favourited,bookmarked,sensitive,reblogs_count,\
        #         favourites_count,language) \
        #             VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)'''
        # cur.execute(sql,(id,url,created_at,edited_at,in_reply_to_id,in_reply_to_account_id,content,media_list,spoiler_text,\
        #     poll_id,emoji_list,visibility,reblogged,favourited,bookmarked,sensitive,reblogs_count,favourites_count,language))
    return duplicates_counter


def archive_toot(url, archive_args):
    mastodon, user = app_login(url)
    acct = mastodon.me().acct
    skip_duplicates = False

    @retry(stop=stop_after_attempt(5))
    def fetch_next_statuses(statuses ):
        return mastodon.fetch_next(statuses)

    def archive(statuses, skip_duplicates=True):
        happy_counter = 20
        duplicates_counter = 0
        while(True):
            duplicates_counter = toot_process(statuses, acct)
            db.session.commit()
            print(str(happy_counter) + ' / '  + statuses_count)
            happy_counter += 20

            if duplicates_counter >= 10 and skip_duplicates:
                print("检测到重复嘟文达到十次，取消存档……")
                break

            statuses = fetch_next_statuses(statuses )
            if statuses == None:
                break

    if 'duplicate' in archive_args:
        skip_duplicates = True

    if 'statuses' in archive_args:
        statuses_count = str(mastodon.me().statuses_count)
        statuses = mastodon.account_statuses(user["id"], limit=20)
        archive(statuses, skip_duplicates=skip_duplicates)

    if 'favourites' in archive_args:
        statuses_count = '???'
        statuses = mastodon.favourites()
        archive(statuses, skip_duplicates=skip_duplicates)

    if 'bookmarks' in archive_args:
        statuses_count = '???'
        statuses = mastodon.bookmarks()
        archive(statuses, skip_duplicates=skip_duplicates)
