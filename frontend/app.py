"""
frontend/app.py

Phase 16: full Streamlit chatbot UI.

Layout:
    Sidebar   - upload files, list of uploaded files this session,
                list of generated artifacts this session (quick-select)
    Main      - chat interface. Each assistant turn shows a progress
                checklist of which agents ran, then artifact cards
                (download + validation status) for anything generated,
                plus an expandable trace view.
    Artifact
    panel     - below the chat: select any artifact from this session to
                see its full version history, download any version,
                request a conversational edit, or convert it to the other
                format (DOCX<->PPTX).

Run with:
    streamlit run frontend/app.py
(from the project root, with the venv activated, backend already running)
"""
import os
from datetime import datetime

import requests
import streamlit as st

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="Multi-Agent Doc/PPT Chatbot", page_icon="🧩", layout="wide")


# --------------------------------------------------------------------------
# Session state
# --------------------------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []  # list of {"role": "user"|"assistant", "content": str, "result": dict|None}
if "uploaded_files" not in st.session_state:
    st.session_state.uploaded_files = []  # list of {"file_id", "filename"}
if "artifacts" not in st.session_state:
    st.session_state.artifacts = {}  # artifact_id -> {"type": "docx"|"pptx", "label": str}


# --------------------------------------------------------------------------
# API helpers
# --------------------------------------------------------------------------
def api_get(path: str, **kwargs):
    return requests.get(f"{BACKEND_URL}{path}", timeout=kwargs.pop("timeout", 30), **kwargs)


def api_post(path: str, **kwargs):
    return requests.post(f"{BACKEND_URL}{path}", timeout=kwargs.pop("timeout", 120), **kwargs)


def register_artifact(artifact_id: str | None, artifact_type: str, label: str) -> None:
    if artifact_id:
        st.session_state.artifacts[artifact_id] = {"type": artifact_type, "label": label}


# --------------------------------------------------------------------------
# Sidebar
# --------------------------------------------------------------------------
with st.sidebar:
    st.subheader("Backend status")
    try:
        resp = api_get("/health", timeout=3)
        if resp.ok:
            st.success(f"Connected · LLM: {resp.json().get('llm_provider')} · Vector store: {resp.json().get('vector_store')}")
        else:
            st.error(f"Backend returned {resp.status_code}")
    except requests.exceptions.RequestException:
        st.error("Cannot reach backend. Is `uvicorn backend.main:app` running?")

    st.divider()

    st.subheader("📁 Upload files")
    uploaded = st.file_uploader(
        "PDF / DOCX / PPTX / image",
        type=["pdf", "docx", "pptx", "png", "jpg", "jpeg"],
        accept_multiple_files=True,
        key="uploader",
    )
    if uploaded:
        for f in uploaded:
            already = any(u["filename"] == f.name for u in st.session_state.uploaded_files)
            if not already:
                files = {"file": (f.name, f.getvalue(), f.type)}
                try:
                    r = api_post("/upload", files=files, timeout=30)
                    if r.ok:
                        file_id = r.json()["file"]["file_id"]
                        st.session_state.uploaded_files.append({"file_id": file_id, "filename": f.name})
                        st.toast(f"Uploaded {f.name}")
                    else:
                        st.error(f"Upload failed for {f.name}: {r.json().get('detail')}")
                except requests.exceptions.RequestException as e:
                    st.error(f"Upload failed: {e}")

    if st.session_state.uploaded_files:
        st.caption("Uploaded this session:")
        for u in st.session_state.uploaded_files:
            st.text(f"📄 {u['filename']}")

    st.divider()

    st.subheader("🗂 Generated artifacts")
    if st.session_state.artifacts:
        for aid, info in st.session_state.artifacts.items():
            icon = "📝" if info["type"] == "docx" else "📊"
            st.text(f"{icon} {info['label']}")
    else:
        st.caption("None yet — ask the assistant to generate something.")


