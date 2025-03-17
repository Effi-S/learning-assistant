import contextlib
import io
import re
import sys
import time
from io import StringIO
from typing import Optional

import streamlit as st
from IPython.core.interactiveshell import InteractiveShell

from pacer.models.code_cell_model import Code

if "code_actions" not in st.session_state:
    st.session_state.code_actions = {}

# ANSI color mappings
ANSI_COLORS = {
    "30": "black",
    "31": "red",
    "32": "green",
    "33": "yellow",
    "34": "blue",
    "35": "purple",
    "36": "cyan",
    "37": "white",
    "90": "gray",
    "91": "#ff5555",  # bright red
    "92": "#55ff55",  # bright green
    "93": "#ffff55",  # bright yellow
    "94": "#5555ff",  # bright blue
    "95": "#ff55ff",  # bright purple
    "96": "#55ffff",  # bright cyan
    "97": "#ffffff",  # bright white
}

shell = InteractiveShell.instance()


def strip_ansi_codes(text: str) -> str:
    """Remove ANSI escape codes from text."""
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    return ansi_escape.sub("", text)


def ansi_to_html(text: str) -> str:
    """Convert ANSI color codes to HTML with inline styles."""

    def replace_ansi(match):
        codes = match.group(0)[2:-1].split(";")
        style = ""
        for code in codes:
            if code in ANSI_COLORS:
                style += f"color: {ANSI_COLORS[code]};"
            elif code == "1":
                style += "font-weight: bold;"
            elif code == "0":
                style = ""
        return f'</span><span style="{style}">' if style else "</span><span>"

    lines = text.split("\n")
    html_lines = [
        f"<span>{re.sub(r'\x1B\[[0-?]*[m]', replace_ansi, line)}</span>"
        for line in lines
    ]
    html = "<br>".join(html_lines)
    return f'<pre style="font-family: monospace; white-space: pre-wrap;">{html}</pre>'


@contextlib.contextmanager
def stdout_io(stdout=None):
    """
    Redirects standard output to a given stream (default is io.StringIO).
    This is useful for capturing output within a function.  Critically, it
    handles nested stdout redirection, which the standard contextlib.redirect_stdout
    does NOT do correctly in some cases (especially with subprocesses).
    """
    old = sys.stdout
    if stdout is None:
        stdout = io.StringIO()
    sys.stdout = stdout
    yield stdout
    sys.stdout = old


def execute_code(code, cell_id, code_history, output_history):
    """Executes Python code and captures output, errors, and execution time.

    Args:
        code (str): The Python code to execute.
        cell_id (str):  A unique identifier for the code cell.
        code_history (dict):  Dictionary to store code history (cell_id: code).
        output_history (dict): Dictionary to store output history (cell_id: output).

    Returns:
        tuple: (output, error, execution_time).  'output' and 'error' are strings,
               'execution_time' is a float (seconds).  If an error occurs, 'output'
               will contain any output produced *before* the error.
    """
    start_time = time.time()
    output_buffer = io.StringIO()
    error = ""

    try:
        with stdout_io(stdout=output_buffer):
            exec(code, globals())  # Execute in the global scope
    except Exception as e:
        error = str(e)
    finally:
        execution_time = time.time() - start_time
        output = output_buffer.getvalue()  # Get captured output
        code_history[cell_id] = code
        output_history[cell_id] = output

    return output, error, execution_time


def interactive_code(code: Code, index: int = 0) -> None:
    """Interactive code execution interface in Streamlit."""
    # Ensure code ID exists in session state
    if code.id not in st.session_state.code_actions:
        st.session_state.code_actions[code.id] = {"output": ""}

    with st.expander(label=f"Input [{index if index else ''}]", expanded=True):
        # Code input area
        code_input = st.text_area(
            label="",
            value=code.code,
            height=150,
            key=f"st_code_input_{code.id}",
            placeholder="Enter your Python code here...",
        )

        st.markdown(ansi_to_html(), unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns(4)

        with c1:
            if st.button("Run :arrow_forward:", key=f"st_code_run_{code.id}"):
                (
                    st.session_state.code_actions[code.id]["output"],
                    st.session_state.code_actions[code.id]["error"],
                ) = ("", "")
                output, error, execution_time = execute_code(code_input)
                if error:
                    st.session_state.code_actions[code.id][
                        "error"
                    ] = f"{output}\n{error}"
                elif output:
                    st.session_state.code_actions[code.id]["output"] = output
                    st.session_state.code_actions[code.id]["execution_time"]
                    st.code(output, language="python")
                    st.success(f"Execution Time: {execution_time}")
        with c2:
            if st.button("Edit :pencil:", key=f"st_code_edit_{code.id}"):
                # Placeholder for edit functionality
                st.session_state.code_actions[code.id]["editing"] = True
                st.rerun()

        with c3:
            if st.button(":floppy_disk:", key=f"st_code_save_{code.id}"):
                # Placeholder for save functionality
                st.success("Code saved (placeholder functionality)")
                code.code = code_input

        with c4:
            if st.button("Delete :wastebasket:", key=f"st_code_delete_{code.id}"):
                # Placeholder for delete functionality
                del st.session_state.code_actions[code.id]
                st.rerun()

        # Display previous output if available
        if st.session_state.code_actions[code.id].get("output"):
            st.subheader("Last Output:")
            st.markdown(
                ansi_to_html(st.session_state.code_actions[code.id]["output"]),
                unsafe_allow_html=True,
            )


if __name__ == "__main__":
    # Example usage
    st.title("Interactive Code Runner")
    sample_code = Code(
        id="sample1", code="print('Hello, World!')\nfor i in range(3): print(i)"
    )
    interactive_code(sample_code, services=None)
