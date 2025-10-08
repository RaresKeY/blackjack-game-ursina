from xml.etree.ElementTree import fromstring
from ursina import Vec3, Ursina, Entity, EditorCamera, color, application, camera, scene, destroy
import json, os
from painting_on_water.gentity import GEntity
from painting_on_water.card import Card
from painting_on_water.camera_outline import outline_camera_prep
from painting_on_water.ursina_helpers import resource_path_rel

from pathlib import Path
import tempfile

CAMERA_POS = "Assets/Data/cam_pos_prop.json"
LEVELS_JSON = "Assets/Data/levels.json"

class SceneManager():
    """custom scene manager"""
    def __init__(self, file_path=LEVELS_JSON):
        self._levels = dict()
        self._file_path = resource_path_rel(file_path)
        self._load_json_scene()

    def _load_json_scene(self):
        if os.path.exists(self._file_path):
            with open(self._file_path, "r") as f:
                self._levels = json.load(f)
        else:
            self._levels = dict()

    def _save_json_scene(self):
        with open(self._file_path, "w") as f:
            json.dump(self._levels, f, indent=4)

    def _get_entity(self, e, level_name):
        eid = len(self._levels[level_name])
        class_type = e.__class__.__name__ # str of class name

        # bullshit
        model_name = None
        if e.model:
            try:
                model_name = e.model.name  # "quad", "cube", etc.
            except AttributeError:
                model_name = str(e.model)  # fallback for file paths

        return {
            "name": f"{e}_{eid}",
            "position": [e.x, e.y, e.z],
            "rotation": [e.rotation_x, e.rotation_y, e.rotation_z],
            "scale": [e.scale.x, e.scale.y, e.scale.z],
            "color": list(e.color),

            "model": model_name,
            "texture": str(e.texture) if e.texture else None,
            "collider": str(e.collider) if e.collider else None,
            "collider_path": getattr(e, "collider_path", None),

            "movable": getattr(e, "movable", None),
            "selectable": getattr(e, "selectable", None),

            "parent": e.parent.name if e.parent else None, # str name only
            "children": [self._get_entity(c, level_name) for c in e.children],
            "class_type": class_type,
            "system": class_type in ["Camera", "EditorCamera", "DirectionalLight", "AmbientLight"],
            "persist": getattr(e, "persist", None),
            "custom_class_param": { # TODO: fill with custom metadata
                "custom_param1": "custom_var1"
            }
        }
    
    def save_scene(self, level_name):
        self._levels[level_name] = {}

        # wanted = ["Card", "GEntity"]

        for e in scene.children:
            print(e.__class__.__name__)
            if not getattr(e, 'persist', False):
                continue
            eid = len(self._levels[level_name])
            self._levels[level_name][eid] = self._get_entity(e, level_name)

        self._save_json_scene()
    
    def _get_spawnable(self, node: dict):
        # Only what Entity/GEntity accepts — no JSON-only fields here.
        kw = {
            "position": Vec3(*node.get("position", (0,0,0))),
            "rotation": Vec3(*node.get("rotation", (0,0,0))),
            "scale":    Vec3(*node.get("scale", (1,1,1))),
            "color":    color.rgba(*node.get("color", (1,1,1,1))),
        }
        if node.get("movable"): kw["movable"] = node["movable"]
        if node.get("selectable"): kw["selectable"] = node["selectable"]

        if node.get("model"): kw["model"] = node["model"]
        if node.get("texture"): kw["texture"] = node["texture"]
        if node.get("collider"): kw["collider"] = node["collider"]
        if node.get("collider_path"): kw["collider_path"] = node["collider_path"]
        if node.get("custom_class_param"): kw["custom_class_param"] = node["custom_class_param"]
        return kw

    def _spawn_entity(self, node: dict, parent):
        if not isinstance(node, dict):
            raise TypeError(f"_spawn_entity expected dict, got {type(node)}")

        kw = self._get_spawnable(node)
        kw["parent"] = parent
        if node.get("class_type") == "Card":
            cls = Card
            kw["front_texture"] = kw["texture"]
        elif node.get("class_type") == "GEntity":
            cls = GEntity
        else:
            cls = Entity

        ent = cls(**kw)
        ent.name = node.get("name", getattr(ent, "name", "entity"))

        if node.get("class_type") != "Card":
            # recurse
            for child in node.get("children", []):
                self._spawn_entity(child, ent)

        return ent

    def load_scene(self, level_name):
        spawned = []
        for node in self._levels.get(level_name, {}).values():
            if node.get("system"):                # skip camera/lights/etc. if desired
                continue
            if node.get("parent") not in (None, "scene"):   # only spawn roots; children handled in recursion
                continue
            spawned.append(self._spawn_entity(node, scene))
        return spawned
    
    def delete_scene(self, level_name):
        self._load_json_scene()
        if level_name in self._levels:
            del self._levels[level_name]
            self._save_json_scene()

    def clear_scene(self):
        # clear runtime Ursina scene (but keep lights, camera, etc.)
        for e in scene.entities[:]:
            if getattr(e, "persist", None):
                destroy(e)

    def spawn_card(self, card):
        Card(front_texture=card)

if __name__ == "__main__":

    app = Ursina()

    outline_camera_prep()

    scn_manager = SceneManager()
    # scn_manager.save_scene("blackjack")
    scn_manager.load_scene("blackjack")
    # scn_manager.save_scene("debug_scene")

    EditorCamera()  # optional scene control
    app.run()

