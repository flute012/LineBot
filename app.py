from flask import Flask, request, abort

from linebot.v3 import (
    WebhookHandler
)
from linebot.v3.exceptions import (
    InvalidSignatureError
)
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
    StickerMessage,
    LocationMessage,
    ImageMessage,
    VideoMessage,
    AudioMessage,
)

from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent,
    StickerMessageContent,
    LocationMessageContent,
    ImageMessageContent,  # 從 webhooks 導入
)

from modules.reply import faq, menu
    
import os

from openai import OpenAI
from dotenv import load_dotenv

running_on_render = os.getenv("RENDER") 
print("現在是在Render上運行嗎?",running_on_render)

#如果不在render上運行，則載入環境變數

if not running_on_render:
    # 載入環境變數
    from dotenv import load_dotenv
    load_dotenv()
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

app = Flask(__name__)
# Line Channel 可於 Line Developer Console 申辦
# https://developers.line.biz/en/

# TODO: 填入你的 CHANNEL_SECRET 與 CHANNEL_ACCESS_TOKEN
CHANNEL_SECRET = os.getenv("CHANNEL_SECRET")
CHANNEL_ACCESS_TOKEN = os.getenv("CHANNEL_ACCESS_TOKEN")

handler = WebhookHandler(CHANNEL_SECRET)
configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)

# @app.route() 用以表達伺服器應用程式路由將會對應到 webhooks 的路徑中
@app.route("/", methods=['POST'])
def callback():
    # ====== 以下為接收並驗證 Line Server 傳來訊息的流程，不需更動 ======
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']
    # get request body as text
    body = request.get_data(as_text=True)
    # app.logger.info("Request body: " + body)
    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.info("signature驗證錯誤，請檢查Secret與Access Token是否正確...")
        abort(400)
    return 'OK'

# 此處理器負責處理接收到Line Server傳來的文字訊息時的流程
@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    with ApiClient(configuration) as api_client:
        # 當使用者傳入文字訊息時
        print("#" * 30)
        line_bot_api = MessagingApi(api_client)
        # event 為 Line Server 傳來的事件物件所有關於一筆訊息的資料皆可從中取得
        # print("event 一個Line文件訊息的事件物件:", event)
        # 在此的 evnet.message.text 即是 Line Server 取得的使用者文字訊息
        user_msg = event.message.text
        print("使用者傳入的文字訊息是:", user_msg)
        # 使用TextMessage產生一段用於回應使用者的Line文字訊息
        bot_msg = TextMessage(text=f"你剛才說的是: {user_msg}, Hello!")


        if user_msg in faq:
            bot_msg = faq[user_msg]
        elif user_msg.lower() in ["menu","選單","主選單"]: 
            bot_msg = menu
        else:
            #如果不是選單的問題，由opai回答
            # TODO: 將使用者的問題由openai回答
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "user", 
                    "content": "請用繁體中文回答"},

                    {"role": "system", 
                    "content": user_msg}
                ]
            )
            bot_msg = TextMessage(text=response.choices[0].message.content)

            print(response.output_text)


        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                # 放置於 ReplyMessageRequest 的 messages 裡的物件即是要回傳給使用者的訊息
                # 必須注意由於 Line 有其使用的內部格式
                # 因此要回覆的訊息務必使用 Line 官方提供的類別來產生回應物件
                messages=[
                    # 要回應的內容放在這個串列中
                    bot_msg, 
                    TextMessage(text="請輸入menu查看選單"),                  
                ]
            )
        )

# 此處理器負責處理接收到Line Server傳來的貼圖訊息時的流程
@handler.add(MessageEvent, message=StickerMessageContent)
def handle_sticker_message(event):
    with ApiClient(configuration) as api_client:
        # 當使用者傳入貼圖時
        line_bot_api = MessagingApi(api_client)
        sticker_id = event.message.sticker_id
        package_id = event.message.package_id
        keywords_msg = "這張貼圖背後沒有關鍵字"
        if len(event.message.keywords) > 0:
            keywords_msg = "這張貼圖的關鍵字有:"
            keywords_msg += ", ".join(event.message.keywords)
        # 可以使用的貼圖清單
        # https://developers.line.biz/en/docs/messaging-api/sticker-list/
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[
                    StickerMessage(package_id="2", sticker_id="145"),
                    TextMessage(text=f"你剛才傳入了一張貼圖，以下是這張貼圖的資訊:"),
                    TextMessage(text=f"貼圖包ID為 {package_id} ，貼圖ID為 {sticker_id} 。"),
                    TextMessage(text=keywords_msg),
                ]
            )
        )