# --------------------------------------------------------------------------
# Main: chat
# --------------------------------------------------------------------------
st.title("🧩 Multi-Agent Document & PPT Generation Chatbot")
st.caption(
    "Upload a DOCX/PPTX template in the sidebar, then ask for research + a proposal + a presentation. "
    "You can also ask to edit a previously generated artifact."
)


def render_progress_checklist(agent_calls: list[dict]) -> None:
    label_map = {
        "document_analyzer": "Document analyzed",
        "ppt_analyzer": "PPT analyzed",
        "web_research": "Web research completed",
        "rag_agent": "Enterprise knowledge retrieved",
        "document_generator": "DOCX generated",
        "ppt_generator": "PPTX generated",
    }
    lines = []
    for call in agent_calls:
        label = label_map.get(call["agent"], call["agent"])
        if call["status"].startswith("success"):
            icon = "✅"
        elif call["status"] == "skipped":
            icon = "⏭️"
        else:
            icon = "❌"
        detail = f" — {call['detail']}" if call.get("detail") else ""
        lines.append(f"{icon} {label}{detail}")
    st.markdown("\n\n".join(f"- {line}" for line in lines))


def render_artifact_card(artifact_id: str, artifact_type: str, validation_status: str | None) -> None:
    icon = "📝" if artifact_type == "docx" else "📊"
    cols = st.columns([3, 1, 1])
    with cols[0]:
        badge = "🟢 PASS" if validation_status == "PASS" else ("🔴 FAIL" if validation_status else "—")
        st.markdown(f"{icon} **{artifact_id}.{artifact_type}**  ·  Validation: {badge}")
    with cols[1]:
        try:
            dl = api_get(f"/artifact/{artifact_id}/download")
            if dl.ok:
                st.download_button(
                    "⬇️ Download",
                    data=dl.content,
                    file_name=f"{artifact_id}.{artifact_type}",
                    key=f"dl_{artifact_id}_{datetime.now().timestamp()}",
                )
        except requests.exceptions.RequestException:
            st.caption("Download unavailable")
    with cols[2]:
        st.caption(f"v{st.session_state.artifacts.get(artifact_id, {}).get('version', 1)}")


for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        result = msg.get("result")
        if result:
            if result.get("agent_calls"):
                with st.expander("Agent activity", expanded=True):
                    render_progress_checklist(result["agent_calls"])

            if result.get("warnings"):
                for w in result["warnings"]:
                    st.warning(w)

            if result.get("generated_docx_artifact_id"):
                render_artifact_card(result["generated_docx_artifact_id"], "docx", result.get("docx_validation_status"))
            if result.get("generated_pptx_artifact_id"):
                render_artifact_card(result["generated_pptx_artifact_id"], "pptx", result.get("pptx_validation_status"))

            if result.get("trace_id"):
                with st.expander(f"🔍 Trace: {result['trace_id']}"):
                    try:
                        trace_resp = api_get(f"/trace/{result['trace_id']}")
                        if trace_resp.ok:
                            st.json(trace_resp.json())
                    except requests.exceptions.RequestException:
                        st.caption("Trace unavailable")


user_input = st.chat_input("Ask the assistant to research, analyze, or generate a document/presentation...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input, "result": None})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Running multi-agent pipeline..."):
            file_ids = [u["file_id"] for u in st.session_state.uploaded_files]
            try:
                resp = api_post("/chat", json={"message": user_input, "file_ids": file_ids}, timeout=600)
                if resp.ok:
                    result = resp.json()
                    reply = result.get("next_step_note") or "Done."
                    st.markdown(reply)

                    if result.get("agent_calls"):
                        with st.expander("Agent activity", expanded=True):
                            render_progress_checklist(result["agent_calls"])
                    if result.get("warnings"):
                        for w in result["warnings"]:
                            st.warning(w)

                    if result.get("generated_docx_artifact_id"):
                        register_artifact(result["generated_docx_artifact_id"], "docx", f"{result['generated_docx_artifact_id']}.docx")
                        render_artifact_card(result["generated_docx_artifact_id"], "docx", result.get("docx_validation_status"))
                    if result.get("generated_pptx_artifact_id"):
                        register_artifact(result["generated_pptx_artifact_id"], "pptx", f"{result['generated_pptx_artifact_id']}.pptx")
                        render_artifact_card(result["generated_pptx_artifact_id"], "pptx", result.get("pptx_validation_status"))

                    if result.get("trace_id"):
                        with st.expander(f"🔍 Trace: {result['trace_id']}"):
                            trace_resp = api_get(f"/trace/{result['trace_id']}")
                            if trace_resp.ok:
                                st.json(trace_resp.json())

                    st.session_state.messages.append({"role": "assistant", "content": reply, "result": result})
                    st.rerun()  # refresh so the sidebar's artifact list reflects what was just generated
                else:
                    error_msg = f"Request failed ({resp.status_code}): {resp.text}"
                    st.error(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg, "result": None})
            except requests.exceptions.RequestException as e:
                error_msg = f"Could not reach backend: {e}"
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg, "result": None})


