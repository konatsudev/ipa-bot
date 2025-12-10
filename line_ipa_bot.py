from flask import Flask, request, Response
import os
import unicodedata
import re

# ===== LINE Messaging API v3 =====
from linebot.v3.webhook import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from linebot.v3.messaging import (
    Configuration, ApiClient, MessagingApi,
    ReplyMessageRequest, TextMessage as V3TextMessage,
)

# 環境変数があればそちらを優先（無ければデフォルト値）
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get(
    "CHANNEL_ACCESS_TOKEN",
    "h8LgfjKtkxVVX+UPgYRZmeKoG0tZswRrXlBQ5FtfaEVCze4PTb2XAKXzeVXrPLtKjBf0lRvqDmNZ7FDal8A1+ebZEMx32XlbvSHXynoSDs5vqDfv2KJW291+vHwCzW2rynVoIPxz4QjQOnGsch7aNQdB04t89/1O/w1cDnyilFU=",
)
LINE_CHANNEL_SECRET = os.environ.get(
    "CHANNEL_SECRET",
    "178ead2cbe1ae680654c88c938469e99",
)

handler = WebhookHandler(LINE_CHANNEL_SECRET)
messaging_api = MessagingApi(
    ApiClient(Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN))
)

# ===== IPA リンク（これだけ配布） =====
MEDIAFIRE_IPA_URL = "https://app.mediafire.com/folder/w9n4pf7gkmk9w"

app = Flask(__name__)


# ===== ヘルスチェック用 =====
@app.route("/", methods=["GET"])
def index():
    return Response("OK", mimetype="text/plain; charset=utf-8")


# ===== IPA を返す HTTP エンドポイント（任意） =====
@app.route("/ipa", methods=["GET"])
def http_ipa():
    return Response(MEDIAFIRE_IPA_URL, mimetype="text/plain; charset=utf-8")


# ===== LINE Webhook エンドポイント =====
@app.route("/callback", methods=["POST"])
def callback():
    # LINE から送られてくる署名
    signature = request.headers.get("X-Line-Signature", "")
    # リクエストボディ（JSON文字列）
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        # 署名が合わないときは 400 を返す
        return "Bad signature", 400
    except Exception:
        # それ以外のエラーも 400 で返しておく
        return "Error", 400

    return "OK"


# ===== メッセージ受信ハンドラ =====
@handler.add(MessageEvent, message=TextMessageContent)
def on_text(event: MessageEvent):
    # テキストを取得（スタンプなどはここに来ない）
    msg = event.message
    raw_text = (getattr(msg, "text", "") or "").strip()

    # 全角/半角を正規化してから小文字に
    text = unicodedata.normalize("NFKC", raw_text)
    text_lower = text.lower()

    # 英数字のかたまりの中の "ipa" を除外するため、
    # 「前後が英数字ではない ipa」だけを拾う
    # 例:
    #   "ipa"       → マッチ
    #   "ipa!"      → マッチ
    #   " ipa "     → マッチ
    #   "ipa3"      → マッチしない
    #   "ipad"      → マッチしない
    #   "xipa9"     → マッチしない
    pattern = r'(?<![0-9a-z])ipa(?![0-9a-z])'

    if not re.search(pattern, text_lower):
        # 条件に合う ipa が無ければ完全スルー
        return

    # 条件に合う ipa が含まれていれば必ず IPA URL を返信
    reply = MEDIAFIRE_IPA_URL

    try:
        messaging_api.reply_message(
            ReplyMessageRequest(
                replyToken=event.reply_token,
                messages=[V3TextMessage(text=reply)],
            )
        )
    except Exception:
        # 返信に失敗してもここでは黙って無視
        pass


if __name__ == "__main__":
    # ローカル実行（ngrok 等で /callback を公開）
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)
