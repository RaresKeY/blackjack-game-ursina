from ursina import application
from pathlib import Path
import tempfile
import sys
import os

# def resource_path_rel(rel_path: str) -> str:
#     temp_root = Path(tempfile.gettempdir())
#     # asset_folder = os.path.dirname(__file__)
#     asset_folder = "/tmp/onefile_9614_1759899549_861280/"

#     temp_project = next((part for part in asset_folder.split(os.sep) if part.startswith("onefile_")),"")
#     temp_project = temp_project + "/"
#     application.asset_folder = Path(temp_root) / Path(temp_project)
#     print("DEBUG:", {"asset_folder": asset_folder,
#                     "temp_project": temp_project,
#                     "temp_root": temp_root,
#                     "rel_path": rel_path})
    
#     return rel_path
    # return os.path.join(temp_root, temp_project, rel_path)

# path helper nuitka
def resource_path_rel(rel_path: str) -> str:
    if getattr(sys, "frozen", False) or "__compiled__" in globals():
        temp_root = Path(tempfile.gettempdir())
        asset_folder = os.path.dirname(__file__)

        #DEBUG: {'asset_folder': '/tmp/onefile_9614_1759899549_861280/', 'temp_project': 'onefile_9614_1759899549_861280/', 'temp_root': PosixPath('/tmp')}
        temp_project = next((part for part in asset_folder.split(os.sep) if part.startswith("onefile_")),"")
        temp_project = temp_project + "/"

        application.asset_folder = Path(temp_root) / Path(temp_project)

        print("DEBUG:", {"asset_folder": asset_folder,
                         "temp_project": temp_project,
                         "temp_root": temp_root})

        # return os.path.join(str(temp_root), temp_project, rel_path)
        return rel_path
    else:
        return rel_path

if __name__ == "__main__":
    with open(resource_path_rel("path/to/file")) as f:
        data = f.read()