# 此處理器負責處理接收到Line Server傳來的地理位置訊息時的流程
@handler.add(MessageEvent, message=LocationMessageContent)
def handle_location_message(event):
    with ApiClient(configuration) as api_client:
        # 當使用者傳入地理位置時
        line_bot_api = MessagingApi(api_client)
        latitude = event.message.latitude
        longitude = event.message.longitude
        address = event.message.address
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[
                    TextMessage(text=f"You just sent a location message."),
                    TextMessage(text=f"The latitude is {latitude}."),
                    TextMessage(text=f"The longitude is {longitude}."),
                    TextMessage(text=f"The address is {address}."),
                    LocationMessage(title="Here is the location you sent.", address=address, latitude=latitude, longitude=longitude)
                ]
            )
        )

@handler.add(MessageEvent, message=ImageMessageContent)
def handle_image_message(event):
    with ApiClient(configuration) as api_client:
        import requests
        import base64
        
        line_bot_api = MessagingApi(api_client)
        message_id = event.message.id
        print("收到圖片，訊息ID:", message_id)
        
        # 使用 requests 獲取圖片內容
        url = f"https://api-data.line.me/v2/bot/message/{message_id}/content"
        headers = {
            "Authorization": f"Bearer {CHANNEL_ACCESS_TOKEN}"
        }
        response = requests.get(url, headers=headers)
        
        # 將圖片內容轉換為 base64 並發送給 OpenAI
        if response.status_code == 200:
            image_base64 = base64.b64encode(response.content).decode('utf-8')
            
            try:
                # 使用 OpenAI 分析圖片
                vision_response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": "請用繁體中文描述這張圖片的內容，如果收到的圖片是食物，請根據此食物的成分，給出進行營養素分析，並且給出適當的回應"
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{image_base64}"
                                    }
                                }
                            ]
                        }
                    ],
                    max_tokens=500
                )
                
                # 獲取 AI 的描述並回覆
                image_description = vision_response.choices[0].message.content
                
                # 回覆給使用者
                line_bot_api.reply_message_with_http_info(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[
                            TextMessage(text="以下是這張圖片的描述："),
                            TextMessage(text=image_description)
                        ]
                    )
                )
            except Exception as e:
                print("OpenAI API 錯誤:", str(e))
                line_bot_api.reply_message_with_http_info(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[
                            TextMessage(text="抱歉，圖片分析發生錯誤，請稍後再試。")
                        ]
                    )
                )
        
        # 當使用者傳入圖片時
        print("event 一個Line圖片訊息的事件物件:", event.message.id)
        message_id = event.message.id
        content_type = event.message.content_type
        line_bot_api = MessagingApi(api_client)
        # 取得圖片的資訊
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[
                    TextMessage(text=f"You just sent an image message."),
                    TextMessage(text=f"The image message id is {event.message.id}."),
                    TextMessage(text=f"The image message content type is {event.message.content_type}."),
                ]
            )
        )

# 如果應用程式被執行執行
if __name__ == "__main__":
    print("[伺服器應用程式開始運行]")
    # 取得遠端環境使用的連接端口，若是在本機端測試則預設開啟於port=5001
    port = int(os.environ.get('PORT', 5001))
    print(f"[Flask即將運行於連接端口:{port}]")
    print(f"若在本地測試請輸入指令開啟測試通道: ./ngrok http {port} ")
    # 啟動應用程式
    # 本機測試ngrok使用127.0.0.1, debug=True
    # Render 部署使用 0.0.0.0
    app.run(host="0.0.0.0", port=port, debug=True)
