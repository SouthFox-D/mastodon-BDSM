#!/usr/bin/env python3

from mastodon import Mastodon
from BDSM import db
from BDSM.models import Reblog, Toot, Tag, Media, Emoji, Poll
import sys

def app_register(url):
    print("Registering app")
    Mastodon.create_app(
        'pyBDSM',
        api_base_url = url,
        to_file = 'pyBDSM_clientcred.secret',
        scopes=["read"]
    )

def archive_toot(url):
    mastodon = Mastodon(
        client_id='pyBDSM_clientcred.secret',
        access_token='user.secret',
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

    acct = mastodon.me().acct
    statuses_count = str(mastodon.me().statuses_count)

    statuses = mastodon.account_statuses(user["id"], limit=20)
    # xx = statuses['created_at'].astimezone(tz_cn)
    # pprint(xx.strftime("%m/%d/%Y, %H:%M:%S"))
    # pprint(statuses)

    happy_counter = 20

    while(True):
        for status in statuses:
            is_reblog = False
            if status['reblog'] != None:
                if acct == status['reblog']['account']['acct']:
                    reblog_myself = True
                else:
                    reblog_myself = False

                is_reblog = True

                reblog_id = status['reblog']['id']
                id = status['id']
                created_at = status['created_at']

                toot = Toot(id=id, created_at=created_at, reblog_myself=reblog_myself, reblog_id=reblog_id)
                db.session.add(toot)
                # cur.execute('''INSERT OR REPLACE INTO TOOT (id,created_at,reblog_myself,reblog_id) \
                #     VALUES (?,?,?,?)''',(id, created_at, reblog_myself, reblog_id))

                if reblog_myself:
                    continue

                status = status['reblog']

            id = status['id']
            acct = status['account']['acct']
            url = status['url']
            created_at = status['created_at']
            edited_at = status['edited_at'] if status['edited_at'] != None else None
            in_reply_to_id = status['in_reply_to_id']
            in_reply_to_account_id = status['in_reply_to_account_id']
            content = status['content']

            if status['media_attachments'] != []:
                media_list = ""
                for media_dict in status['media_attachments']:
                    media_list += str(media_dict['id']) + ","

                    media = Media(id=media_dict['id'], type=media_dict['type'], url=media_dict['url'],
                                  remote_url=media_dict['remote_url'], description=media_dict['description'])
                    db.session.add(media)
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
                db.session.add(poll)
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

                    data=Emoji.query.filter_by(shortcode=shortcode).first()
                    if data is None:
                        emoji_data = Emoji(shortcode=shortcode, url=emoji['url'], static_url=emoji['static_url'], count=count)
                        db.session.add(emoji_data)
                        # cur.execute('''INSERT INTO EMOJI (shortcode,url,static_url,count) \
                        #     VALUES (?,?,?,?)''', (shortcode, emoji['url'], emoji['static_url'], count))
                    else:
                        data.count += count
                        # cur.execute("UPDATE EMOJI SET count = ? WHERE shortcode = ?",(count, shortcode))
            else:
                emoji_list = ""

            if status['tags'] != []:
                for tag in status['tags']:
                    tag_data = Tag(id=id, name=tag['name'])
                    db.session.add(tag_data)
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

            table = Reblog() if is_reblog else Toot()
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


            db.session.add(table)
            # sql = f'''INSERT OR REPLACE INTO {table} (id,url,created_at,edited_at,in_reply_to_id,in_reply_to_account_id,content,\
            #     media_list,spoiler_text,poll_id,emoji_list,visibility,reblogged,favourited,bookmarked,sensitive,reblogs_count,\
            #         favourites_count,language) \
            #             VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)'''
            # cur.execute(sql,(id,url,created_at,edited_at,in_reply_to_id,in_reply_to_account_id,content,media_list,spoiler_text,\
            #     poll_id,emoji_list,visibility,reblogged,favourited,bookmarked,sensitive,reblogs_count,favourites_count,language))

        db.session.commit()
        print(str(happy_counter) + ' / '  + statuses_count)
        happy_counter += 20

        statuses = mastodon.fetch_next(statuses)
        # statuses = None
        if statuses == None:
            break
