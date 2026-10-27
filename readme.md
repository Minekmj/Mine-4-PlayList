<div align="center">

<img src="https://raw.githubusercontent.com/Minekmj/Mine-4-PlayList/refs/heads/main/src/icon/icon.png" width="128" height="128">

# Mine 4 PlayList

Windows용 감성 영상 플레이어입니다. 영상을 화려하게 볼 수 있습니다.\
주로 애니 OP, ED, MV를 보기 좋습니다.

<p>
  <a href="https://github.com/Minekmj/Mine-4-PlayList/releases/latest">
    <img src="https://img.shields.io/github/v/release/Minekmj/Mine-4-PlayList?display_name=tag&sort=date" alt="Latest Release">
  </a>

  <a href="https://github.com/Minekmj/Mine-4-PlayList/releases">
    <img src="https://img.shields.io/github/downloads/Minekmj/Mine-4-PlayList/total" alt="Downloads">
  </a>

  <a href="https://github.com/Minekmj/Mine-4-PlayList">
    <img src="https://img.shields.io/github/license/Minekmj/Mine-4-PlayList" alt="License">
  </a>

</p>

</div>

## 스크린샷

<div align="center">

<img width="500" alt="Image" src="https://github.com/user-attachments/assets/164abd65-ab12-43e3-9cd4-de540e228ddf" />

이미지 1

<img width="500" alt="Image" src="https://github.com/user-attachments/assets/f2d631c8-b90c-44ec-849e-fba80fee1069" />

이미지 2

<img width="500" alt="Image" src="https://github.com/user-attachments/assets/8b651910-e3cb-4dba-90dc-aef8eecf042d" />

이미지 3

<img width="500" alt="Image" src="https://github.com/user-attachments/assets/2e6629df-db72-4b63-b87c-eb15909be317" />

이미지 4

<img width="500" alt="Image" src="https://github.com/user-attachments/assets/4af37750-d5f8-47b4-95ef-70566400e9cf" />

이미지 5

<img width="500" alt="Image" src="https://github.com/user-attachments/assets/7b19291e-b1a5-4941-aeb3-64ec7a742a74" />

이미지 6

<img width="500" alt="Image" src="https://github.com/user-attachments/assets/c318fa33-13b7-4e4f-8e8c-f1079744dc2f" />

이미지 7

<img width="500" alt="Image" src="https://github.com/user-attachments/assets/416e006c-f7e8-4073-a005-1d8eabe5bfdf" />

가변 크기 이미지

<img width="500" alt="Image" src="https://github.com/user-attachments/assets/5c5dd178-62c0-4e79-87eb-42e767177692" />

전체 화면 이미지

<img width="500" alt="Image" src="https://github.com/user-attachments/assets/08741113-dc54-45c5-978a-07d01c3bc7c4" />

전체 화면 비교 (전체)

<img width="500" alt="Image" src="https://github.com/user-attachments/assets/bf43717b-8782-4940-bfa7-829a63ba5c1f" />

전체 화면 비교 (축소)

<img width="500"  alt="Image" src="https://github.com/user-attachments/assets/0ef85c05-36cc-4046-8dd8-5d6fbaab1111" />

미니멀 모드

<img width="500" alt="Image" src="https://github.com/user-attachments/assets/ede4af19-1462-4b95-959a-8bb5ceea0bb5" />

작동 이미지 1

<img width="500" alt="Image" src="https://github.com/user-attachments/assets/01a3fd24-d119-473f-abd9-fa3b225b84fe" />

작동 이미지 2

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