from collections import defaultdict
from typing import Any

import streamlit as st
from audio_recorder_streamlit import audio_recorder as st_audiorec
from langchain.schema import AIMessage, HumanMessage, SystemMessage

from pacer import services
from pacer.config import consts
from pacer.config.llm_adapter import LLMSwitch
from pacer.models.code_cell_model import JupyterCells
from pacer.models.file_model import FileEntry
from pacer.models.project_model import ProjectData
from pacer.orm.file_orm import FileType
from pacer.tools.jupyter_handler import JupyterHandler
from pacer.tools.streamlit_utils import confirm_popup

st.set_page_config(layout="wide", page_icon=":placard:", page_title="PACER")

if "edit_toggles" not in st.session_state:
    st.session_state["edit_toggles"] = {}

if "messages" not in st.session_state:
    st.session_state.messages = defaultdict(list)

if "audios" not in st.session_state:
    st.session_state.audios = defaultdict(set)

if "jupyter_handles" not in st.session_state:
    st.session_state.jupyter_handles = {}

_edit_toggles = st.session_state["edit_toggles"]


@st.cache_data
def list_projects() -> list[str]:
    return services.list_projects()


@st.cache_data
def list_files(project: str) -> list[FileEntry]:
    files = services.list_files(project)
    return files


@st.fragment
def _render_notes(project: str):

    with st.form(key=f"{project}_note_form", clear_on_submit=True):

        note = st.text_area("Write your note here:", key=f"{project}_note_input")
        submit_button = st.form_submit_button(label="Add Note")

        if submit_button and note.strip():
            services.add_note(note, project)
            st.success("Note added!")

    st.divider()
    st.markdown("**Your Notes:**\n\n")

    for i, note in enumerate(services.get_notes(project), 1):
        with st.expander(f"{i}) {note.content.split('\n', 1)[0][:50]}.."):
            _c1, _c2, _c3 = st.columns([0.8, 0.1, 0.1])
            with _c2:
                if st.button(f":pencil:", key=f"edit_note_toggle_{i}"):
                    _edit_toggles[i] = not _edit_toggles.get(i, False)
            if _edit_toggles.get(i):
                with _c1:
                    note_edit = st.text_area(label="edit", value=note.content)
                    if st.button("Update", key=f"update_note_{i}"):
                        services.update_note(note, note_edit)
                        _edit_toggles[i] = False
                        st.rerun()
            else:
                with _c1:
                    st.markdown(note.content)
            with _c3:
                if st.button(f":wastebasket:", key=f"del_{i}"):
                    services.remove_note(note)
                    _edit_toggles[i] = True
                    st.rerun(scope="fragment")


@st.fragment
def _render_quiz(project: str):
    if not (quiz := services.get_quiz(project)):
        if st.button(":arrows_counterclockwise:", key=f"{project}_add_quiz_button"):
            with st.spinner("Adding Quiz.."):
                quiz = services.create_quiz(project_name=project)
            st.rerun(scope="fragment")
    if quiz:
        friendly_mode = st.checkbox("Show Answers")
        choices = []
        for i, q in enumerate(quiz.questions):
            if choice := st.radio(
                f"**{q.question}**", q.options, index=None, key=f"qestion_{i}"
            ):
                if friendly_mode:
                    if choice == (ans := q.answer):
                        st.write(":white_check_mark:")
                    else:
                        st.write(f":exclamation: Answer: {ans}")
            choices.append(choice)
        _c1, _c2, _c3 = st.columns(3)
        with _c1:
            if st.button("Make More"):
                with st.spinner("Adding Questions.."):
                    services.create_quiz(project_name=project)
                st.rerun(scope="fragment")
        right, total = sum(
            1 for q, a in zip(quiz.questions, choices) if q.answer == a
        ), len(quiz.questions)
        score = right / total

        with _c2:
            see_score = st.button("See Score")
        if see_score:
            handler = {
                0 <= score < 0.5: st.error,
                0.5 <= score < 0.7: st.info,
                0.7 <= score: st.success,
            }[True]
            handler(f"[{right} / {total}] Score: {score:.0%} ")

        with _c3:
            if st.button("Remove All"):
                with st.spinner("Adding Questions.."):
                    services.remove_quiz(project_name=project)
                st.rerun(scope="fragment")

    st.divider()


