<div align="center">

<img src="https://raw.githubusercontent.com/Minekmj/Mine-4-PlayList/refs/heads/main/src/icon/icon.png" width="128" height="128">

# Mine 4 PlayList

Windows용 감성 영상 플레이어입니다. 영상을 화려하게 볼 수 있습니다.\
주로 애니 OP, ED, MV를 보기 좋습니다.

</div>

## 스크린샷

<div align="center">

<div style="border-radius: 10px; overflow: hidden; max-width: 500px;">
  <img alt="Image" src="https://github.com/user-attachments/assets/e41f24d3-995d-45b9-b14a-1dc133e4fff3" style="width: 100%; display: block;" />
</div>

이미지 1

<div style="border-radius: 10px; overflow: hidden; max-width: 500px;">
  <img alt="Image" src="https://github.com/user-attachments/assets/5ace0061-a38f-4ec4-8e5b-eae42328b250" style="width: 100%; display: block;" />
</div>

이미지 2

<div style="border-radius: 10px; overflow: hidden; max-width: 500px;">
  <img alt="Image" src="https://github.com/user-attachments/assets/146c2043-553f-4460-8160-b4eb19d3a3c0" style="width: 100%; display: block;" />
</div>

이미지 3

<div style="border-radius: 10px; overflow: hidden; max-width: 500px;">
  <img alt="Image" src="https://github.com/user-attachments/assets/62a2e96a-16c9-436f-bdfa-86bb16774ff9" style="width: 100%; display: block;" />
</div>

이미지 4

<div style="border-radius: 10px; overflow: hidden; max-width: 500px;">
  <img alt="Image" src="https://github.com/user-attachments/assets/441c4984-bfc3-4c04-b507-2a73187cbc9f" style="width: 100%; display: block;" />
</div>

가변 크기 이미지

<div style="border-radius: 10px; overflow: hidden; max-width: 500px;">
  <img alt="Image" src="https://github.com/user-attachments/assets/db9675a9-0dfb-4f46-a2ed-7afb031ea9f3" style="width: 100%; display: block;" />
</div>

플레이리스트 숨기기 이미지 1

<div style="border-radius: 10px; overflow: hidden; max-width: 500px;">
  <img alt="Image" src="https://github.com/user-attachments/assets/61a71958-5b8a-4c94-a193-eb8a6d1c03b7" style="width: 100%; display: block;" />
</div>

플레이리스트 숨기기 이미지 2

<div style="border-radius: 20px; overflow: hidden; max-width: 500px;">
  <img alt="Image" src="https://github.com/user-attachments/assets/9b69ed2e-de4c-480d-aa59-40e5a49bd293" style="width: 100%; display: block;" />
</div>

미니멀 모드

</div>

## 주요 기능

### 1. 비주얼 & 감성 UI
- **실시간 주변광**: 영상 프레임 색상을 분석하여 배경으로 자연스럽게 번져나가는 조명 효과
- **배경 이펙트 시스템**: 오로라 웨이브, 부유 파티클, 스크린 테두리 지원
- **글래스모피즘 인터페이스**: 반투명 프로스티드 글래스 패널 기반의 미니멀 UI
- **둥근 모서리**: 둥근 모서리로 한층더 예쁘게

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