from flask import Flask, request, abort

from linebot import LineBotApi, WebhookHandler

from linebot.exceptions import InvalidSignatureError

from linebot.models import (
    MessageEvent,
    TextMessage,
    TextSendMessage,
    StickerMessage
)

import os
import psycopg2
import numpy as np
from portpass import * # noqa

app = Flask(__name__)

# 環境変数を取得
CHANNEL_ACCESS_TOKEN = os.environ["LINE_CHANNEL_ACCESS_TOKEN"]
CHANNEL_SECRET = os.environ["LINE_CHANNEL_SECRET"]

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)
conn = psycopg2.connect(host=HOST, port=PORT, database=DATABASE, user=USER, password=PASSWORD) # noqa
cur = conn.cursor()


# def get_connection():
#     connection =  psycopg2.connect(host=HOST, port=PORT, database=DATABASE, user=USER, password=PASSWORD)
#     return connection


@app.route("/callback", methods=['POST'])
def callback():
    # ヘッダのX-Line-Signatureを取得
    signature = request.headers['X-Line-Signature']

    # JSONを取得
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # 取得した情報を扱う　もしデータが改竄されてたらエラーになる
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'


# テキストメッセージが来たとき
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    global cur
     # with get_connection() as conn:
     #     with conn.cursor() as cur:
    user_id = str(event.source.user_id)
    cur.execute("SELECT * FROM FlagTB WHERE userID='%s';" % user_id)
    result = cur.fetchall()
    if '乱数' in event.message.text or 'リセット' in event.message.text:
        if '乱数' in event.message.text and result[0][1]:
            # min_flagがオンのとき
            cur.execute("UPDATE FlagTB SET maxFlag=FALSE,randFlag=FALSE,stampNum=0 WHERE userID='%s';" % user_id)
            line_bot_api.reply_message(
                event.reply_token,
                (
                    TextSendMessage('再設定するのか'),
                    TextSendMessage('最小値は何にすんだ?')
                ))

        elif '乱数' in event.message.text:
            cur.execute("UPDATE FlagTB SET minFlag=TRUE,stampNum=0 WHERE userID='%s';" % user_id)
            line_bot_api.reply_message(
                event.reply_token,
                (
                    TextSendMessage('お、乱数の生成だな'),
                    TextSendMessage('最小値は何にすんだ?')
                ))
        elif result[0][1]:
            # min_flagがオンのとき
            cur.execute("UPDATE FlagTB SET minFlag=FALSE,maxFlag=FALSE,randFlag=FALSE,stampNum=0 WHERE userID='%s';" % user_id)
            line_bot_api.reply_message(
                event.reply_token,
                (
                    TextSendMessage('リセットするのか'),
                    TextSendMessage('乱数を作りたい時はまた呼んでくれ!')
                ))
        else:
            cur.execute("UPDATE FlagTB SET minFlag=FALSE,maxFlag=FALSE,randFlag=FALSE,stampNum=0 WHERE userID='%s';" % user_id)
            line_bot_api.reply_message(
                event.reply_token,
                (
                    TextSendMessage('リセットするのか'),
                    TextSendMessage('ってまだ何も設定してねぇじゃねぇか!')
                ))
    else:
        if result[0][3]:
            # rand_flagがオンのとき
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(np.random.randint(result[0][5], result[0][4] + 1)))
        elif result[0][2]:
            # max_flagがオンのとき
            if event.message.text.isdecimal():
                max_number = int(event.message.text)
                min_number = result[0][5]
                min_number, max_number = min(min_number, max_number), max(min_number, max_number)
                cur.execute("UPDATE FlagTB SET randFlag=TRUE,maxNumber=%d,minNumber=%d,stampNum=0 WHERE userID='%s';" % (max_number, min_number, user_id))
                line_bot_api.reply_message(
                    event.reply_token,
                    (
                        TextSendMessage('よし!\n乱数の設定完了だ!'),
                        TextSendMessage('あとは適当に話しかけてくれりゃいいぞ')
                    ))
            else:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage('わりいけど、アラビア数字の自然数のみのメッセージにしてくんねぇか?'))
        elif result[0][1]:
            # min_flagがオンのとき
            if event.message.text.isdecimal():
                min_number = int(event.message.text)
                cur.execute("UPDATE FlagTB SET maxFlag=TRUE,minNumber=%d,stampNum=0 WHERE userID='%s';" % (min_number, user_id))
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage('最大値は何にすんだ?'))
            else:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage('わりいけど、アラビア数字の自然数のみのメッセージにしてくんねぇか?'))

        else:
            cur.execute("UPDATE FlagTB SET stampNum=0 WHERE userID='%s';" % user_id)
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage('ちょっと"乱数"って言ってみねぇか?'))


# スタンプが来たとき
@handler.add(MessageEvent, message=StickerMessage)
def handle_sticker(event):
    # with get_connection() as conn:
    #     with conn.cursor() as cur:
    user_id = str(event.source.user_id)
    cur.execute("SELECT * FROM FlagTB WHERE userID='%s';" % user_id)
    result = cur.fetchall()
    if result[0][3]:
        # rand_flagがオンのとき
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(np.random.randint(result[0][5], result[0][4] + 1)))
    elif result[0][2]:
        # max_flagがオンのとき
        line_bot_api.reply_message(event.reply_token, (
            TextSendMessage('いいスタンプだなぁ'),
            TextSendMessage('でも今は最大値を教えてくれ')
        ))
    elif result[0][2]:
        # min_flagがオンのとき
        line_bot_api.reply_message(event.reply_token, (
            TextSendMessage('いいスタンプだなぁ'),
            TextSendMessage('でも今は最小値を教えてくれ')
        ))
    else:
        stamp_num = result[0][6]
        stamp_num += 1
        cur.execute("UPDATE FlagTB SET stampNum=%d WHERE userID='%s';" % (stamp_num, user_id))
        if stamp_num > 10:
            line_bot_api.reply_message(event.reply_token, (
                TextSendMessage('お前オラに%d回も連続でスタンプ送って何がしてぇんだ!?' % stamp_num),
                TextSendMessage('馬鹿なことしてねえで乱数って言え!!!')
            ))
        else:
            line_bot_api.reply_message(event.reply_token, (
                TextSendMessage('いいスタンプだなぁ'),
                TextSendMessage('ところで"乱数"って言ってみねぇか？')
            ))


if __name__ == "__main__":
    # app.run()
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
