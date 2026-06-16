import os
import time

import requests
import streamlit as st

_raw = os.getenv("API_URL", "http://localhost:8000").rstrip("/")
if _raw.endswith("/chat"):
    _raw = _raw[: -len("/chat")]
API_BASE = _raw


def list_conversations() -> list[dict]:
    r = requests.get(f"{API_BASE}/conversations", timeout=10)
    r.raise_for_status()
    return r.json()


def create_conversation(title: str | None = None) -> dict:
    r = requests.post(
        f"{API_BASE}/conversations",
        json={"title": title},
        timeout=10,
    )
    r.raise_for_status()
    return r.json()


def get_conversation(conv_id: int) -> dict:
    r = requests.get(f"{API_BASE}/conversations/{conv_id}", timeout=10)
    r.raise_for_status()
    return r.json()


def delete_conversation(conv_id: int) -> None:
    r = requests.delete(f"{API_BASE}/conversations/{conv_id}", timeout=10)
    r.raise_for_status()


def list_collections() -> list[dict]:
    r = requests.get(f"{API_BASE}/collections", timeout=10)
    r.raise_for_status()
    return r.json()


# ---------------------------------------------------------------------------
# [P3 DeepResearch] API ヘルパー
# ---------------------------------------------------------------------------

def _start_deep_research(query: str, collection_id: int, conversation_id: int | None) -> str:
    r = requests.post(
        f"{API_BASE}/deep-research",
        json={"query": query, "collection_id": collection_id, "conversation_id": conversation_id},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["job_id"]


def _poll_deep_research(job_id: str) -> dict:
    r = requests.get(f"{API_BASE}/deep-research/{job_id}/progress", timeout=10)
    r.raise_for_status()
    return r.json()


def _save_deep_research(job_id: str) -> None:
    r = requests.post(f"{API_BASE}/deep-research/{job_id}/save", timeout=10)
    r.raise_for_status()


# ---------------------------------------------------------------------------
# [P3 DeepResearch] 進捗・結果表示ヘルパー
# ---------------------------------------------------------------------------

_STATUS_LABELS = {
    "decomposing": "質問を分解中...",
    "searching": "サブクエリで検索中...",
    "synthesizing": "調査結果を統合中...",
    "done": "完了",
    "error": "エラー",
}

_SUB_STATUS_ICONS = {
    "pending": "",
    "searching": "",
    "done": "",
}


def _render_research_progress(progress: dict) -> None:
    status = progress["status"]
    st.markdown(f"**{_STATUS_LABELS.get(status, status)}**")
    for sq in progress.get("sub_queries", []):
        icon = _SUB_STATUS_ICONS.get(sq["status"], "")
        st.markdown(f"{icon} {sq['sub_query']}")


def _render_research_sources(progress: dict) -> None:
    sub_queries = progress.get("sub_queries", [])
    if not sub_queries:
        return
    with st.expander("調査詳細（サブクエリ別ソース）"):
        for sq in sub_queries:
            st.markdown(f"**{sq['sub_query']}**")
            if sq["sources"]:
                for src in sq["sources"]:
                    label = src.get("heading") or src.get("source_file", "")
                    st.caption(f"[{label}] {src['content'][:200]}...")
            else:
                st.caption("(関連情報なし)")
            st.divider()


# ---------------------------------------------------------------------------
# アプリ本体
# ---------------------------------------------------------------------------

st.set_page_config(page_title="Ollama チャット", page_icon="💬")
st.title("Ollama チャット")

if "active_id" not in st.session_state:
    st.session_state.active_id = None
if "messages" not in st.session_state:
    st.session_state.messages = []


def switch_to(conv_id: int | None) -> None:
    st.session_state.active_id = conv_id
    if conv_id is None:
        st.session_state.messages = []
    else:
        detail = get_conversation(conv_id)
        st.session_state.messages = [
            {"role": m["role"], "content": m["content"]}
            for m in detail.get("messages", [])
        ]


with st.sidebar:
    # [P3 DeepResearch] コレクション選択
    st.markdown("### コレクション")
    try:
        collections = list_collections()
    except requests.RequestException:
        collections = []
    collection_names = ["(なし)"] + [c["name"] for c in collections]
    selected_col_name = st.selectbox("RAG コレクション", collection_names)
    selected_collection_id = None
    if selected_col_name != "(なし)":
        selected_collection_id = next(
            (c["id"] for c in collections if c["name"] == selected_col_name), None
        )

    # [P3 DeepResearch] モード切替トグル
    st.markdown("### 検索モード")
    deep_research_mode = st.toggle(
        "Deep Research モード",
        value=False,
        disabled=selected_collection_id is None,
        help="ON にすると質問を複数のサブクエリに分解し、多角的に調査して包括的な回答を生成します（コレクション選択が必要）",
    )

    st.markdown("### 会話一覧")
    if st.button("新しいセッションを開始", use_container_width=True):
        switch_to(None)
        st.rerun()

    try:
        convs = list_conversations()
    except requests.RequestException as exc:
        st.error(f"会話一覧の取得に失敗しました: {exc}")
        convs = []

    for c in convs:
        label = c.get("title") or f"会話 #{c['id']}"
        is_active = st.session_state.active_id == c["id"]
        prefix = "▶ " if is_active else ""
        if st.button(
            f"{prefix}{label}",
            key=f"conv-{c['id']}",
            use_container_width=True,
        ):
            switch_to(c["id"])
            st.rerun()

    if st.session_state.active_id is not None:
        if st.button("この会話を削除", use_container_width=True):
            try:
                delete_conversation(st.session_state.active_id)
            except requests.RequestException as exc:
                st.error(f"削除に失敗しました: {exc}")
            else:
                switch_to(None)
                st.rerun()


for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])


