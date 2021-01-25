# -*- coding: utf-8 -*-

import json
from flask import Flask, request, make_response
from slacker import Slacker
import requests
from bs4 import BeautifulSoup
import time
import logging

token = ""  # 봇 토큰
url = "https://www.sedaily.com/Stock/Quote?type=1"

logging.basicConfig(filename=time.strftime('%Y-%m-%d', time.localtime(time.time())) + "slack_log.log",
                    level=logging.DEBUG)

app = Flask(__name__)
slack = Slacker(token)


answer_dict = {}
mx = 0


def event_handler(event_type, slack_event):
    global mx
    channel = slack_event["event"]["channel"]

    string_slack_event = str(slack_event)
    if string_slack_event.find("'type': 'message', 'text': '<@") != -1:  # 멘션으로 호출
        try:
            user_query = slack_event['event']['blocks'][0]['elements'][0]['elements'][1]['text']

            # 주식 실시간 정보 가져오기
            html = requests.get(url)
            stock_dict = {}
            soup = BeautifulSoup(html.text, "html.parser")
            all_table = soup.find_all('div', {'class': 'table'})

            for thead in all_table:
                dl = thead.find('dl', {'class': 'thead'})
                dt = dl.find('dt')
                field_name = dt.text  # fieldName 업종 (18개의 thead로 나누어져있다)
                tbody = thead.find_all('dl', {'class': 'tbody'})

                for dl in tbody:  # 세부종목 for loop
                    name = dl.find('dt').get_text()  # 종목명
                    dd = dl.find('dd')
                    code = dd.get('id').replace('dd_Item_', '')  # 종목코드
                    price = dd.find('span').get_text().replace(',', '')  # 가격
                    stock_dict[name] = [code, field_name, price]

            try:
                user_query = user_query.replace(" ", "")
                out = stock_dict[user_query]

            except KeyError:
                slack.chat.post_message(channel, "찾지 못했어요")
                return make_response("ok", 200, )

            slack.chat.post_message(channel, ''
                                    + "\n이름\t" + user_query
                                    + "\ncode\t" + out[0]
                                    + "\n종목\t" + out[1]
                                    + "\n가격\t" + out[2]
                                    + "원\n5초 뒤에 다음 명령을 해주세요")
            return make_response("ok", 200, {"X-Slack-No-Retry": 1})

        except IndexError:
            pass

    message = "[%s] cannot find event handler" % event_type

    return make_response(message, 200, {"X-Slack-No-Retry": 1})


@app.route('/', methods=['POST'])
def slack_server():
    print(request.environ.get('HTTP_X_REAL_IP', request.remote_addr), end="\t")
    print(request.environ.get('SERVER_PROTOCOL'))
    slack_event = json.loads(request.data)

    if "challenge" in slack_event:
        return make_response(slack_event["challenge"], 200, {"content_type": "application/json"})

    if "event" in slack_event:
        event_type = slack_event["event"]["type"]
        return event_handler(event_type, slack_event)

    return make_response("There are no slack request events", 404, {"X-Slack-No-Retry": 1})


if __name__ == '__main__':
    app.run(debug=True, port=5000, host="0.0.0.0")
