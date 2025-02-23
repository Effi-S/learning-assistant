import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import streamlit as st

from pacer import services
from pacer.models.file_model import FileEntry

st.set_page_config(layout="wide")  # Enables wide mode


@st.cache_data
def list_projects() -> list[str]:
    return services.list_projects()


@st.cache_data
def list_files(project: str) -> list[FileEntry]:
    files = services.list_files(project)
    files2status = defaultdict(list)
    for file in files:
        files2status[str(file.status)].append(file)
    return dict(files2status)


def _show_file(file: FileEntry):
    with st.expander(f"{Path(file.filepath).name}"):
        st.text_input("Path:", value=file.filepath)

        if summary := file.crypto_data.get("summary"):
            st.header("Summary:")
            st.markdown("---")
            st.markdown(summary)

        if crypto_summary := file.crypto_data.get("crypto_summary"):
            st.subheader("Crypto Summary:")
            st.divider()
            st.markdown(crypto_summary)
        elif keywords := file.crypto_data.get("filter_keywords"):
            st.text_input(
                label="keywords found:",
                value=" ".join(d.get("name") for d in keywords),
                key=f"keywords_{file.id}",
            )

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
    c1, c2 = st.columns(2)
    with c1:
        st.subheader(project)
    with c2:
        if st.button(":arrows_counterclockwise: Refresh Data"):
            st.cache_data.clear()
    files2status = list_files(project)
    # st.json(files2status)
    if not files2status:
        return st.warning("No files found in this project.")

    proceral_tab, analogous_tab, conceptual_tab, evidence_tab, reference_tab = st.tabs(
        ["Proceral", "Analogous", "Conceptual ", "Evidence", "Reference"]
    )
    with proceral_tab:
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
        # TODO:
        st.success(f"{project_name} Added!")
    st.markdown("---")

    # Section: List existing projects
    st.header("Projects:")
    if projects := list_projects():

        if selected_project := st.sidebar.selectbox("Select a Project", projects):
            # Subection: Add new Source to project
            st.header("Add source to project")
            if uploaded_files := st.file_uploader(
                "Choose a file", [".pdf", ".txt", ".png"], accept_multiple_files=True
            ):
                if st.button("Add"):
                    for file in uploaded_files:
                        # TODO
                        st.info(f"Added file: {file.name}")
                        content = file.read()
                        st.json(
                            {
                                "filename": file.name,
                                "filetype": file.type,
                                "filesize": file.size,
                            },
                            expanded=False,
                        )
            if url := st.text_input("Enter URL"):
                # TODO
                st.info(f"Added URL: {url}")

    else:
        st.warning("No projects available. Add a new project to get started.")


# Main Section:
display_project_files(selected_project)


def main():
    """ """


if __name__ == "__main__":
    main()
