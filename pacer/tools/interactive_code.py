import re
import sys
from io import StringIO

import streamlit as st
from IPython.core.interactiveshell import InteractiveShell


# Function to strip ANSI color codes
def strip_ansi_codes(text):
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    return ansi_escape.sub("", text)


shell = InteractiveShell.instance()

ANSI_COLORS = {
    "30": "black",
    "31": "red",
    "32": "green",
    "33": "yellow",
    "34": "blue",
    "35": "purple",
    "36": "cyan",
    "37": "white",
    # Bright colors (90-97)
    "90": "gray",
    "91": "#ff5555",  # bright red
    "92": "#55ff55",  # bright green
    "93": "#ffff55",  # bright yellow
    "94": "#5555ff",  # bright blue
    "95": "#ff55ff",  # bright purple
    "96": "#55ffff",  # bright cyan
    "97": "#ffffff",  # bright white
}


def ansi_to_html(text):
    def replace_ansi(match):
        codes = match.group(0)[2:-1].split(";")  # Extract numbers between [ and m
        style = ""
        for code in codes:
            if code in ANSI_COLORS:
                style += f"color: {ANSI_COLORS[code]};"
            elif code == "1":  # Bold
                style += "font-weight: bold;"
            elif code == "0":  # Reset
                style = ""
        return f'</span><span style="{style}">' if style else "</span><span>"

    # Split into lines and process each line
    lines = text.split("\n")
    html_lines = []

    for line in lines:
        # Add initial span
        processed = (
            "<span>" + re.sub(r"\x1B\[[0-?]*[m]", replace_ansi, line) + "</span>"
        )
        html_lines.append(processed)

    # Join lines with <br> and wrap in pre
    html = "<br>".join(html_lines)
    return f'<pre style="font-family: monospace; white-space: pre-wrap;">{html}</pre>'


def interactive_code(code: str):
    code_input = st.text_area("Enter Python/IPython code", code, key="st_code_input")

    if st.button("Run"):
        # Capture stdout and stderr
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        captured_output = StringIO()
        captured_error = StringIO()
        sys.stdout = captured_output
        sys.stderr = captured_error

        try:
            # Execute the code
            res = shell.run_cell(code_input)

            # Get the outputs
            print_output = captured_output.getvalue()
            error_output = captured_error.getvalue()

            # Display the results
            st.write("Output:")

            if any(
                (
                    not res.success,
                    error_output,
                    res.error_before_exec is not None,
                    res.error_in_exec is not None,
                )
            ):
                if error_output:
                    print_output = f"{print_output}\n{error_output.rstrip()}"
                st.markdown(ansi_to_html(print_output.rstrip()), unsafe_allow_html=True)
                # st.write(ansi_to_html(print_output.rstrip()), unsafe_allow_html=True)

            elif print_output:
                st.code(
                    print_output.rstrip(),
                    language="python",
                )

        finally:
            # Restore stdout and stderr
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            captured_output.close()
            captured_error.close()


if __name__ == "__main__":
    interactive_code("print('Hello')\n23*2")
