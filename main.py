from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError

from linebot.models import (
    MessageEvent,
    TextMessage,
    TextSendMessage,
    StickerMessage,
    ImageMessage
)

import os
import psycopg2
import numpy as np
from google.cloud import vision
from io import BytesIO

app = Flask(__name__)

# 環境変数を取得
CHANNEL_ACCESS_TOKEN = os.environ["LINE_CHANNEL_ACCESS_TOKEN"]
CHANNEL_SECRET = os.environ["LINE_CHANNEL_SECRET"]
DATABASE_URL = os.environ["DATABASE_URL"]

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)


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


def get_connection():
    return psycopg2.connect(DATABASE_URL)


def do_sql_select(sql):
    result = None
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            result = cur.fetchall()
    return result


def do_sql_other(sql):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)


# テキストメッセージが来たとき
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = str(event.source.user_id)
    result = do_sql_select("SELECT * FROM FlagTB WHERE userID='%s';" % user_id)

    if result: # データベースに登録されているユーザかどうか
        # データベースに登録されているユーザーならここに入る
        if '乱数' in event.message.text or 'ランダム' in event.message.text:
            # '乱数''ランダム'を含む発言の場合は最小値の設定からはじめる
            if result[0][2]:
                # 何かを設定していた時(max_flagがTRUEの時)に発言した場合はここに入る
                do_sql_other("UPDATE FlagTB SET maxFlag=FALSE,randFlag=FALSE,stampNum=0 WHERE userID='%s';" % user_id)
                line_bot_api.reply_message(
                    event.reply_token,
                    (
                        TextSendMessage('再設定するんですね'),
                        TextSendMessage('最小値は何にしますか？')
                    )
                )
            else:
                # なにも設定せず発言した場合はここに入る
                do_sql_other("UPDATE FlagTB SET minFlag=TRUE,stampNum=0 WHERE userID='%s';" % user_id)
                line_bot_api.reply_message(
                    event.reply_token,
                    (
                        TextSendMessage('出番ですね'),
                        TextSendMessage('最小値は何にしますか？')
                    )
                )

        elif 'リセット' in event.message.text or 'ストップ' in event.message.text or '中止' in event.message.text:
            # 'リセット'を含む発言の場合は話しかける前の状態に初期化する
            if result[0][2]:
                # 何かを設定していた時(max_flagがTRUEの時)に'リセット'と発言した
                do_sql_other("UPDATE FlagTB SET minFlag=FALSE,maxFlag=FALSE,randFlag=FALSE,stampNum=0 WHERE userID='%s';" % user_id)
                line_bot_api.reply_message(
                    event.reply_token,
                    (
                        TextSendMessage('リセットするんですね'),
                        TextSendMessage('出番の時はまた呼んでください')
                    )
                )
            else:
                # なにもなしにリセット
                do_sql_other("UPDATE FlagTB SET minFlag=FALSE,maxFlag=FALSE,randFlag=FALSE,stampNum=0 WHERE userID='%s';" % user_id)
                line_bot_api.reply_message(
                    event.reply_token,
                    (
                        TextSendMessage('リセットするんですね'),
                        TextSendMessage('まだ何も設定していませんけど')
                    )
                )

        else:
            # '乱数'と'リセット'以外の発言だった場合は乱数の生成を進める
            if result[0][3]:
                # rand_flagがTRUEのとき、乱数を生成してメッセージを送る
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(np.random.randint(result[0][5], result[0][4] + 1))
                )

            elif result[0][2]:
                # max_flagがTRUEのときは最大値の設定を行う
                if event.message.text.isdecimal():
                    # 自然数なら最大値の設定を行い、乱数生成の準備が整ったことを伝える
                    max_number = int(event.message.text)
                    if max_number > 999999999:
                        max_number = 999999999
                    min_number = result[0][5]
                    min_number, max_number = min(min_number, max_number), max(min_number, max_number)
                    do_sql_other("UPDATE FlagTB SET randFlag=TRUE,maxNumber=%d,minNumber=%d,stampNum=0 WHERE userID='%s';" % (max_number, min_number, user_id))
                    line_bot_api.reply_message(
                        event.reply_token,
                        (
                            TextSendMessage('これで準備はオーケーです'),
                            TextSendMessage('あとは適当に話しかけてください')
                        )
                    )
                else:
                    do_sql_other("UPDATE FlagTB SET stampNum=0 WHERE userID='%s';" % user_id)
                    line_bot_api.reply_message(
                        event.reply_token,
                        (
                            TextSendMessage('そのメッセージでは最大値がわかりません'),
                            TextSendMessage('アラビア数字の自然数のみのメッセージにして欲しいです')
                        )
                    )

            elif result[0][1]:
                # min_flagがTRUEのときは最小値の設定を行う
                if event.message.text.isdecimal():
                    # 自然数なら最小値の設定を行い、最大値の設定を促す
                    min_number = int(event.message.text)
                    if min_number > 999999999:
                        min_number = 999999999
                    do_sql_other("UPDATE FlagTB SET maxFlag=TRUE,minNumber=%d,stampNum=0 WHERE userID='%s';" % (min_number, user_id))
                    line_bot_api.reply_message(
                        event.reply_token,
                        (
                            TextSendMessage('なるほど'),
                            TextSendMessage('最大値は何にしますか?')
                        )
                    )
                else:
                    do_sql_other("UPDATE FlagTB SET stampNum=0 WHERE userID='%s';" % user_id)
                    line_bot_api.reply_message(
                        event.reply_token,
                        (
                            TextSendMessage('そのメッセージでは最小値がわかりません'),
                            TextSendMessage('アラビア数字の自然数のみのメッセージにして欲しいです')
                        )
                    )

            else:
                # 何も関係のない発言だった場合には'乱数'を促す
                do_sql_other("UPDATE FlagTB SET stampNum=0 WHERE userID='%s';" % user_id)
                line_bot_api.reply_message(
                    event.reply_token,
                    (
                        TextSendMessage('"ランダム"'),
                        TextSendMessage('なんて言ってみませんか?')
                    )
                )

    else:
        # データベースに登録されていないユーザーは登録する
        if '乱数' in event.message.text:
            do_sql_other("INSERT INTO FlagTB VALUES ('%s',TRUE,FALSE,FALSE,-1,-1,0);" % user_id)
            line_bot_api.reply_message(
                event.reply_token,
                (
                    TextSendMessage('出番ですね'),
                    TextSendMessage('最小値は何にしますか？')
                )
            )
        elif 'リセット' in event.message.text:
            do_sql_other("INSERT INTO FlagTB VALUES ('%s',TRUE,FALSE,FALSE,-1,-1,0);" % user_id)
            line_bot_api.reply_message(
                event.reply_token,
                (
                    TextSendMessage('リセットするんですね'),
                    TextSendMessage('まだ何も設定していませんけど')
                )
            )
        else:
            do_sql_other("INSERT INTO FlagTB VALUES ('%s',TRUE,FALSE,FALSE,-1,-1,0);" % user_id)
            line_bot_api.reply_message(
                event.reply_token,
                    TextSendMessage('私は好きな範囲の数字をランダムに教えることができます。\n [ 0 ~ 999999999 ] \n\
                                    \n"ランダム"って言ってくれれば始めますので、まずは言ってみてください。\n\
                                    \n一度乱数を設定すると、\n"リセット"って言うまで数字を教えるので注意してください。\n\
                                    \n一度乱数を設定したら、スタンプを押すのがオススメです。\n\
                                    \nよろしくね。')
            )


