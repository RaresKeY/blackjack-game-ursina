from ursina import EditorCamera, Entity, Vec3, held_keys, time, application, camera  # type: ignore
from painting_on_water.animators import TransformAnimator, OneValueAnimator
from painting_on_water.ursina_helpers import resource_path_rel
from ursina.curve import in_out_expo, in_out_quint, in_out_back
import json
import os
from pathlib import Path
import tempfile

CAMERA_POS = "Assets/Data/cam_pos_prop.json"

# cool json trick to keep in mind # TODO: extract to generalized class for lib
class Vec3Encoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Vec3):
            return (obj.x, obj.y, obj.z)
        return super().default(obj)

class EditorCamFix(EditorCamera):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        

        # supress updates control while animating
        update_orig = self.update
        def update_wrapped():
            if any(isinstance(s, TransformAnimator) for s in camera.parent.scripts):
                return
            return update_orig()
        
        self.update = update_wrapped

        # supress manual control while animating
        input_orig = self.input
        def input_wrapped(key):
            if any(isinstance(s, TransformAnimator) for s in camera.parent.scripts):
                return
            return input_orig(key)

        self.input = input_wrapped

class CameraMan(Entity):
    def __init__(self, file_path=CAMERA_POS, debug=True):
        super().__init__()
        self.camera_saves = dict()
        self.toggle_camera_num = True
        self.current_view = 0
        self._file_path = resource_path_rel(file_path)
        self.debug = debug

        if os.path.exists(self._file_path):
            with open(self._file_path) as f:
                data = json.load(f)
                if isinstance(data, dict) and data:  # file has dict items
                    self.camera_saves = data

    # save cam pos, rot, zoom
    def save_cam(self, index: str):
        camera_pos = camera.position
        camera_rot = camera.rotation
        camera_piv = camera.parent if camera.parent else None

        camera_piv_pos = camera.parent.position if camera_piv else None
        camera_piv_rot = camera.parent.rotation if camera_piv else None

        self.camera_saves[index] = {"position": camera_piv_pos, "rotation": camera_piv_rot, "zoom": camera.z}
        if self.debug:
            print(f"[SaveCam] index={index}")
            print("  pivot pos:", camera_piv_pos)
            print("  pivot rot:", camera_piv_rot)
            print("  cam local pos:", camera_pos)
            print("  cam local rot:", camera_rot)
            print("  zoom:", camera.z)

    def save_cam_to_file(self, index: str):
        self.save_cam(index)

        with open(self._file_path, 'w') as f:
            json.dump(self.camera_saves, f, cls=Vec3Encoder)

    # load cam pos, rot, zoom
    def load_cam(self, index: str):
        if index not in self.camera_saves:
            print("No save at", index)
            return
        
        camera.parent.position = self.camera_saves[index]["position"]
        camera.parent.rotation = self.camera_saves[index]["rotation"]
        camera.parent.target_z = self.camera_saves[index]["zoom"]

        camera.z = self.camera_saves[index]["zoom"]
        camera.parent.target_z = self.camera_saves[index]["zoom"]

        self.current_view = index

    def load_cam_anim(self, index: str, duration: float = 1):
        if index not in self.camera_saves:
            print("No save at", index)
            return

        target = Entity()
        target.position = self.camera_saves[index]["position"]
        target.rotation = self.camera_saves[index]["rotation"]

        camera.parent.add_script(TransformAnimator(target, duration=duration))
        # in_out_expo, in_out_quint, in_out_back
        camera.add_script(OneValueAnimator('z', target_value=self.camera_saves[index]["zoom"], duration=1.25, curve=in_out_expo))
        camera.parent.smoothing_helper.rotation = target.rotation # this only works properly with EditorCamFix

        # camera.z = self.camera_saves[index]["zoom"]
        camera.parent.target_z = self.camera_saves[index]["zoom"]

        self.current_view = index

    def input(self, key):
        if self.toggle_camera_num:
            if key in [str(x) for x in (range(0, 10))]:
                if held_keys["left control"]: # type: ignore
                    self.save_cam(key)
                else:
                    self.load_cam(key)

if __name__ == "__main__":
    from ursina import Ursina
    from painting_on_water.scene_manager import SceneManager

    app = Ursina()
    EditorCamFix()
    
    scn_manager = SceneManager()
    scn_manager.load_scene("blackjack")

    camera_man = CameraMan()

    accumulated_time = 0
    trigger = False

    def update():
        global accumulated_time, trigger
        accumulated_time += time.dt # type: ignore

        if accumulated_time >= 1.5 and not trigger:
            trigger = True
            camera_man.load_cam_anim('1')


    app.run()

