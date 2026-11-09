"""changedetection.py 단위 테스트 (편의 기능 1: 검출 상태 안정화)

실행 : python -m unittest test_changedetection -v
커버리지 : coverage run --include=changedetection.py -m unittest test_changedetection
          coverage report -m
서버나 웹캠 없이 돌아가도록 requests.post 는 mock 으로 바꿔서 시험함
"""
import io
import os
import pathlib
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest import mock

import cv2
import numpy as np

from changedetection import ChangeDetection

NAMES = {0: 'person', 41: 'cup', 67: 'cell phone'}
NAMES = {i: NAMES.get(i, 'class%d' % i) for i in range(80)}   # yolov5 처럼 0~79 dict
CUP, PHONE = 41, 67


def frame(*classes):
    detected = [0 for i in range(len(NAMES))]
    for c in classes:
        detected[c] = 1
    return detected


def token_response():
    res = mock.Mock()
    res.json.return_value = {'token': 'abcdef123456'}
    return res


class ChangeDetectionTest(unittest.TestCase):
    def setUp(self):
        with mock.patch('changedetection.requests.post', return_value=token_response()) as post, \
                redirect_stdout(io.StringIO()):   # 토큰 출력은 화면에 안 찍히게
            self.cd = ChangeDetection(NAMES)
        self.token_call = post.call_args
        self.sent = []   # send() 대신 보낸 글 제목만 기록
        self.cd.send = lambda save_dir, image: self.sent.append((self.cd.title, self.cd.text))

    def run_frames(self, frames, stable):
        self.cd.STABLE = stable
        for f in frames:
            self.cd.add(NAMES, f, pathlib.Path('runs'), None)
        return [title for title, text in self.sent]

    # ---------- 토큰 ----------
    def test_token_request(self):
        args, kwargs = self.token_call
        self.assertTrue(args[0].endswith('/api-token-auth/'))
        self.assertEqual(args[1]['username'], self.cd.username)
        self.assertEqual(self.cd.token, 'abcdef123456')

    # ---------- 강의자료 방식 (안정화 OFF) ----------
    def test_lecture_mode_sends_again_after_one_frame_flicker(self):
        # 컵이 한 프레임만 안 잡혀도 0 -> 1 이 다시 생겨서 같은 컵이 두 번 올라감
        sent = self.run_frames([frame(CUP), frame(), frame(CUP)], stable=False)
        self.assertEqual(sent, ['cup', 'cup'])

    def test_lecture_mode_sends_one_frame_false_detection(self):
        sent = self.run_frames([frame(PHONE), frame()], stable=False)
        self.assertEqual(sent, ['cell phone'])

    # ---------- 안정화 ON ----------
    def test_stable_mode_ignores_flicker(self):
        frames = [frame(CUP)] * 3 + [frame()] * 2 + [frame(CUP)] * 3
        sent = self.run_frames(frames, stable=True)
        self.assertEqual(sent, ['cup'])

    def test_stable_mode_ignores_short_false_detection(self):
        # 1~2 프레임만 잡힌 휴대폰(오검출)은 올리지 않음
        frames = [frame(PHONE), frame(), frame(PHONE), frame(PHONE), frame()]
        sent = self.run_frames(frames, stable=True)
        self.assertEqual(sent, [])

    def test_stable_mode_waits_appear_frames(self):
        sent = self.run_frames([frame(CUP)] * 2, stable=True)
        self.assertEqual(sent, [])
        sent = self.run_frames([frame(CUP)], stable=True)
        self.assertEqual(sent, ['cup'])

    def test_stable_mode_sends_again_after_really_gone(self):
        frames = [frame(CUP)] * 3 + [frame()] * 15 + [frame(CUP)] * 3
        sent = self.run_frames(frames, stable=True)
        self.assertEqual(sent, ['cup', 'cup'])

    def test_stable_mode_not_gone_before_disappear_frames(self):
        frames = [frame(CUP)] * 3 + [frame()] * 14 + [frame(CUP)] * 3
        sent = self.run_frames(frames, stable=True)
        self.assertEqual(sent, ['cup'])

    def test_two_objects_appear_together(self):
        self.run_frames([frame(CUP, PHONE)] * 3, stable=True)
        self.assertEqual(self.sent, [('cell phone', 'cup, cell phone, ')])


class SendTest(unittest.TestCase):
    def setUp(self):
        with mock.patch('changedetection.requests.post', return_value=token_response()), \
                redirect_stdout(io.StringIO()):
            self.cd = ChangeDetection(NAMES)
        self.cd.title, self.cd.text = 'cup', 'cup, '
        self.old_cwd = os.getcwd()
        self.tmp = tempfile.TemporaryDirectory()
        os.chdir(self.tmp.name)

    def tearDown(self):
        os.chdir(self.old_cwd)
        self.tmp.cleanup()

    def test_send_saves_image_and_posts_with_jwt(self):
        image = np.zeros((1080, 1920, 3), dtype=np.uint8)   # 16:9 웹캠 프레임
        res = mock.Mock(status_code=201)
        with mock.patch('changedetection.requests.post', return_value=res) as post, \
                redirect_stdout(io.StringIO()):
            self.cd.send(pathlib.Path('runs/detect/exp'), image)

        saved = list(pathlib.Path('runs/detect/exp/detected').rglob('*.jpg'))
        self.assertEqual(len(saved), 1)
        self.assertEqual(cv2.imread(str(saved[0])).shape[:2], (180, 320))   # 가로 320, 비율 유지

        args, kwargs = post.call_args
        self.assertTrue(args[0].endswith('/api_root/Post/'))
        self.assertEqual(kwargs['headers']['Authorization'], 'JWT abcdef123456')
        self.assertEqual(kwargs['data']['title'], 'cup')
        self.assertEqual(kwargs['data']['text'], 'cup, ')
        self.assertIn('image', kwargs['files'])
        kwargs['files']['image'].close()


if __name__ == '__main__':
    unittest.main()