# スタンプが来たとき
@handler.add(MessageEvent, message=StickerMessage)
def handle_sticker(event):
    user_id = str(event.source.user_id)
    result = do_sql_select("SELECT * FROM FlagTB WHERE userID='%s';" % user_id)
    if result:
        # データベースに登録されているユーザーならここに入る
        if result[0][3]:
            # rand_flagがTRUEのとき、乱数を生成してメッセージを送る
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(np.random.randint(result[0][5], result[0][4] + 1))
            )

        elif result[0][2]:
            # max_flagがTRUEのとき、最大値の設定を促す
            stamp_num = result[0][6]
            stamp_num += 1
            do_sql_other("UPDATE FlagTB SET stampNum=%d WHERE userID='%s';" % (stamp_num, user_id))
            if stamp_num > 10: # スタンプを連続で送っていきた回数でメッセージが変化する
                line_bot_api.reply_message(
                    event.reply_token, (
                        TextSendMessage('最大値を教えてくれずにスタンプばかり'),
                        TextSendMessage('これで%d個目です' % stamp_num)
                    )
                )
            else:
                line_bot_api.reply_message(
                    event.reply_token, (
                        TextSendMessage('ナイスなスタンプですね'),
                        TextSendMessage('でも今は最大値を教えて欲しいですね')
                    )
                )

        elif result[0][1]:
            # min_flagがTRUEのとき、最小値の設定を促す
            stamp_num = result[0][6]
            stamp_num += 1
            do_sql_other("UPDATE FlagTB SET stampNum=%d WHERE userID='%s';" % (stamp_num, user_id))
            if stamp_num > 10: # スタンプを連続で送っていきた回数でメッセージが変化する
                line_bot_api.reply_message(
                    event.reply_token, (
                        TextSendMessage('最小値を教えてくれずにスタンプばかり'),
                        TextSendMessage('これで%d個目です' % stamp_num)
                    )
                )
            else:
                line_bot_api.reply_message(
                    event.reply_token, (
                        TextSendMessage('ナイスなスタンプですね'),
                        TextSendMessage('でも今は最小値を教えて欲しいですね')
                    )
                )

        else:
            # 何のフラグもTRUEでない場合は'乱数'を促す
            stamp_num = result[0][6]
            stamp_num += 1
            do_sql_other("UPDATE FlagTB SET stampNum=%d WHERE userID='%s';" % (stamp_num, user_id))
            if stamp_num > 10:
                line_bot_api.reply_message(
                    event.reply_token, (
                        TextSendMessage('スタンプを%d個も送ってくれてますが' % stamp_num),
                        TextSendMessage('そんなことに意味はないので、"ランダム"って言ってください')
                    )
                )
            else:
                line_bot_api.reply_message(
                    event.reply_token, (
                        TextSendMessage('ナイスなスタンプですね'),
                        TextSendMessage('でも今は\n"ランダム"って言ってみませんか？')
                    )
                )

    else:
        # データベースの中にないユーザーは追加する
        do_sql_other("INSERT INTO FlagTB VALUES ('%s',FALSE,FALSE,FALSE,-1,-1,1);" % user_id)
        line_bot_api.reply_message(
            event.reply_token,
                TextSendMessage('私は好きな範囲の数字をランダムに教えることができます。\n [ 0 ~ 999999999 ] \n\
                                \n"ランダム"って言ってくれれば始めますので、まずは言ってみてください。\n\
                                \n一度乱数を設定すると、\n"リセット"って言うまで数字を教えるので注意してください。\n\
                                \n一度乱数を設定したら、スタンプを押すのがオススメです。\n\
                                \nよろしくね。')
        )


# 画像が来たとき
@handler.add(MessageEvent, message=ImageMessage)
def handle_image(event):
    # 画像が送られてきた場合はGoogle Cloud Vision APIで文字起こしを行う

    messageId = event.message.id

    # messageIdから画像のバイナリデータを取得
    message_content = line_bot_api.get_message_content(messageId)
    io_content = BytesIO(message_content.content)
    bytes_content = io_content.getvalue()

    # Google Cloud Visionを使用する
    client = vision.ImageAnnotatorClient()
    image = vision.Image(content=bytes_content)
    response = client.document_text_detection(image=image)

    # Google Cloud Visionからのレスポンスからテキスト部分を抜き取る
    text = response.full_text_annotation.text

    line_bot_api.reply_message(
        event.reply_token, (
            TextSendMessage('画像の文字起こしをしてみますね'),
            TextSendMessage('%s' % text)
        )
    )


if __name__ == "__main__":
    # app.run()
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
