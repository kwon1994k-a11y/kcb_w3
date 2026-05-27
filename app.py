import pandas as pd
import streamlit as st

from database import (
    init_db,
    save_post,
    save_image,
    save_excel,
    load_posts,
    load_images,
    load_excel_data,
    load_keirin_pattern_db,
    save_keirin_pattern_db,
    base64_to_bytes,
)
from keirin_predictor import predict_from_popularity


st.set_page_config(
    page_title="경마&경륜&경정_분석표",
    layout="wide"
)

ADMIN_PASSWORD = st.secrets.get("admin_password")


try:
    init_db()
except Exception as e:
    st.error("Google Sheets 연결에 실패했습니다.")
    st.warning("`.streamlit/secrets.toml` 또는 Streamlit Cloud Secrets 설정을 확인하세요.")
    st.code(str(e))
    st.stop()


def show_category_page(menu_name: str, category: str):
    st.title(f"{menu_name} 분석표")

    tab1, tab2, tab3 = st.tabs(["📝 게시글", "🖼️ 이미지", "📊 엑셀표"])

    with tab1:
        posts = load_posts(category)

        if posts.empty:
            st.info("등록된 게시글이 없습니다.")
        else:
            for _, row in posts.iterrows():
                st.subheader(row["title"])
                st.caption(f"작성일: {row['created_at']}")
                st.write(row["content"])
                st.divider()

    with tab2:
        imgs = load_images(category)

        if imgs.empty:
            st.info("등록된 이미지가 없습니다.")
        else:
            for _, row in imgs.iterrows():
                try:
                    image_bytes = base64_to_bytes(row["base64_data"])
                    st.image(image_bytes, caption=row["filename"], use_container_width=True)
                    st.divider()
                except Exception as e:
                    st.error(f"이미지를 불러오지 못했습니다: {row.get('filename', '')}")
                    st.code(str(e))

    with tab3:
        excels = load_excel_data(category)

        if excels.empty:
            st.info("등록된 엑셀표가 없습니다.")
        else:
            for _, row in excels.iterrows():
                st.subheader(row["title"])
                st.caption(f"등록일: {row['created_at']}")

                try:
                    df = pd.read_json(row["json_data"])
                    st.dataframe(df, use_container_width=True)
                except Exception as e:
                    st.error("엑셀 데이터를 불러오는 중 오류가 발생했습니다.")
                    st.code(str(e))

                st.divider()


def _parse_popularity_input(text: str):
    values = text.replace(" ", ",").split(",")
    values = [value.strip() for value in values if value.strip()]
    if len(values) != 5:
        raise ValueError("인기순위 숫자 5개를 입력하세요. 예: 4,7,2,1,5")
    parsed = [int(value) for value in values]
    if len(set(parsed)) != 5:
        raise ValueError("같은 번호를 중복 입력할 수 없습니다.")
    if any(value < 1 or value > 7 for value in parsed):
        raise ValueError("선수 번호는 1부터 7까지만 입력하세요.")
    return parsed


def show_keirin_field_prediction():
    st.title("🚴 경륜 현장 예측")
    st.write("현장에서 확인한 배당률(인기도) 순서대로 선수 번호 5개를 입력하세요.")
    st.caption("예: 1위 4번, 2위 7번, 3위 2번, 4위 1번, 5위 5번이면 `4,7,2,1,5`")

    db = load_keirin_pattern_db()
    if db.empty:
        st.warning("저장된 예측 db가 없습니다. 관리자 업로드 메뉴에서 db 엑셀을 먼저 등록하세요.")
        return

    st.caption(f"현재 저장된 과거 db: {len(db):,}경주")
    with st.form("field_prediction_form"):
        popularity_text = st.text_input(
            "인기도 순서 a1~a5",
            placeholder="4,7,2,1,5",
            help="쉼표로 구분하여 입력하세요.",
        )
        submitted = st.form_submit_button("예측 결과 보기", use_container_width=True)

    if not submitted:
        return

    try:
        inputs = _parse_popularity_input(popularity_text)
        result = predict_from_popularity(db, inputs)
    except Exception as e:
        st.error(str(e))
        return

    st.subheader("예측 결과")
    st.info(result["message"])
    result_df = result["rows"].copy()
    result_df.insert(0, "순위", range(1, len(result_df) + 1))
    result_df["확률"] = result_df["확률"].map(lambda value: f"{value:.2%}")
    st.dataframe(result_df, hide_index=True, use_container_width=True)
    st.caption(f"예측 방식: {result['method']} | 정확 빈도: {result['match_count']}건")