@st.fragment
def _render_summary(fl: FileEntry):
    st.subheader(fl.title)
    if fl.data and (summary := fl.data.get("summary")):
        st.markdown(summary)
    elif st.button(":arrows_counterclockwise:", key=f"{fl.id}_add_button"):
        with st.spinner("Adding summary..", show_time=True):
            services.add_summary_to_file(fl)
            st.toast("Added summary to file")
            st.cache_data.clear()
        st.rerun(scope="fragment")


@st.fragment
def _render_chat(project: str):
    st.markdown("#### Context:")
    files = list_files(project=project)
    context_files = [
        file
        for file in files
        if st.checkbox(label=file.title, key=f"{project}_{file}_chat-choice")
    ]

    messages = st.session_state.messages[project]
    if not messages:
        messages.append(AIMessage("Ask some questions about your docs."))
    for message in messages:
        with st.chat_message(message.type):
            st.markdown(message.content)
    c1, c2 = st.columns([0.8, 0.2])
    with c1:
        if user_input := st.chat_input("Type your message..."):
            with st.spinner("Thinking...", show_time=True):
                messages.append(HumanMessage(user_input))
                bot_response = services.ask(
                    messages=messages, context_files=context_files
                )
                messages.append(bot_response)
            st.rerun(scope="fragment")
    with c2:
        if st.button(":wastebasket: Clear Chat", key=f"{project}_clear_chat"):
            st.session_state.messages[project] = []
            st.rerun(scope="fragment")
    st.json(messages, expanded=False)


def display_project_files(project: str = None) -> Any:
    """Display the list of files in a project and available actions."""
    if not project:
        return st.warning("Please Choose a project in the sidebar")
    st.subheader(project)

    files = list_files(project)

    c1, c2 = st.columns([0.8, 0.1])
    for fl in files:
        fl: FileEntry
        with c1:
            st.markdown(f"> {fl.title}")
        with c2:
            if st.button(":wastebasket:", key=f"{fl.id}_remove_button"):
                services.delete_file(fl)
                st.cache_data.clear()
                st.rerun()

    (
        original_tab,
        summary_tab,
        procederal_tab,
        # analogous_tab,
        # conceptual_tab,
        # evidence_tab,
        # reference_tab,
        notes_tab,
        chat_tab,
    ) = st.tabs(
        [
            "Original",
            "Summary",
            "Procederal",
            # "Analogous",
            # "Conceptual ",
            # "Evidence",
            # "Reference",
            "Notes",
            "Chat",
        ]
    )
    with original_tab:
        for fl in files:
            if fl.type_ == FileType.URL:
                st.markdown(fl.title)
                st.markdown(
                    consts.iframe.format(fl.filepath),
                    unsafe_allow_html=True,
                )
            else:
                st.subheader(fl.title)
                for i, doc in enumerate(services.iter_read_entry(fl)):
                    title = "".join(doc.page_content.splitlines()[:1])
                    with st.expander(f"{i}: {title}", expanded=False):
                        st.markdown(doc.page_content)
                st.divider()
    with summary_tab:
        for fl in files:
            _render_summary(fl)
            st.divider()
    with procederal_tab:
        if not files:
            st.warning("No files found in this project.")

        else:
            quiz_tab, practice_tab = st.tabs(["Quiz", "Practice"])
            with quiz_tab:
                _render_quiz(project=project)
            with practice_tab:
                if project not in st.session_state.jupyter_handles:
                    st.session_state.jupyter_handles[project] = JupyterHandler(
                        project=project
                    )

                handler: JupyterHandler = st.session_state.jupyter_handles[project]
                if st.button("Generate", key=f"{project}_jupyter-generate"):
                    with st.spinner("Generating Notebook..", show_time=True):
                        jup: JupyterCells = services.create_jupyter_cells(
                            project_name=project
                        )
                        for cell in jup.cells:
                            handler.add_cell(cell)
                    handler.save_changes()

                handler.run_jupyter().render()

                st.divider()
    # with analogous_tab:
    #     st.divider()

    # with conceptual_tab:
    #     st.divider()

    # with evidence_tab:
    #     st.divider()

    # with reference_tab:
    #     st.divider()

    with notes_tab:
        _render_notes(project=project)
    with chat_tab:
        _render_chat(project)


