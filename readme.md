<div align="center">

<img src="https://raw.githubusercontent.com/Minekmj/Mine-4-PlayList/refs/heads/main/src/icon/icon.png" width="128" height="128">

# Mine 4 PlayList

Windows용 영상·음악 플레이어입니다. 영상을 화려하게 볼 수 있습니다(?)

</div>

## 스크린샷

<img width="1300" height="820" alt="Image" src="https://github.com/user-attachments/assets/41341319-a135-4c25-8c20-9e13998e3a5b" />

<img width="1300" height="820" alt="Image" src="https://github.com/user-attachments/assets/b67deec6-f9bf-4442-a805-a0b1c7936f73" />

<img width="1300" height="820" alt="Image" src="https://github.com/user-attachments/assets/f2f592d4-1454-4c6a-8b4d-8c243286a9a7" />

<img width="1300" height="820" alt="Image" src="https://github.com/user-attachments/assets/17908f91-4943-41d8-8e75-5653bce874f9" />

## 주요 기능

### 1. 비주얼 & 감성 UI
- **실시간 주변광**: 영상 프레임 색상을 분석하여 배경으로 자연스럽게 번져나가는 조명 효과
- **배경 이펙트 시스템**: 오로라 웨이브, 부유 파티클, 스크린 테두리 지원
- **글래스모피즘 인터페이스**: 반투명 프로스티드 글래스 패널 기반의 미니멀 UI

### 2. 재생 및 미디어 제어
- **음량 자동 평준화**: 영상/음원마다 들쭉날쭉한 볼륨 편차를 자동으로 보정
- **세션 자동 저장**: 마지막 재생 위치, 플레이리스트, 볼륨 및 모드 상태 자동 복구

### 3. 미니멀 모드
- 작업 중 화면 구석에 띄워둘 수 있는 컴팩트 위젯 모드

### 4. 자막 & 편의 기능
- **자막 렌더링**: 전용 자막 기능 지원
- **YouTube 스트리밍/다운로드**: 영상 URL 입력 시 자동 다운로드 및 자막 한국어 번역 연동


## 설치 및 실행

### 방법 1

1. [최신 릴리스(Releases)](https://github.com/Minekmj/Mine-4-PlayList/releases) 페이지에서 최신 `.zip` 파일을 다운로드합니다.
2. 압축을 푼 뒤 폴더 안의 `Mine 4 PlayList.exe`를 실행합니다.
3. 추후 새 버전 업데이트는 폴더 내부의 `updater.exe`를 실행하면 자동으로 진행됩니다.

### 방법 2. 소스코드 직접 실행 (Python 3.10+)

1. **저장소 클론 및 패키지 설치**
   ```bash
   git clone https://github.com/Minekmj/Mine-4-PlayList.git
   cd Mine-4-PlayList
   pip install -r requirements.txt
   ```

3. **실행**
   ```bash
   python main.py
   ```