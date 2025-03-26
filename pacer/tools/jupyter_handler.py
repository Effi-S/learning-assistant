import atexit
import hashlib
import re
import socket
import subprocess
import time
from collections import defaultdict

import nbformat as nbf
import streamlit as st

from pacer.config.consts import ROOT_DIR
from pacer.models.code_cell_model import Cell, CellType


class JupyterHandler:
    _port = None

    def __init__(self, project: str):
        self.project = project
        name = self._sanitize(project)
        self._parent = ROOT_DIR / ".jupyter"
        self._parent.mkdir(exist_ok=True)
        self.main_ipynb_path = self._parent / f"{name}.ipynb"
        self.processes = defaultdict(list)
        self.port = JupyterHandler._port or self._find_free_port()

        self.url = f"http://localhost:{self.port}/notebooks/{self.main_ipynb_path.name}"
        atexit.register(self._cleanup)
        self.cells = []
        if self.main_ipynb_path.exists():
            with open(self.main_ipynb_path) as fl:
                nb = nbf.read(fl, as_version=4)
                self.cells = nb["cells"]

    def _sanitize(self, project: str):
        sanitized_name = re.sub(r"[^a-zA-Z0-9_-]", "_", project)
        if not sanitized_name.strip("_"):
            hash_object = hashlib.sha256(project.encode("utf-8"))
            return hash_object.hexdigest()
        return sanitized_name

    def _find_free_port(self, start_port: int = 8888, max_attempts: int = 5):
        """Find an available port starting from start_port."""
        port = start_port
        for _ in range(max_attempts):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind(("localhost", port))
                    return port
                except OSError:
                    port += 1
        return port - 1
        # raise RuntimeError("No available ports found.")

    def _find_streamlit_port(
        self, start_port: int = 8501, max_attempts: int = 10
    ) -> int:
        """Find a port that is currently in use, starting from start_port."""
        for port in range(start_port, start_port + max_attempts):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                if s.connect_ex(("localhost", port)) == 0:  # Port is in use
                    return port
        raise RuntimeError(
            f"No used Streamlit ports found in range {start_port} - {start_port + max_attempts - 1}."
        )

    def add_markdown(self, markdown: str):
        markdown_cell = nbf.v4.new_markdown_cell(markdown)
        self.cells.append(markdown_cell)
        return self

    def add_code(self, code: str):
        code_cell = nbf.v4.new_code_cell(code)
        self.cells.append(code_cell)
        return self

    def add_cell(self, cell: Cell):
        if cell.type == CellType.MARKDOWN:
            return self.add_markdown(cell.content)
        if cell.type == CellType.PYTHON:
            return self.add_code(cell.content)

    def save_changes(self):
        nb = nbf.v4.new_notebook()
        nb["cells"] = self.cells
        with open(self.main_ipynb_path, "w", encoding="utf-8") as fl:
            nbf.write(nb, fl)
        return self

    def run_jupyter(self):

        # --1-- Create Jupyter file
        if not self.main_ipynb_path.exists():
            self.save_changes()

        # Run Jupyter Notebook in the background
        print("Running Jupyter on:", self.port)
        streamlit_port = self._find_streamlit_port()
        tornado_settings = {
            "headers": {
                "Content-Security-Policy": f"frame-ancestors 'self' http://localhost:{streamlit_port}"
            }
        }
        cmd = [
            "jupyter-notebook",
            str(self.main_ipynb_path),
            "--port",
            str(self.port),
            "--no-browser",  # Don't open a browser automatically
            "--NotebookApp.token=''",
            "--NotebookApp.password=''",
            f"--NotebookApp.tornado_settings={tornado_settings}",
        ]
        print("Running:\n", *cmd)
        process = subprocess.Popen(
            cmd,
            cwd=str(self._parent),  # Set working directory to project folder
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.processes[self.port].append(process)

        # Wait briefly to ensure the server starts
        time.sleep(1)
        if process.poll() is not None:
            raise RuntimeError("Failed to start Jupyter Notebook server.")

        if not JupyterHandler._port:
            JupyterHandler._port = self.port

        return self

    def _cleanup(self):
        """Clean up by terminating the Jupyter process."""
        for port, procs in self.processes.items():
            for proc in procs:
                print(f"Jupyter Process killed! port: {port}")
                if proc and proc.poll() is None:
                    proc.terminate()
                try:
                    proc.wait(timeout=5)  # Wait for clean termination
                except subprocess.TimeoutExpired:
                    proc.kill()  # Force kill if it doesn't terminate

    def render(self):
        st.write(f"URL: {self.url}")
        st.components.v1.html(
            f"""
    <style>
        iframe {{
            width: 100%;
            height: 100% !important;
            min-height: 1000px !important;
            border: none;
            background-color: #f0f0f0; /* Debug visibility */
        }}
    </style>
    <iframe src="{self.url}" width="100%" height="100%" frameborder="0"></iframe>
    """,
            height=10_000,
            width=None,
        )
        return self


def main():
    st.set_page_config(layout="wide")
    handler = JupyterHandler("test-proj")
    handler.add_markdown("# Title").add_code('print("Hello, World!")').run_jupyter()

    st.title("Embedded Jupyter")
    #
    handler.render()


if __name__ == "__main__":
    main()