def _add_proj(project_add_name: str):

    if not project_add_name:
        return

    if project_add_name in list_projects():
        return st.warning(f"Project {project_add_name} already exists!")

    with st.spinner(f"Creating project: {[project_add_name]}.."):
        services.add_project(project_add_name)
    st.cache_data.clear()
    st.success(f"{project_add_name} Added!")
    st.balloons()


@st.fragment
def _render_sidebar():
    # Section Add Project
    with st.form(key="add_proj_form", clear_on_submit=True):
        project_add_name = st.text_input(
            "Add New Project",
            key="add_proj_text_input",
        )
        if st.form_submit_button("Add Project"):
            _add_proj(project_add_name=project_add_name)
    # if project_add_name := st.text_input(
    #     "Add New Project", key="add_proj_text_input"
    # ):
    #     if project_add_name in list_projects():
    #         st.warning(f"Project {project_add_name} already exists!")
    #     else:
    #         st.cache_data.clear()
    #         with st.spinner(f"Creating project: {[project_add_name]}.."):
    #             services.add_project(project_add_name)
    #         st.success(f"{project_add_name} Added!")
    #         st.balloons()
    st.divider()

    # Section: List existing projects
    if not (projects := list_projects()):
        st.warning("No projects available. Add a new project to get started.")
        return
    selected_project = st.selectbox("Select a Project", projects)

    # Subection: Add new Source to project
    st.header("Add source to project")
    if uploaded_files := st.file_uploader(
        "Choose a file", [".pdf", ".txt"], accept_multiple_files=True
    ):
        if st.button("Add"):
            entries = [
                FileEntry(
                    filepath=f.name,
                    project_ref=ProjectData(name=selected_project),
                    content=f.read(),
                )
                for f in uploaded_files
            ]
            with st.spinner(f"Adding ({len(entries)}) files.."):
                services.add_files(entries)
            for file in uploaded_files:
                st.info(f"Added file: {file.name}")

                st.json(
                    {
                        "filename": file.name,
                        "filetype": file.type,
                        "filesize": file.size,
                    },
                    expanded=False,
                )
            st.cache_data.clear()
    with st.form("enter_url_form"):
        url = st.text_input("Enter URL")
        submitted = st.form_submit_button()
    if submitted and url:
        with st.spinner("Adding URL.."):
            services.add_url(url, project_name=selected_project)
        st.cache_data.clear()
        st.info(f"Added URL: {url}")

    st.divider()

    choice = st.selectbox("Choose LLM", options=LLMSwitch.services(), key="cllm-sb")
    if choice:
        LLMSwitch.switch(choice)
        # st.info(f"Current: {LLMSwitch.get_current()}")
    st.divider()
    if audio_data := st_audiorec(
        text="",
        icon_size="2x",
        energy_threshold=0.99,
        key=f"{selected_project}_audio_rec",
    ):

        confirm = confirm_popup("You want to add this audio to project?")
        if confirm:
            st.audio(audio_data)
            st.success("Added audio file")
        if confirm is not None:
            st.session_state.clear()
            st.rerun(scope="fragment")
    st.divider()

    if st.button(":wastebasket: delete project"):
        services.delete_project(selected_project)
        st.cache_data.clear()
        st.rerun()
    return selected_project


def main():
    """ """
    with st.sidebar:
        selected_project = _render_sidebar()
    display_project_files(selected_project)


if __name__ == "__main__":
    main()