if prompt := st.chat_input("メッセージを入力..."):
    if st.session_state.active_id is None:
        try:
            new_conv = create_conversation(title=prompt[:50])
        except requests.RequestException as exc:
            st.error(f"会話の開始に失敗しました: {exc}")
            st.stop()
        st.session_state.active_id = new_conv["id"]

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    if deep_research_mode and selected_collection_id is not None:
        # [P3 DeepResearch] DeepResearch モード
        progress_area = st.empty()
        try:
            job_id = _start_deep_research(
                query=prompt,
                collection_id=selected_collection_id,
                conversation_id=st.session_state.active_id,
            )

            while True:
                progress = _poll_deep_research(job_id)
                status = progress["status"]

                with progress_area.container():
                    _render_research_progress(progress)

                if status == "done":
                    _save_deep_research(job_id)
                    progress_area.empty()
                    # 結果をセッションに保存して再描画
                    st.session_state["last_research_result"] = progress
                    detail = get_conversation(st.session_state.active_id)
                    st.session_state.messages = [
                        {"role": m["role"], "content": m["content"]}
                        for m in detail.get("messages", [])
                    ]
                    st.rerun()

                if status == "error":
                    progress_area.empty()
                    st.error(f"DeepResearch エラー: {progress.get('error', '不明なエラー')}")
                    break

                time.sleep(1.5)

        except requests.RequestException as exc:
            st.error(f"DeepResearch エラー: {exc}")
    else:
        # 通常チャットモード
        with st.chat_message("assistant"):
            def token_stream():
                try:
                    resp = requests.post(
                        f"{API_BASE}/chat",
                        json={
                            "messages": st.session_state.messages,
                            "conversation_id": st.session_state.active_id,
                            "collection_id": selected_collection_id,
                        },
                        stream=True,
                        timeout=120,
                    )
                    resp.raise_for_status()
                    for chunk in resp.iter_content(chunk_size=1, decode_unicode=True):
                        if chunk:
                            yield chunk
                except requests.RequestException as exc:
                    yield f"\n\n**[接続エラー]** {exc}"

            full_response = st.write_stream(token_stream())

        st.session_state.messages.append(
            {"role": "assistant", "content": full_response}
        )
        st.rerun()

# [P3 DeepResearch] 前回の DeepResearch 結果があれば調査詳細を表示
if "last_research_result" in st.session_state:
    _render_research_sources(st.session_state["last_research_result"])
    del st.session_state["last_research_result"]
