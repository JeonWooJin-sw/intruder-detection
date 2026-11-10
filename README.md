# Intruder Detection

2026-2 모바일/웹서비스 프로젝트 공통평가 02

웹캠 영상에서 YOLOv5로 물체를 검출하고, 새로 나타난 물체가 있으면 사진을 포토블로그 서버(Django)에 올린다.
안드로이드 앱(PhotoViewer)에서 서버에 올라온 감지 사진을 확인한다.

```
intruder-detection/
├── PhotoBlogServer/   Django 서버 (공통평가 01에서 가져옴)
├── PhotoViewer/       Android 클라이언트 (공통평가 01에서 가져옴)
├── YOLOv5/            Edge 클라이언트 (ultralytics/yolov5 + 변경 감지 코드)
└── 모바일웹서비스 프로젝트 공통평가 02_수행 결과 보고서_2023110399_전우진.docx
```

## YOLOv5 실행

```bash
cd YOLOv5
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

export PHOTOBLOG_PASSWORD=<cam01 비밀번호>
python detect.py --source 0      # 로컬 서버(127.0.0.1:8000)로 전송

export PHOTOBLOG_HOST=https://woojin123123.pythonanywhere.com
python detect.py --source 0      # PythonAnywhere로 전송
```

- 강의자료(ch08 p8~11)대로 추가/수정한 파일 : `YOLOv5/changedetection.py`, `YOLOv5/detect.py` (`# added by woojin` 표시)
- `--classes 39 41 67 73` : 책상 위 물체(bottle, cup, cell phone, book)만 검출 (YOLOv5 기본 옵션, 테스트할 때 사람은 올리지 않으려고 사용)
- `PHOTOBLOG_STABLE=0 python detect.py --source 0` : 편의 기능 1을 끄고 강의자료 방식 그대로 실행

## 편의 기능 (보고서 ID 10)

| ID | 기능 | 위치 |
|---|---|---|
| 10-1 | 검출 상태 안정화 : 연속 3프레임 보여야 출현, 연속 15프레임 안 보여야 사라짐으로 판단해서 같은 물체 글이 여러 번 올라가는 것을 막음 | `YOLOv5/changedetection.py` |
| 10-2 | 감지 기록 아카이브 (서버) : 날짜별·물체별 모아보기 `/archive/`, API `/api_root/archive/`, `/api_root/Post/?date=YYYY-MM-DD&title=물체` | `PhotoBlogServer/blog/` |
| 10-3 | 감지 기록 (앱) : ⋮ → 감지 기록 → 날짜 → 물체를 고르면 그 기록만 목록에 표시 | `PhotoViewer/` |

```bash
cd YOLOv5
coverage run --include=changedetection.py -m unittest test_changedetection -v   # 편의 기능 1 테스트 10개
coverage report -m
```

- 서버 실행/테스트 : [PhotoBlogServer/README.md](PhotoBlogServer/README.md)
- 앱 : [PhotoViewer/README.md](PhotoViewer/README.md)
- 배포 주소 : https://woojin123123.pythonanywhere.com
