import os
import cv2
import pathlib
import requests
from datetime import datetime

# 강의자료 ch08 p8~10 changedetection.py
# 강의 코드에서 바꾼 곳은 "# changed" 주석으로 이유를 적어둠
# 편의 기능 1(검출 상태 안정화)로 추가한 곳은 "# added (편의 기능 1)" 주석


class ChangeDetection:
    result_prev = []
    # changed: GitHub 레포가 공개라 비밀번호를 코드에 적지 않고 환경변수로 받음
    #          PHOTOBLOG_HOST를 안 주면 강의자료처럼 로컬 서버(127.0.0.1:8000)로 보냄
    HOST = os.environ.get('PHOTOBLOG_HOST', 'http://127.0.0.1:8000')
    username = os.environ.get('PHOTOBLOG_USER', 'cam01')
    password = os.environ.get('PHOTOBLOG_PASSWORD', '')
    token = ''
    title = ''
    text = ''

    # added (편의 기능 1): 검출 상태 안정화
    # 강의자료 p9 "모든 연산 프레임을 전송할 경우 서버 과부하, 과 검출" 문제를 줄이려고
    # 한두 프레임만 잡혔다 끊기는 검출은 무시하고, 몇 프레임 이어질 때만 0/1 상태를 바꿈
    APPEAR_FRAMES = 3       # 연속 3프레임(약 0.4초) 보여야 '나타남(1)'
    DISAPPEAR_FRAMES = 15   # 연속 15프레임(약 2초) 안 보여야 '사라짐(0)'
    STABLE = os.environ.get('PHOTOBLOG_STABLE', '1') != '0'   # PHOTOBLOG_STABLE=0 이면 강의자료 방식 그대로

    def __init__(self, names):
        self.result_prev = [0 for i in range(len(names))]
        # added (편의 기능 1): 클래스별 연속 검출/미검출 프레임 수와 안정화된 상태
        self.count_on = [0 for i in range(len(names))]
        self.count_off = [0 for i in range(len(names))]
        self.state = [0 for i in range(len(names))]

        res = requests.post(self.HOST + '/api-token-auth/', {
            'username': self.username,
            'password': self.password,
        })
        res.raise_for_status()
        self.token = res.json()['token']  # 토큰 저장
        # changed: 토큰 전체가 터미널 캡처에 찍히지 않게 앞부분만 출력
        print(self.token[:6] + '...')
        print('검출 상태 안정화 :', 'ON' if self.STABLE else 'OFF (강의자료 방식)')

    # added (편의 기능 1)
    def stabilize(self, detected_current):
        for i in range(len(detected_current)):
            if detected_current[i] == 1:
                self.count_on[i] += 1
                self.count_off[i] = 0
                if self.count_on[i] >= self.APPEAR_FRAMES:
                    self.state[i] = 1
            else:
                self.count_off[i] += 1
                self.count_on[i] = 0
                if self.count_off[i] >= self.DISAPPEAR_FRAMES:
                    self.state[i] = 0
        return self.state[:]

    def add(self, names, detected_current, save_dir, image):
        # added (편의 기능 1): 프레임 검출 결과 대신 안정화된 상태로 0 -> 1 변화를 판단
        if self.STABLE:
            detected_current = self.stabilize(detected_current)

        self.title = ''
        self.text = ''
        change_flag = 0  # 변화 감지 플래그
        i = 0
        while i < len(self.result_prev):
            if self.result_prev[i] == 0 and detected_current[i] == 1:
                change_flag = 1
                self.title = names[i]
                self.text += names[i] + ", "
            i += 1

        self.result_prev = detected_current[:]  # 객체 검출 상태 저장

        if change_flag == 1:
            self.send(save_dir, image)

    def send(self, save_dir, image):
        now = datetime.now()
        now.isoformat()

        today = datetime.now()
        save_path = os.getcwd() / save_dir / 'detected' / str(today.year) / str(today.month) / str(today.day)
        pathlib.Path(save_path).mkdir(parents=True, exist_ok=True)

        full_path = save_path / '{0}-{1}-{2}-{3}.jpg'.format(today.hour, today.minute, today.second, today.microsecond)

        # changed: 웹캠이 16:9라 320x240으로 바꾸면 사진이 세로로 늘어나서 가로 320은 그대로 두고 비율 유지
        h, w = image.shape[:2]
        dst = cv2.resize(image, dsize=(320, int(h * 320 / w)), interpolation=cv2.INTER_AREA)
        cv2.imwrite(full_path, dst)

        # 인증이 필요한 요청에 아래의 headers를 붙임
        headers = {'Authorization': 'JWT ' + self.token, 'Accept': 'application/json'}

        # Post Create
        data = {
            'title': self.title,
            'text': self.text,
            'created_date': now,
            'published_date': now
        }
        file = {'image': open(full_path, 'rb')}
        res = requests.post(self.HOST + '/api_root/Post/', data=data, files=file, headers=headers)
        print(res)
