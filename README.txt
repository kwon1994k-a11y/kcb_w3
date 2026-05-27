# Google Sheets 연동 Streamlit 앱

## 1. 설치

```bash
pip install -r requirements.txt
```

## 2. Google Cloud 설정

1. Google Cloud Console 접속
2. 새 프로젝트 생성
3. Google Sheets API 사용 설정
4. Google Drive API 사용 설정
5. 서비스 계정 생성
6. 서비스 계정 JSON 키 다운로드

## 3. Google Sheets 만들기

구글 스프레드시트 새로 만들기

예시 이름:

```text
경마&경륜&경정_분석표
```

서비스 계정 이메일을 구글 시트에 공유해야 합니다.

예시:

```text
xxxxx@xxxxx.iam.gserviceaccount.com
```

권한은 편집자로 설정하세요.

## 4. 로컬 secrets.toml 설정

프로젝트 안에 아래 폴더와 파일을 만듭니다.

```text
my_project_google_sheets/
├── app.py
├── database.py
├── requirements.txt
└── .streamlit/
    └── secrets.toml
```

`secrets_example.toml` 내용을 복사해서 `.streamlit/secrets.toml` 로 저장한 뒤,
서비스 계정 JSON 내용을 붙여넣으세요.

## 5. 실행

```bash
streamlit run app.py
```

## 6. 관리자 비밀번호 변경

관리자 비밀번호는 `app.py`에 적지 말고 Streamlit Cloud의 Secrets에 추가하세요.

```toml
admin_password = "새로운_관리자_비밀번호"
```

## 7. Streamlit Cloud 배포

GitHub에 아래 3개 파일을 올립니다.

```text
app.py
database.py
requirements.txt
```

주의: `.streamlit/secrets.toml` 은 GitHub에 올리지 마세요.

Streamlit Cloud 앱 설정의 Secrets 메뉴에 `secrets.toml` 내용을 그대로 붙여넣으면 됩니다.

반드시 `admin_password`는 새 비밀번호로 설정하세요. 코드에 직접 입력한 비밀번호는 GitHub에 공개될 수 있습니다.

## 저장 구조

Google Sheets 안에 자동으로 아래 시트가 생성됩니다.

- posts
- images
- excel_data
- keirin_pattern_db

이미지는 Google Sheets 셀에 Base64 문자열로 저장됩니다.
이미지가 너무 크면 시트가 무거워질 수 있으니 작은 이미지 사용을 추천합니다.

## 경륜 현장예측 사용 방법

### 최초 db 등록

1. 앱 왼쪽 메뉴에서 `관리자 업로드`를 선택합니다.
2. 관리자 비밀번호를 입력합니다.
3. `현장예측 db 등록`에서 엑셀 파일을 선택합니다.
4. 업로드 파일은 `db` 시트에 아래 열을 포함해야 합니다.

```text
no, a1, a2, a3, a4, a5, n1, n2, n3
```

5. `현장예측 db 저장`을 누르면 Google Sheets의 `keirin_pattern_db` 시트에 저장됩니다.

### 스마트폰에서 예측

1. 스마트폰 브라우저에서 Streamlit 앱 주소를 엽니다.
2. `경륜 현장예측` 메뉴를 선택합니다.
3. 현장 배당률 기준 인기순위 1~5위 선수 번호를 순서대로 입력합니다.

```text
4,7,2,1,5
```

4. `예측 결과 보기`를 누르면 과거 db의 실제 `n1~n3` 조합 상위 3개와 확률이 표시됩니다.

예측 원리:

- 같은 `a1~a5` 조합이 과거 db에 있으면 해당 조합에서 실제로 발생한 `n1~n3` 빈도를 사용합니다.
- 같은 조합이 없으면 `a1~a5` 위치와 선수 번호 구성이 비슷한 과거 조합의 결과 패턴을 가중 집계합니다.

### 휴대폰 홈 화면에 앱처럼 추가

- Android Chrome: 앱 주소 접속 후 메뉴에서 `홈 화면에 추가`
- iPhone Safari: 공유 버튼을 누른 뒤 `홈 화면에 추가`

별도의 Python 앱을 스마트폰에 설치할 필요는 없습니다.