st.sidebar.title("📌 메뉴")

menu = st.sidebar.selectbox(
    "메뉴 선택",
    ["🚴 경륜 현장예측", "🏇 경마", "🚤 경정", "🚴 경륜", "📢 공지사항", "🔑 관리자 업로드"]
)


if menu == "🚴 경륜 현장예측":
    show_keirin_field_prediction()

elif menu == "🏇 경마":
    show_category_page(menu, "경마")

elif menu == "🚤 경정":
    show_category_page(menu, "경정")

elif menu == "🚴 경륜":
    show_category_page(menu, "경륜")

elif menu == "📢 공지사항":
    st.title("📢 공지사항")

    posts = load_posts("공지사항")

    if posts.empty:
        st.info("등록된 공지사항이 없습니다.")
    else:
        for _, row in posts.iterrows():
            st.subheader(row["title"])
            st.caption(f"작성일: {row['created_at']}")
            st.write(row["content"])
            st.divider()


elif menu == "🔑 관리자 업로드":
    st.title("🔑 관리자 업로드")

    if not ADMIN_PASSWORD:
        st.error("관리자 비밀번호가 설정되지 않았습니다. Streamlit Secrets에 `admin_password`를 추가하세요.")
        st.stop()

    pw = st.text_input("관리자 비밀번호", type="password")

    if pw and pw != ADMIN_PASSWORD:
        st.error("비밀번호가 틀렸습니다.")

    if pw == ADMIN_PASSWORD:
        st.success("관리자 로그인 성공")

        st.subheader("🚴 현장예측 db 등록")
        st.write("`db` 시트에 `no, a1~a5, n1~n3` 열이 들어 있는 엑셀 파일을 등록하세요.")
        pattern_file = st.file_uploader(
            "경륜 예측 db 엑셀 선택",
            type=["xlsx", "xls"],
            key="keirin_pattern_db_uploader"
        )
        if st.button("현장예측 db 저장", type="primary"):
            if pattern_file is None:
                st.warning("db 엑셀 파일을 선택하세요.")
            else:
                try:
                    pattern_df = pd.read_excel(pattern_file, sheet_name="db")
                    saved_rows = save_keirin_pattern_db(pattern_df)
                    load_keirin_pattern_db.clear()
                    st.success(f"현장예측 db {saved_rows:,}건 저장 완료!")
                except Exception as e:
                    st.error("현장예측 db 저장 중 오류가 발생했습니다.")
                    st.code(str(e))

        st.divider()

        category = st.selectbox(
            "카테고리 선택",
            ["경마", "경정", "경륜", "공지사항"]
        )

        st.divider()

        st.subheader("📝 텍스트 글 올리기")
        title = st.text_input("글 제목")
        content = st.text_area("글 내용", height=180)

        if st.button("글 저장"):
            if not title.strip():
                st.warning("제목을 입력하세요.")
            elif not content.strip():
                st.warning("내용을 입력하세요.")
            else:
                save_post(category, title, content)
                st.success("글 저장 완료!")

        st.divider()

        st.subheader("🖼️ 이미지 올리기")
        img_file = st.file_uploader(
            "이미지 선택",
            type=["png", "jpg", "jpeg"],
            key="image_uploader"
        )

        if st.button("이미지 저장"):
            if img_file is None:
                st.warning("이미지 파일을 선택하세요.")
            else:
                save_image(category, img_file.name, img_file.read())
                st.success("이미지 저장 완료!")

        st.divider()

        st.subheader("📊 엑셀표 올리기")
        xl_title = st.text_input("표 제목")
        xl_file = st.file_uploader(
            "엑셀 파일 선택",
            type=["xlsx", "xls"],
            key="excel_uploader"
        )

        if st.button("엑셀 저장"):
            if not xl_title.strip():
                st.warning("표 제목을 입력하세요.")
            elif xl_file is None:
                st.warning("엑셀 파일을 선택하세요.")
            else:
                try:
                    df = pd.read_excel(xl_file)
                    save_excel(category, xl_title, df)
                    st.success("엑셀 저장 완료!")
                except Exception as e:
                    st.error("엑셀 저장 중 오류가 발생했습니다.")
                    st.code(str(e))