# --------------------------------------------------------------------------
# Artifact panel: version history, editing, conversion
# --------------------------------------------------------------------------
st.divider()
st.header("📋 Artifact Panel")

if not st.session_state.artifacts:
    st.caption("Generate a document or presentation via the chat above to manage it here.")
else:
    selected_id = st.selectbox(
        "Select an artifact to manage",
        options=list(st.session_state.artifacts.keys()),
        format_func=lambda aid: st.session_state.artifacts[aid]["label"],
    )

    if selected_id:
        artifact_type = st.session_state.artifacts[selected_id]["type"]

        try:
            info_resp = api_get(f"/artifact/{selected_id}")
            if info_resp.ok:
                info = info_resp.json()

                st.subheader("Version history")
                for v in info["versions"]:
                    cols = st.columns([1, 3, 2])
                    with cols[0]:
                        st.markdown(f"**v{v['version']}**")
                    with cols[1]:
                        st.caption(v.get("change_request") or "(initial generation)")
                    with cols[2]:
                        dl = api_get(f"/artifact/{selected_id}/download", params={"version": v["version"]})
                        if dl.ok:
                            st.download_button(
                                "Download",
                                data=dl.content,
                                file_name=f"{selected_id}_v{v['version']}.{artifact_type}",
                                key=f"dl_v_{selected_id}_{v['version']}",
                            )

                st.subheader("✏️ Request an edit")
                edit_request = st.text_input(
                    "Describe the change",
                    placeholder="e.g. Add an executive summary / Make it more concise / Remove the Introduction section",
                    key=f"edit_input_{selected_id}",
                )
                if st.button("Apply edit", key=f"edit_btn_{selected_id}") and edit_request:
                    with st.spinner("Applying edit..."):
                        edit_resp = api_post(f"/artifact/{selected_id}/edit", json={"request": edit_request})
                        if edit_resp.ok:
                            edit_result = edit_resp.json()
                            st.success(f"{edit_result['change_summary']} (now v{edit_result['new_version']}, validation: {edit_result['validation_status']})")
                            st.rerun()
                        else:
                            st.error(f"Edit failed: {edit_resp.text}")

                st.subheader("🔄 Convert format")
                other_format = "pptx" if artifact_type == "docx" else "docx"
                if st.button(f"Convert to {other_format.upper()}", key=f"conv_btn_{selected_id}"):
                    with st.spinner(f"Converting to {other_format}..."):
                        endpoint = "/convert/document-to-presentation" if artifact_type == "docx" else "/convert/presentation-to-document"
                        conv_resp = api_post(endpoint, json={"artifact_id": selected_id})
                        if conv_resp.ok:
                            conv_result = conv_resp.json()
                            new_id = conv_result["new_artifact_id"]
                            register_artifact(new_id, other_format, f"{new_id}.{other_format}")
                            st.success(f"Converted → {new_id} (validation: {conv_result['validation_status']})")
                            st.rerun()
                        else:
                            st.error(f"Conversion failed: {conv_resp.text}")
            else:
                st.error("Could not load artifact info.")
        except requests.exceptions.RequestException as e:
            st.error(f"Backend request failed: {e}")
