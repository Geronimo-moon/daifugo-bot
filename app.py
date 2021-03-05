# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import errno
import os
import sys
from argparse import ArgumentParser
import random
import json

from flask import Flask, request, abort, send_from_directory
from werkzeug.middleware.proxy_fix import ProxyFix

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    LineBotApiError, InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    SourceUser, SourceGroup, SourceRoom,
    TemplateSendMessage, MessageAction,
    ButtonsTemplate, ImageCarouselTemplate, ImageCarouselColumn,
    PostbackAction, CarouselTemplate, CarouselColumn, PostbackEvent)

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_host=1, x_proto=1)

channel_secret = os.getenv('LINE_CHANNEL_SECRET', None)
channel_access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', None)
if channel_secret is None or channel_access_token is None:
    print('Specify LINE_CHANNEL_SECRET and LINE_CHANNEL_ACCESS_TOKEN as environment variables.')
    sys.exit(1)

line_bot_api = LineBotApi(channel_access_token)
handler = WebhookHandler(channel_secret)

static_tmp_path = os.path.join(os.path.dirname(__file__), 'static', 'tmp')

with open('gamedata.json', 'w') as f:
    gamedata = {'group':{}, 'room':{}, 'user':{'cards':{}}}
    json.dump(gamedata, f, ensure_ascii=False, indent=3)

def rand_ints_nodup(a, b):
        ns = []
        while len(ns) < b:
            n = random.randint(a, b)
            if not n in ns:
                ns.append(n)
        return ns

def subtract_list(lst1, lst2):
    lst = lst1.copy()
    for element in lst2:
        try:
            lst.remove(element)
        except ValueError:
            pass
    return lst

def list_slice(lst):
    arr = lst
    length = len(arr)
    n = 0
    s = 10
    result = []
    for i in range(5):
        result.append(arr[n:n+s:1])
        n += s
        if n >= length:
            break
    return result

