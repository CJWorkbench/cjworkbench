from functools import lru_cache
import hashlib
from http.server import HTTPServer, BaseHTTPRequestHandler
import io
from pathlib import Path
import threading
from typing import Dict, NamedTuple
import zipfile
from integrationtests.browser import Browser


ZipfileEntry = NamedTuple("ZipfileEntry", [("name", str), ("body", bytes)])


def _load_zipfile_entry(dirpath: Path) -> ZipfileEntry:
    module_id = dirpath.name
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, mode="w") as zf:
        for path in dirpath.glob("**/*"):
            if path.is_file():
                zf.write(path, str(path.relative_to(dirpath)))
    body = bio.getbuffer()
    sha1 = hashlib.sha1()
    sha1.update(body)
    version = sha1.hexdigest()

    name = f"{module_id}.{version}.zip"

    return ZipfileEntry(name, body)


def _load_zipfile_entries() -> Dict[str, ZipfileEntry]:
    entries = (
        _load_zipfile_entry(dirpath)
        for dirpath in MODULES_ROOT.iterdir()
        if dirpath.is_dir()
    )
    return {f"/{entry.name}": entry for entry in entries}


MODULES_ROOT = Path(__file__).parent.parent / "module-zipfile-server" / "modules"
ZIPFILE_ENTRIES = _load_zipfile_entries()
ZIPFILE_PATHS: Dict[str, str] = {
    path[1:].split(".", 1)[0]: path for path in ZIPFILE_ENTRIES.keys()
}


@lru_cache(maxsize=1)
def _get_singleton_http_server() -> HTTPServer:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            try:
                entry = ZIPFILE_ENTRIES[self.path]
            except KeyError:
                self.send_error(404)
                return

            self.send_response(200)
            self.send_header("Content-Type", "application/zip")
            self.end_headers()
            self.wfile.write(entry.body)

        def log_message(self, *args):
            pass

    server = HTTPServer(("module-zipfile-server", 0), Handler)
    thread = threading.Thread(
        target=server.serve_forever, kwargs={"poll_interval": 0.005}
    )
    thread.setDaemon(True)  # so it dies when we finish integration-testing
    thread.start()
    return server


def import_workbench_module(browser: Browser, module_id: str) -> None:
    """
    Import a module by clicking through the browser.

    Assumes there's a context menu with an "Import Module" modal.

    Side-effect: this will launch a singleton HTTP-server thread at
    http://module-zipfile-server:PORT, where PORT is an unused TCP port.
    """
    server = _get_singleton_http_server()
    port = server.server_port
    path = ZIPFILE_PATHS[module_id]
    with browser.scope(".navbar", wait=True):  # wait for page to load
        browser.click_button("menu")
    browser.click_button("Import Module")
    with browser.scope(".modal-dialog"):
        browser.fill_in("url", f"http://module-zipfile-server:{port}{path}", wait=True)
        browser.click_button("Import")
        browser.wait_for_element(".import-github-success", text="Imported", wait=True)
        browser.click_button("×")
