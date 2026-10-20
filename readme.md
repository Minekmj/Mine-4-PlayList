<div align="center">

<img src="https://raw.githubusercontent.com/Minekmj/Mine-4-PlayList/refs/heads/main/src/icon/icon.png" width="128" height="128">

# Mine 4 PlayList

Windows용 영상·음악 플레이어입니다. 영상을 화려하게 볼 수 있습니다(?)

</div>

## 주요 기능

- MP4, MKV, AVI, MOV, WebM 영상 및 MP3, FLAC, WAV 오디오 재생
- 재생목록과 마지막 재생 상태 저장
- SMI, SRT, VTT 자막 표시 및 자막 스타일·애니메이션 설정
- YouTube 영상 다운로드 및 사용 가능한 자막의 한국어 번역
- 오로라, 파티클, 주변광 효과 설정
- 볼륨 자동 보정

## 스크린샷

<img width="1300" height="820" alt="Image" src="https://github.com/user-attachments/assets/41341319-a135-4c25-8c20-9e13998e3a5b" />

<img width="1300" height="820" alt="Image" src="https://github.com/user-attachments/assets/b67deec6-f9bf-4442-a805-a0b1c7936f73" />

<img width="1300" height="820" alt="Image" src="https://github.com/user-attachments/assets/f2f592d4-1454-4c6a-8b4d-8c243286a9a7" />

<img width="1300" height="820" alt="Image" src="https://github.com/user-attachments/assets/17908f91-4943-41d8-8e75-5653bce874f9" />

## 실행 방법 1

1. 최신 릴리스에서 `.zip` 파일을 다운로드합니다. [최신 릴리스](https://github.com/Minekmj/Mine-4-PlayList/releases) <-링크 바로가기
2. 다운로드한 파일을 압축해제합니다.
3. 폴더 내부에 있는 `Mine 4 PlayList.exe`를 실행합니다.

## 실행 방법 2

Python 3.10 이상과 Windows 환경을 기준으로 합니다.

1. 저장소를 내려받고 프로젝트 폴더에서 터미널을 엽니다.
2. 필요한 패키지를 설치합니다.

   ```bash
   pip install -r requirements.txt
   ```

3. 프로그램을 실행합니다.

   ```bash
   python main.py
   ```

## 사용법

- 파일이나 폴더를 재생목록에 끌어 놓거나 파일 추가 메뉴를 이용하세요.
- 재생목록 항목을 두 번 클릭하면 해당 파일이 재생됩니다.
- 항목을 끌어 놓아 재생 순서를 바꿀 수 있습니다.
- 항목을 마우스 오른쪽 버튼으로 클릭하면 자막 연결이나 목록에서 삭제 등의 메뉴가 표시됩니다.
- YouTube 다운로드 기능에서 영상 URL을 입력하면 다운로드를 시작합니다.
- 설정 창에서 자막 모양, 배경 효과, 재생 엔진 옵션을 변경할 수 있습니다.

### 키보드 단축키

| 키 | 기능 |
| --- | --- |
| `Space` | 재생 / 일시 정지 |
| `↑` / `↓` | 볼륨 높이기 / 낮추기 |
| `F` | 전체 화면 전환 |
| `L` | 재생목록 표시 / 숨기기 |
| `M` | 음소거 전환 |
| `V` | 자막 표시 / 숨기기 |
| `Esc` | 전체 화면 종료 |

## EXE 빌드

프로젝트 폴더에서 `build.bat`을 실행하면 PyInstaller로 실행 파일을 빌드합니다. 빌드에 필요한 패키지가 설치되어 있어야 합니다.

```bash
pip install pyinstaller
build.bat
```

## 참고

- YouTube 다운로드와 자막 가져오기는 외부 서비스의 정책이나 제공 상태에 따라 동작하지 않을 수 있습니다.
- 자막 번역은 영상에 번역 가능한 공식 자막이 있을 때 시도됩니다.
- 재생목록과 설정 상태는 실행 폴더의 `session_state.json`에 저장됩니다.
