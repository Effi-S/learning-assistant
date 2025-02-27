import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import streamlit as st

from pacer import services
from pacer.models.file_model import FileEntry
from pacer.models.project_model import ProjectData
from pacer.orm.file_orm import FileStatus

st.set_page_config(layout="wide")  # Enables wide mode


@st.cache_data
def list_projects() -> list[str]:
    return services.list_projects()


@st.cache_data
def list_files(project: str) -> list[FileEntry]:
    files = services.list_files(project)
    return files


def _show_file(file: FileEntry):
    with st.expander(f"{Path(file.filepath).name}"):
        st.text_input("Path:", value=file.filepath)

        if summary := file.crypto_data.get("summary"):
            st.header("Summary:")
            st.markdown("---")
            st.markdown(summary)

        if st.checkbox(f"File Content", key=f"content_checkbox_{file.filepath}"):
            st.code(
                file.content, line_numbers=True, language=Path(file.filepath).suffix[1:]
            )
        if st.checkbox(f"View Raw Data", key=f"raw_checkbox_{file.id}"):
            st.code(
                json.dumps(
                    file.crypto_data | {"id": file.id, "status": file.status}, indent=2
                ),
                line_numbers=True,
                language="json",
            )


def display_project_files(project: str = None) -> Any:
    """Display the list of files in a project and available actions."""
    if not project:
        return st.warning("Please Choose a project in the sidebar")
    st.subheader(project)

    files = list_files(project)
    if not files:
        return st.warning("No files found in this project.")

    c1, c2 = st.columns([0.8, 0.1])
    for fl in files:
        fl: FileEntry
        with c1:
            st.markdown(f"`{Path(fl.filepath).name}`")
        with c2:
            if st.button(":wastebasket:", key=f"{fl.id}_remove_button"):
                services.delete_file(fl)
                st.cache_data.clear()
                st.rerun()
    (
        summary_tab,
        procederal_tab,
        analogous_tab,
        conceptual_tab,
        evidence_tab,
        reference_tab,
    ) = st.tabs(
        ["Summary", "Procederal", "Analogous", "Conceptual ", "Evidence", "Reference"]
    )
    with summary_tab:
        for fl in files:
            st.subheader(fl.filepath)
            data = fl.data
            if data and (summary := data.get("summary")):
                st.markdown(summary)
            elif st.button(":arrows_counterclockwise:", key=f"{fl.id}_add_button"):
                services.add_summary_to_file(fl)
                st.toast("Added summary to file")
                st.cache_data.clear()
                st.markdown(fl.data.get("summary"))
            st.markdown("----")
    with procederal_tab:

        quiz_tab, practice_tab = st.tabs(["Quiz", "Practice"])
        with quiz_tab:

            if not (quiz := services.get_quiz(project)):
                if st.button(
                    ":arrows_counterclockwise:", key=f"{project}_add_quiz_button"
                ):
                    quiz = services.create_quiz(project_name=project)
            if quiz:
                friendly_mode = st.checkbox("Friendly mode")
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
                if st.button("Make More"):
                    services.create_quiz(project_name=project)
                    st.rerun()

                if all(choices):
                    right, total = sum(
                        1 for q, a in zip(quiz.questions, choices) if q.answer == a
                    ), len(quiz.questions)
                    score = right / total
                    if st.button("See Score"):
                        (
                            st.success
                            if score > 0.7
                            else st.info if score > 0.5 else st.error
                        )(f"[{right} / {total}] Score: {score:.0%} ")

            st.markdown("----")
        with practice_tab:

            st.markdown("----")
    with analogous_tab:
        st.markdown("----")

    with conceptual_tab:
        st.markdown("----")

    with evidence_tab:
        st.markdown("----")

    with reference_tab:
        st.markdown("----")


with st.sidebar:
    # Section Add Project
    if project_name := st.text_input("Add New Project"):
        if project_name in list_projects():
            st.warning(f"Project {project_name} already exists!")
        else:
            st.cache_data.clear()
            services.add_project(project_name)
            st.success(f"{project_name} Added!")
            # st.balloons()
        project_name = None
    st.markdown("---")

    # Section: List existing projects
    if not (projects := list_projects()):
        st.warning("No projects available. Add a new project to get started.")
    elif selected_project := st.sidebar.selectbox("Select a Project", projects):

        # Subection: Add new Source to project
        st.header("Add source to project")
        if uploaded_files := st.file_uploader(
            "Choose a file", [".pdf", ".txt", ".png"], accept_multiple_files=True
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
        if url := st.text_input("Enter URL"):
            # TODO
            st.warning("Not implemented yet")
            # st.info(f"Added URL: {url}")
        for _ in range(20):
            st.write("")
        if st.button(":wastebasket: delete project"):
            services.delete_project(selected_project)
            st.cache_data.clear()
            st.rerun()
    st.markdown("---")


# Main Section:
display_project_files(selected_project)


def main():
    """ """


if __name__ == "__main__":
    main()