def make_static_tmp_dir():
    try:
        os.makedirs(static_tmp_path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(static_tmp_path):
            pass
        else:
            raise

@app.route("/")
def hello():
    return "Hello World"

@app.route("/callback", methods=['POST'])
def callback():
   
    signature = request.headers['X-Line-Signature']

   
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    
    try:
        handler.handle(body, signature)
    except LineBotApiError as e:
        print("Got exception from LINE Messaging API: %s\n" % e.message)
        for m in e.error.details:
            print("  %s: %s" % (m.property, m.message))
        print("\n")
    except InvalidSignatureError:
        abort(400)

    return 'OK'


@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    text = event.message.text

    with open('gamedata.json', 'r+') as f:
        game = json.load(f)
        game_id_group = game["group"]
        game_id_room = game["room"]
        user_card = game["user"]

        groupid = json.dumps(game_id_group, ensure_ascii=False)
        userid = json.dumps(user_card, ensure_ascii=False)
        print(groupid)
        print(userid)

        if text == '大富豪スタート':

            image_carousel_template = ImageCarouselTemplate(columns=[
                ImageCarouselColumn(image_url=request.url_root + '/static/start_game.png',
                                    action=PostbackAction(label='ゲームを開始する',
                                                        data='start_game')),
                ImageCarouselColumn(image_url=request.url_root + '/static/settings.png',
                                    action=PostbackAction(label='設定を変更する',
                                                        data='set_config')),
                ImageCarouselColumn(image_url=request.url_root + '/static/explain.png',
                                    action=PostbackAction(label='ルール説明を見る',
                                                        data='show_rule'))
            ])

            template_message = TemplateSendMessage(
                alt_text='大富豪スタートメニュー', template=image_carousel_template)

            players = {}
            configs = {"eight":False, "eleven":False, "revol":False, "spade3":False, "sootlock":False, "steplock":False, "kingdie":False, "e_change":False, "change":False, "soot":False, "step":False}
            rankings = {"past":[], "now":[]}
            cards = []
            game_data = {"menber":players, "config":configs, "ranking":rankings, "card":cards}

            if isinstance(event.source, SourceGroup):
                game_id_group[event.source.group_id] = game_data

                line_bot_api.reply_message(event.reply_token, template_message)
            elif isinstance(event.source, SourceRoom):
                game_id_room[event.source.room_id] = game_data

                line_bot_api.reply_message(event.reply_token, template_message)
            else:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text="複数人のトークルームでない場合、大富豪をお楽しみいただけません。"))

        elif text == '八切り有効' and not isinstance(event.source, SourceUser):
            if isinstance(event.source, SourceGroup):
                if event.source.group_id in game_id_group:
                    game_id_group[event.source.group_id]["config"]["eight"] = True

            elif isinstance(event.source, SourceRoom):
                if event.source.room_id in game_id_room:
                    game_id_room[event.source.room_id]["config"]["eight"] = True
            
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text='八切りが有効になりました'))

        elif text == '八切り無効' and not isinstance(event.source, SourceUser):
            if isinstance(event.source, SourceGroup):
                if event.source.group_id in game_id_group:
                    game_id_group[event.source.group_id]["config"]["eight"] = False
                    
            elif isinstance(event.source, SourceRoom):
                if event.source.room_id in game_id_room:
                    game_id_room[event.source.room_id]["config"]["eight"] = False
            
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text='八切りが無効になりました'))

        elif text == 'イレブンバック有効' and not isinstance(event.source, SourceUser):
            if isinstance(event.source, SourceGroup):
                if event.source.group_id in game_id_group:
                    game_id_group[event.source.group_id]["config"]["eleven"] = True
                    
            elif isinstance(event.source, SourceRoom):
                if event.source.room_id in game_id_room:
                    game_id_room[event.source.room_id]["config"]["eleven"] = True

            line_bot_api.reply_message(event.reply_token, TextSendMessage(text='イレブンバックが有効になりました'))

        elif text == 'イレブンバック無効' and not isinstance(event.source, SourceUser):
            if isinstance(event.source, SourceGroup):
                if event.source.group_id in game_id_group:
                    game_id_group[event.source.group_id]["config"]["eleven"] = False
                    
            elif isinstance(event.source, SourceRoom):
                if event.source.room_id in game_id_room:
                    game_id_room[event.source.room_id]["config"]["eleven"] = False
            
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text='イレブンバックが無効になりました'))

        elif text == '革命有効' and not isinstance(event.source, SourceUser):
            if isinstance(event.source, SourceGroup):
                if event.source.group_id in game_id_group:
                    game_id_group[event.source.group_id]["config"]["revol"] = True
                    
            elif isinstance(event.source, SourceRoom):
                if event.source.room_id in game_id_room:
                    game_id_room[event.source.room_id]["config"]["revol"] = True
            
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text='革命が有効になりました'))

        elif text == '革命無効' and not isinstance(event.source, SourceUser):
            if isinstance(event.source, SourceGroup):
                if event.source.group_id in game_id_group:
                    game_id_group[event.source.group_id]["config"]["revol"] = False
                    
            elif isinstance(event.source, SourceRoom):
                if event.source.room_id in game_id_room:
                    game_id_room[event.source.room_id]["config"]["revol"] = False
            
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text='革命が無効になりました'))

        elif text == 'スぺ3有効' and not isinstance(event.source, SourceUser):
            if isinstance(event.source, SourceGroup):
                if event.source.group_id in game_id_group:
                    game_id_group[event.source.group_id]["config"]["spade3"] = True
                    
            elif isinstance(event.source, SourceRoom):
                if event.source.room_id in game_id_room:
                    game_id_room[event.source.room_id]["config"]["spade3"] = True
            
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text='スぺ3が有効になりました'))

        elif text == 'スぺ3無効' and not isinstance(event.source, SourceUser):
            if isinstance(event.source, SourceGroup):
                if event.source.group_id in game_id_group:
                    game_id_group[event.source.group_id]["config"]["spade3"] = False

            elif isinstance(event.source, SourceRoom):
                if event.source.room_id in game_id_room:
                    game_id_room[event.source.room_id]["config"]["spade3"] = False
            
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text='スぺ3が無効になりました'))

        elif text == 'スート縛り有効' and not isinstance(event.source, SourceUser):
            if isinstance(event.source, SourceGroup):
                if event.source.group_id in game_id_group:
                    game_id_group[event.source.group_id]["config"]["sootlock"] = True
                    
            elif isinstance(event.source, SourceRoom):
                if event.source.room_id in game_id_room:
                    game_id_room[event.source.room_id]["config"]["sootlock"] = True
            
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text='スート縛りが有効になりました'))

        elif text == 'スート縛り無効' and not isinstance(event.source, SourceUser):
            if isinstance(event.source, SourceGroup):
                if event.source.group_id in game_id_group:
                    game_id_group[event.source.group_id]["config"]["sootlock"] = False
                    
            elif isinstance(event.source, SourceRoom):
                if event.source.room_id in game_id_room:
                    game_id_room[event.source.room_id]["config"]["sootlock"] = False
            
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text='スート縛りが無効になりました'))

        elif text == '階段縛り有効' and not isinstance(event.source, SourceUser):
            if isinstance(event.source, SourceGroup):
                if event.source.group_id in game_id_group:
                    game_id_group[event.source.group_id]["config"]["steplock"] = True

            elif isinstance(event.source, SourceRoom):
                if event.source.room_id in game_id_room:
                    game_id_room[event.source.room_id]["config"]["steplock"] = True
            
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text='階段縛りが有効になりました'))

        elif text == '階段縛り無効' and not isinstance(event.source, SourceUser):
            if isinstance(event.source, SourceGroup):
                if event.source.group_id in game_id_group:
                    game_id_group[event.source.group_id]["config"]["steplock"] = False
                    
            elif isinstance(event.source, SourceRoom):
                if event.source.room_id in game_id_room:
                    game_id_room[event.source.room_id]["config"]["steplock"] = False

            line_bot_api.reply_message(event.reply_token, TextSendMessage(text='階段縛りが無効になりました'))

        elif text == '都落ち・カード交換有効' and not isinstance(event.source, SourceUser):
            if isinstance(event.source, SourceGroup):
                if event.source.group_id in game_id_group:
                    game_id_group[event.source.group_id]["config"]["kingdie"] = True

            elif isinstance(event.source, SourceRoom):
                if event.source.room_id in game_id_room:
                    game_id_room[event.source.room_id]["config"]["kingdie"] = True
            
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text='都落ち・カード交換が有効になりました'))

        elif text == '都落ち・カード交換無効' and not isinstance(event.source, SourceUser):
            if isinstance(event.source, SourceGroup):
                if event.source.group_id in game_id_group:
                    game_id_group[event.source.group_id]["config"]["kingdie"] = False

            elif isinstance(event.source, SourceRoom):
                if event.source.room_id in game_id_room:
                    game_id_room[event.source.room_id]["config"]["kingdie"] = False
            
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text='都落ち・カード交換が無効になりました'))

        elif text == 'ゲームに参加する' and not isinstance(event.source, SourceUser):
            if isinstance(event.source, SourceGroup):
                if event.source.group_id in game_id_group:
                    game_id_group[event.source.group_id]["menber"][event.source.user_id] = line_bot_api.get_profile(event.source.user_id).display_name
                    user_card[event.source.user_id] = []
                    user_card["cards"][event.source.user_id] = []
                    line_bot_api.reply_message(
                        event.reply_token,
                        TextSendMessage(text=f"{line_bot_api.get_profile(event.source.user_id).display_name}さんの参加を受け付けました。"))
                else:
                    line_bot_api.reply_message(
                        event.reply_token,
                        TextSendMessage(text="先にゲームを開始してください。"))
            elif isinstance(event.source, SourceRoom):
                if event.source.room_id in game_id_room:
                    game_id_room[event.source.room_id]["menber"][event.source.user_id] = line_bot_api.get_profile(event.source.user_id).display_name
                    user_card[event.source.user_id] = []
                    user_card["cards"][event.source.user_id] = []
                    line_bot_api.reply_message(
                        event.reply_token,
                        TextSendMessage(text=f"{line_bot_api.get_profile(event.source.user_id).display_name}さんの参加を受け付けました。"))
                else:
                    line_bot_api.reply_message(
                        event.reply_token,
                        TextSendMessage(text="先にゲームを開始してください。"))

        elif text == 'カードを確認する' and isinstance(event.source, SourceUser):
            try:
                cards = user_card[event.source.user_id]
            except KeyError:
                return None
            column = []
            for i in cards:
                column.append(ImageCarouselColumn(image_url=request.url_root + f'/static/cards/{i}.png',
                                                action=PostbackAction(label='これを提出する',
                                                                        data=f'release {i}')))

            lst = list_slice(column)
            template_message = []
            for i in range(len(lst)):
                image_carousel_template = ImageCarouselTemplate(columns=lst[i])

                template_message.append(TemplateSendMessage(alt_text='あなたのカード', template=image_carousel_template))

            line_bot_api.reply_message(event.reply_token, template_message)

        elif text == '提出する' and not isinstance(event.source, SourceUser):

            try:
                card = user_card["cards"][event.source.user_id]
            except KeyError:
                return None
            send = []
            breakflg = False
            if isinstance(event.source, SourceGroup):
                try:
                    trash = game_id_group[event.source.group_id]["card"]
                    game_id_group[event.source.group_id]["card"] = []
                except KeyError:
                    return None
                many = len(trash)
                config = game_id_group[event.source.group_id]["config"]
                player = game_id_group[event.source.group_id]["menber"][event.source.user_id]
            elif isinstance(event.source, SourceRoom):
                try:
                    trash = game_id_room[event.source.room_id]["card"]
                    game_id_room[event.source.room_id]["card"] = []
                except KeyError:
                    return None
                many = len(trash)
                config = game_id_room[event.source.room_id]["config"]
                player = game_id_room[event.source.room_id]["menber"][event.source.user_id]
            e_change = config["e_change"]
            change = config["change"]
            stepflg = 0
            message = []
            send_msg = ''
            jkr = 1
            j = 0
            reset = False
            msg = []
            soot = []
            tsoot = []

            if many != 0 and len(card) != many:
                if isinstance(event.source, SourceGroup):
                    game_id_group[event.source.group_id]["card"] = trash
                elif isinstance(event.source, SourceRoom):
                    game_id_room[event.source.room_id]["card"] = trash
                user_card["cards"][event.source.user_id] = []
                msg = [TextSendMessage(text="場のカードと提出するカードの枚数が違います。カードを一から選びなおすか、パスすることを宣言してください。")]
            else:
                if config["sootlock"]:
                    for i in range(many):
                        if card[i] == 52 or card[i] == 53:
                            tsoot.append(trash[i] // 13)
                            continue
                        soot.append(card[i] // 13)
                        tsoot.append(trash[i] // 13)

                    if config["soot"] and (len(tsoot)-len(soot)) != len(subtract_list(tsoot,soot)):
                        user_card["cards"][event.source.user_id] = []
                        send = [TextSendMessage(text="場のカードと同じスートのカードを提出する必要があります。カードを一から選びなおすか、パスすることを宣言してください。")]

                    elif not config["soot"] and subtract_list(soot, tsoot) == [] and many != 0:
                        if isinstance(event.source, SourceGroup):
                            game_id_group[event.source.group_id]["config"]["soot"] = True
                        elif isinstance(event.source, SourceRoom):
                            game_id_room[event.source.room_id]["config"]["soot"] = True

                        message.append('スート縛りが発生しました。現在出ているスートと同じ組み合わせのスートのみ提出できます。')

                for i in card:
                    if i == 52 or i == 53:
                        num = 13
                    else:
                        num = i % 13
                    for j in range(many):
                        if trash[j] == 52 or trash[j] == 53:
                            if config["spade3"] and many == 1 and i == 13:
                                reset = True
                                message.append(f'スぺ3返しが発生しました。{player}さんはもう一度カードを選択し、提出してください。')

                            else:
                                user_card["cards"][event.source.user_id] = []
                                send = [TextSendMessage(text="場のカードより強いカードを提出する必要があります。カードを一から選びなおすか、パスすることを宣言してください。")]
                                breakflg = True
                                break

                        if (e_change or change) and not (e_change and change):
                            if num >= trash[j]%13 and num != 13:
                                user_card["cards"][event.source.user_id] = []
                                send = [TextSendMessage(text="場のカードより小さいカードを提出する必要があります。カードを一から選びなおすか、パスすることを宣言してください。")]
                                breakflg = True
                                break 

                        elif num <= trash[j]%13:
                            user_card["cards"][event.source.user_id] = []
                            send = [TextSendMessage(text="場のカードより大きいカードを提出する必要があります。カードを一から選びなおすか、パスすることを宣言してください。")]
                            breakflg = True
                            break

                        if config["steplock"]:
                            if config["step"] and (trash[j]%13)+1 != num and num != 13:
                                user_card["cards"][event.source.user_id] = []
                                send = [TextSendMessage(text="場のカードより1大きいカードを提出する必要があります。カードを一から選びなおすか、パスすることを宣言してください。")]
                                breakflg = True
                                break

                            elif not config["step"] and (trash[j]%13)+1 == num:
                                stepflg += 1

                    if breakflg:
                        break

                    if num == 5 and config["eight"]:
                        reset = True
                        message.append(f'八切りが発生しました。{player}さんはもう一度カードを選択し、提出してください。')

                    elif num == 8 and config["eleven"]:
                        if isinstance(event.source, SourceGroup):
                            game_id_group[event.source.group_id]["config"]["e_change"] = True
                        elif isinstance(event.source, SourceRoom):
                            game_id_room[event.source.room_id]["card"]["e_change"] = True

                        message.append('イレブンバックが発生しました。場のカードの序列が反転します。')

                    if config["revol"] and len(card) >= 4:
                        if isinstance(event.source, SourceGroup):
                            game_id_group[event.source.group_id]["config"]["change"] = not change
                        elif isinstance(event.source, SourceRoom):
                            game_id_room[event.source.room_id]["config"]["change"] = not change

                        message.append('革命が発生しました。場のカードの序列が反転します。')

                    send.append(ImageCarouselColumn(image_url=request.url_root + f'/static/cards/{i}.png',
                                                    action=PostbackAction(label='提出されたカード',
                                                                        data='pass')))

                    if isinstance(event.source, SourceGroup):
                        if (i == 52 or i == 53):
                            if subtract_list(card, [52,53]) == []:
                                game_id_group[event.source.group_id]["card"].append(i)
                            
                            else:
                                jkr += 1

                        elif config["soot"] and jkr >= 2:
                                while jkr >= 2: 
                                    b = subtract_list(tsoot, soot)[0]
                                    a = b*13 + num
                                    game_id_group[event.source.group_id]["card"].append(a)
                                    soot.append(b)
                                    jkr -= 1

                                game_id_group[event.source.group_id]["card"].append(i)

                        else:
                            for i in range(jkr):
                                game_id_group[event.source.group_id]["card"].append(i)
                                jkr = 1

                    elif isinstance(event.source, SourceRoom):
                        if (i == 52 or i == 53):
                            if subtract_list(card, [52,53]) == []:
                                game_id_room[event.source.room_id]["card"].append(i)
                            
                            else:
                                jkr += 1

                        elif config["soot"] and jkr >= 2:
                                while jkr >= 2: 
                                    b = subtract_list(tsoot, soot)[0]
                                    a = b*13 + num
                                    game_id_room[event.source.room_id]["card"].append(a)
                                    soot.append(b)
                                    jkr -= 1

                                game_id_room[event.source.room_id]["card"].append(i)

                        else:
                            for z in range(jkr):
                                game_id_room[event.source.room_id]["card"].append(i)
                                jkr = 1
                if stepflg == many and subtract_list(card, [52,53]) != [] and many != 0:
                    if isinstance(event.source, SourceGroup):
                        game_id_group[event.source.group_id]["config"]["step"] = True
                    elif isinstance(event.source, SourceRoom):
                        game_id_room[event.source.room_id]["card"]["step"] = True

                    message.append('階段縛りが発生しました。場のカードより1だけ強いカードのみ提出できます。')

                message.append('次の人はカードを選択し、「提出する」と発言してください。')        

            if reset:
                if isinstance(event.source, SourceGroup):
                    game_id_group[event.source.group_id]["card"] = []
                    game_id_group[event.source.group_id]["config"]["e_change"] = False
                    game_id_group[event.source.group_id]["config"]["soot"] = False
                    game_id_group[event.source.group_id]["config"]["step"] = False
                elif isinstance(event.source, SourceRoom):
                    game_id_room[event.source.room_id]["card"] = []
                    game_id_room[event.source.room_id]["card"]["e_change"] = False
                    game_id_room[event.source.room_id]["card"]["soot"] = False
                    game_id_room[event.source.room_id]["card"]["step"] = False

            user_card[event.source.user_id] = subtract_list(user_card[event.source.user_id], user_card["cards"][event.source.user_id])
            user_card["cards"][event.source.user_id] = []

            if send != []:

                message = list(set(message))

                send_msg = '\n\n'.join(message)

                print(send)

                image_carousel_template = ImageCarouselTemplate(columns=send)

                template_message = TemplateSendMessage(
                    alt_text='場', template=image_carousel_template)

                msg = [template_message, TextSendMessage(text=send_msg)]

            line_bot_api.reply_message(event.reply_token, msg)


        elif text == '全員がパスを選択' and not isinstance(event.source, SourceUser):
            if isinstance(event.source, SourceGroup):
                game_id_group[event.source.group_id]["card"] = []
                game_id_group[event.source.group_id]["config"]["e_change"] = False
                game_id_group[event.source.group_id]["config"]["soot"] = False
                game_id_group[event.source.group_id]["config"]["step"] = False
            elif isinstance(event.source, SourceRoom):
                game_id_room[event.source.room_id]["card"] = []
                game_id_room[event.source.room_id]["card"]["e_change"] = False
                game_id_room[event.source.room_id]["card"]["soot"] = False
                game_id_room[event.source.room_id]["card"]["step"] = False

            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="場を削除しました。最後に提出した人からゲームを再開してください。"))


        elif text == 'あがる' and not isinstance(event.source, SourceUser):
            send = []
            fin = False
            if user_card[event.source.user_id] != []:
                send = [TextSendMessage(text="まだ手持ちにカードが残っています。")] 

            else:
                if isinstance(event.source, SourceGroup):
                    game_id_group[event.source.group_id]["ranking"]["now"].append(event.source.user_id)
                    game = game_id_group[event.source.group_id]
                    winner = game["menber"][event.source.user_id]
                    send.append(TextSendMessage(text=f"{winner}さんがあがりました。"))
                elif isinstance(event.source, SourceRoom):
                    game_id_room[event.source.room_id]["ranking"]["now"].append(event.source.user_id)
                    game = game_id_room[event.source.room_id]

                if game["ranking"]["past"] != []:
                    if game["config"]["kingdie"] and len(game["ranking"]["now"]) == 1 and game["ranking"]["past"][0] != game["ranking"]["now"][0]:
                        king = game["ranking"]["past"][0]
                        name = game["menber"][king]
                        send.append(TextSendMessage(text=f"都落ちが発生しました。{name}さんは大貧民となります。"))
                        if isinstance(event.source, SourceGroup):
                            game_id_group[event.source.group_id]["ranking"]["died"] = king
                        elif isinstance(event.source, SourceRoom):
                            game_id_room[event.source.room_id]["ranking"]["died"] = king

                if len(game["ranking"]["now"]) + 2 == len(game["menber"]) and "died" in game["ranking"]:
                        player = list(game["menber"].keys())
                        game["ranking"]["now"].append(game["ranking"]["died"])
                        poor = subtract_list(player, game["ranking"]["now"])

                        if isinstance(event.source, SourceGroup):
                            game_id_group[event.source.group_id]["ranking"]["now"].append(poor)
                            game_id_group[event.source.group_id]["ranking"]["now"].append(game["ranking"]["died"])
                        elif isinstance(event.source, SourceRoom):
                            game_id_room[event.source.room_id]["ranking"]["now"].append(poor)
                            game_id_room[event.source.room_id]["ranking"]["now"].append(game["ranking"]["died"])
                        fin = True

                elif len(game["ranking"]["now"]) + 1 == len(game["menber"]):
                    player = list(game["menber"].keys())
                    poor = subtract_list(player, game["ranking"]["now"])
                    if isinstance(event.source, SourceGroup):
                        game_id_group[event.source.group_id]["ranking"]["now"].append(poor)
                    elif isinstance(event.source, SourceRoom):
                        game_id_room[event.source.room_id]["ranking"]["now"].append(poor)
                    fin = True

                if fin:
                    sendstr = []
                    for i, j in enumerate(game["ranking"]["now"]):
                        if i == 0:
                            level = "大富豪"
                        elif i == 1:
                            level = "富豪"
                        elif i == len(game["ranking"]["now"]) - 2:
                            level = "貧民"
                        elif i == len(game["ranking"]["now"]) - 1:
                            level = "大貧民"
                        else:
                            level = "平民"
                        name = game["menber"][j]

                        sendstr.append(f"{level}:{name}")

                    send_msg = '\n'.join(sendstr)
                    send.append(TextSendMessage(text=send_msg))

                    buttons_template = ButtonsTemplate(
                        title='ゲームが終了しました', text='ゲームを続行しますか？', actions=[
                            PostbackAction(label='続ける', data='continued'),
                            PostbackAction(label='やめる', data='finish'),
                            PostbackAction(label='設定を変更', data='set_config'),
                            PostbackAction(label='説明を見る', data='show_rule'),
                        ])
                    template_message = TemplateSendMessage(
                        alt_text='ゲーム終了メニュー', template=buttons_template)
                    send.append(template_message)

            line_bot_api.reply_message(event.reply_token, send)

        elif text == "終了する":
            buttons_template = ButtonsTemplate(title='終了しますか？', text='ゲームのデータは完全に削除されます', actions=[PostbackAction(label='終了する', action='finish')])
            template_message = TemplateSendMessage(
                alt_text='終了ボタン', template=buttons_template)
            line_bot_api.reply_message(event.reply_token, template_message)


        data = {'group':game_id_group, 'room':game_id_room, 'user':user_card}
        json.dump(data, f, ensure_ascii=False, indent=3)


@handler.add(PostbackEvent)
def handle_postback(event):

    with open('gamedata.json', 'r+') as f:
        game = json.load(f)
        game_id_group = game["group"]
        game_id_room = game["room"]
        user_card = game["user"]

        groupid = json.dumps(game_id_group, ensure_ascii=False)
        userid = json.dumps(user_card, ensure_ascii=False)
        print(groupid)
        print(userid)

        if event.postback.data == 'show_rule':
            explain = [
                TextSendMessage(text="基本ルール：\n　前の人が出したカードより強いカードを出していって、手持ちのカードを早くなくした人が勝ちです。\n\nカードの強さ：\n　最弱を3として、4,5,...Q,K,A,2の順に強くなります。最強はジョーカーです。\n\nカードの種類：\n　各スートの十三枚とジョーカー二枚の計54枚で行います。\n\n誰もカードを出せない場合：\n　全員がパスを行ってターンを終了した場合、場のカードを削除し、最後に出した人がもう一度カードを出して再開します。\n\n複数カードについて：\n　場が更新された時、同じ数の書かれたカードは複数枚提出することが可能です。その場合、後続は提出された数と同じだけのカードを提出する必要があります(ジョーカーを含んでもよい)。\n\n特殊ルール：\n　特殊なルールです。「設定を変更」からオン・オフを切り替えられます(ゲーム開始時はオフになっています)。\n\n　八切り：\n　　8のカードが出た時に場のカードを削除し、8を出した人がもう一度カードを出して再開します。\n\n　イレブンバック：\n　　Jのカードが出た時に、ジョーカーを除くカードの強さを反転させるか選びます。反転は場のカードが削除されるまで続きます。\n\n　革命：\n　　4枚のカードが同時に場に出た時、ジョーカーを除くカードの強さを反転させます。反転は再び革命が起こるまで続きます。\n\n　スペ3：\n　　ジョーカー一枚が出た時、スペードの3を場に出すことができます。この時、場のカードを削除しスペードの3を出した人からゲームを再開します。\n\n　縛り：\n　　条件を満たしたとき、提出条件が追加されます。効果は場が削除されるまで続きます。ジョーカーの提出に縛りは適用されません。\n\n　　スート縛り：\n　　　連続して同じスートのカードが提出された時、同じスートのカードしか出せなくなります。\n\n　　階段縛り：\n　　　場のカードより1だけ強いカードが提出された時、次の強さのカードしか出せなくなります。ジョーカーは数字カードの代用となります（例えば4→5→ジョーカーと出た場合、このジョーカーは6として扱われる）\n\n　都落ち：\n　　大富豪が1抜け出来なかった場合、強制的に大貧民となります。このルールを適用すると、カード交換も自動で適用されます。\n\n　カード交換：\n　　カードが配られた時、大貧民は最も強いカードを二枚大富豪に、大富豪は好きなカードを二枚大貧民にそれぞれ渡します。同様に、富豪と貧民はカードを一枚交換します。都落ちがオンの時のみ適用されます。"),
                TextSendMessage(text="「大富豪スタート」と発言することで、スタートメニューを表示します。\n「（特殊ルール名）有効/無効」と発言することで、その特殊ルールを有効/無効にすることができます。都落ちとカード交換は同時発生のため、「都落ち・カード交換有効/無効」と発言してください。\n「ゲームに参加する」と発言することで、ゲームに参加することができます。\n「カードを確認する」とbotとのトークで発言すると、カードが表示され、提出するカードを選ぶことができます。\nカードを選択後にグループで「提出する」と発言すると、選択したカードが提出されます。\n「全員がパスを選択」と発言することで、場を削除し、新しいターンを開始します。\n手札がなくなった時点で「あがる」と発言してください。手札がないことを確認したのち、あがることができます。\n「終了する」と発言することで、いつでもゲームを終了できます。但し、戦績などのデータはすべて破棄されますのでご注意ください。\n\nパスの処理・あがりの処理は自動で行われません。条件を満たした時は必ず自分で発言するようにしてください。\nまた、PC版LINEでは現在大富豪をお楽しみいただけません。\nタイムアウトエラーにより返信が来ない時があります。お手数ですが、返信が来るまで根気よくメッセージを送信してください。")
            ]
            line_bot_api.reply_message(event.reply_token, explain)
        elif event.postback.data == 'set_config':
            carousel_template = CarouselTemplate(columns=[
                CarouselColumn(text='有効化しますか？', title='八切り', actions=[
                    MessageAction(label='はい', text='八切り有効'),
                    MessageAction(label='いいえ', text='八切り無効')
                ]),
                CarouselColumn(text='有効化しますか？', title='イレブンバック', actions=[
                    MessageAction(label='はい', text='イレブンバック有効'),
                    MessageAction(label='いいえ', text='イレブンバック無効')
                ]),
                CarouselColumn(text='有効化しますか？', title='革命', actions=[
                    MessageAction(label='はい', text='革命有効'),
                    MessageAction(label='いいえ', text='革命無効')
                ]),
                CarouselColumn(text='有効化しますか？', title='スぺ3', actions=[
                    MessageAction(label='はい', text='スぺ3有効'),
                    MessageAction(label='いいえ', text='スぺ3無効')
                ]),
                CarouselColumn(text='有効化しますか？', title='スート縛り', actions=[
                    MessageAction(label='はい', text='スート縛り有効'),
                    MessageAction(label='いいえ', text='スート縛り無効')
                ]),
                CarouselColumn(text='有効化しますか？', title='階段縛り', actions=[
                    MessageAction(label='はい', text='階段縛り有効'),
                    MessageAction(label='いいえ', text='階段縛り無効')
                ]),
                CarouselColumn(text='有効化しますか？', title='都落ち・カード交換', actions=[
                    MessageAction(label='はい', text='都落ち・カード交換有効'),
                    MessageAction(label='いいえ', text='都落ち・カード交換無効')
                ])
            ])
            template_message = TemplateSendMessage(
                alt_text='設定', template=carousel_template)
            line_bot_api.reply_message(event.reply_token, template_message)

        elif event.postback.data == 'start_game':
            buttons_template = ButtonsTemplate(title='ゲームが作成されました', text='ゲームに参加する場合は下のボタンを押す', actions=[MessageAction(label='参加する', text='ゲームに参加する'), PostbackAction(label='開始する', data='load_game')])
            template_message = TemplateSendMessage(
                alt_text='参加ボタン', template=buttons_template)
            line_bot_api.reply_message(event.reply_token, template_message)

        elif event.postback.data == 'load_game':
            trump = rand_ints_nodup(1,54)
            k = 0
            if isinstance(event.source, SourceGroup):
                while k < 54 :
                    for i in list(game_id_group[event.source.group_id]["menber"].keys()):
                        user_card[i].append(trump[k])
                        k += 1
                        if k >= 54:
                            break

                

            if isinstance(event.source, SourceRoom):
                while k < 54 :
                    for i in list(game_id_room[event.source.room_id]["menber"].keys()):
                        user_card[i].append(trump[k])
                        k += 1
                        if k >= 54:
                            break

            line_bot_api.reply_message(event.reply_token, TextSendMessage(text='カードの分配を行いました。botとのトークで「カードを確認する」と発言し、自分の手札を確認してください。全員の確認が終わったら好きな人からカードを提出してください。'))


        elif event.postback.data.startswith('release '):
            num = int(event.postback.data.split(' ')[1])
            error = False
            error2 = False
            error3 = False

            try:
                for i in user_card["cards"][event.source.user_id]:
                    if i % 13 != num % 13 and not (num == 52 or num == 53):
                        error = True

                    elif i == num:
                        error2 = True

                if not num in user_card[event.source.user_id]:
                    error3 = True

            except KeyError:
                pass

            if error:
                send = TextSendMessage(text='違う数のカードは同時に出せません。')

            elif error2:
                send = TextSendMessage(text="同じカードをもう一度提出しようとしています。")

            elif error3:
                send = TextSendMessage(text="あなたの持っていないカードです。")

            else:        
                soot = 0
                no = 0
                if num == 52 or num == 53:
                    st = 'ジョー'
                    no = 'カー'
                else:    
                    soot = num // 13
                    no = ((num % 13) + 3)% 13
                    if soot == 0:
                        st = 'クラブの'
                    elif soot == 1:
                        st = 'スペードの'
                    elif soot == 2:
                        st = 'ダイヤの'
                    elif soot == 3:
                        st = 'ハートの'
                    if no == 11:
                        no = 'J'
                    elif no == 12:
                        no = 'Q'
                    elif no == 0:
                        no = 'K'

                send = TextSendMessage(text=f"{st}{no}を提出します。ほかに提出したいカードがある場合は選択し、グループに戻って「提出する」と発言してください。")
                user_card["cards"][event.source.user_id].append(num)
            line_bot_api.reply_message(event.reply_token, send)

        elif event.postback.data == 'pass':
            pass

        elif event.postback.data == 'continued':
            if isinstance(event.source, SourceGroup):
                past = game_id_group[event.source.group_id]["ranking"]["now"]
                game_id_group[event.source.group_id]["card"] = []
                game_id_group[event.source.group_id]["ranking"] = {"past":past, "now":[]}
                
                for i in list(game_id_group[event.source.group_id]["menber"].keys()):
                    user_card[i] = []
                    user_card[cards] = []

            if isinstance(event.source, SourceRoom):
                past = game_id_room[event.source.room_id]["ranking"]["now"]
                game_id_room[event.source.room_id]["card"] = []
                game_id_room[event.source.room_id]["ranking"] = {"past":past, "now":[]}
                
                for i in list(game_id_group[event.source.room_id]["menber"].keys()):
                    user_card[i] = []
                    user_card[cards] = []

            trump = rand_ints_nodup(0,53)
            k = 0
            if isinstance(event.source, SourceGroup):
                while k < 54 :
                    for i in list(game_id_group[event.source.group_id]["menber"].keys()):
                        user_card[i].append(trump[k])
                        k += 1
                        if k >= 54:
                            break

                

            if isinstance(event.source, SourceRoom):
                while k < 54 :
                    for i in list(game_id_room[event.source.room_id]["menber"].keys()):
                        user_card[i].append(trump[k])
                        k += 1
                        if k >= 54:
                            break

            line_bot_api.reply_message(event.reply_token, TextSendMessage(text='カードの分配を行いました。botとのトークで「カードを確認する」と発言し、自分の手札を確認してください。全員の確認が終わったら好きな人からカードを提出してください。'))

        elif event.postback.data == 'finish':
            if isinstance(event.source, SourceGroup):
                del game_id_group[event.source.group_id]
            elif isinstance(event.source, SourceRoom):
                del game_id_room[event.source.room_id]

            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="大富豪を終了しました。またのご利用をお待ちしております。"))

        data = {'group':game_id_group, 'room':game_id_room, 'user':user_card}
        json.dump(data, f, ensure_ascii=False, indent=3)

@app.route('/static/<path:path>')
def send_static_content(path):
    return send_from_directory('static', path)


if __name__ == "__main__":
    arg_parser = ArgumentParser(
        usage='Usage: python ' + __file__ + ' [--port <port>] [--help]'
    )
    arg_parser.add_argument('-p', '--port', type=int, default=8000, help='port')
    arg_parser.add_argument('-d', '--debug', default=False, help='debug')
    options = arg_parser.parse_args()

    make_static_tmp_dir()

    app.run(debug=options.debug, port=options.port)