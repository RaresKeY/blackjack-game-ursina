from ursina import Entity, EditorCamera, time, Vec3, held_keys, color, camera, scene, mouse, destroy, window
from painting_on_water.card import Card
from painting_on_water.gentity import GEntity
from panda3d.core import Quat, BitMask32, LQuaternionf
import math
import numpy as np
from painting_on_water.camera_manager import EditorCamFix

# ------- type hints --------------
from typing import cast
hk = cast(dict[str, bool], held_keys)
# ------- type hints --------------

BIT = BitMask32.bit(1) 

# [x] todo: Expand copy/paste properly
# [x] todo: Implement focus on group

class BlenderCamera(EditorCamFix):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # camera views (pos, rot, fov)
        self.mode = "view"
        self.saved_views = {}

        # selected entities
        self.selected_ents: list = [] # selected entities
        self._clipboard: list = [] # copied entities

        # transform state
        self.transform_mode = None   # "move", "rotate", "scale"
        self.transform_axis = None   # "x", "y", "z", or None

        self._start_scale = self.scale

        # save transforms state: Entity -> Snapshot
        self.transforms_snapshot()

        # pivot/origin for multiple selects
        self._pivot = None
        self._pivot_start_rot = Quat()
        self._original_parents = {} # for restore origins

        # mouse stuff
        self._start_mouse = mouse.position
        self._mouse_last_pos = mouse.position   # for wrap logic
        
        self._debug = True

    def update(self):
        super().update()
        speed = 5 * time.dt # type: ignore

        if hk['shift']:
            speed *= 3

        # Fly navigation
        # if hk['w']: self.position += self.forward * speed
        # if hk['s']: self.position -= self.forward * speed
        # if hk['a']: self.position -= self.right * speed
        # if hk['d']: self.position += self.right * speed
        # if hk['q']: self.position -= self.up * speed
        # if hk['e']: self.position += self.up * speed

        # Wrap mouse around while transform
        if self.transform_mode:
            self.wrap_mouse()

        # Mouse-driven transform
        if self.selected_ents and self.transform_mode:
            if self.transform_mode == 'rotate':
                fine = 0.2 if hk['shift'] else 1.0 # [ ] TODO: start from new position when changing moode without breaking cancel/send
                dx = (mouse.position[0] - self._start_mouse[0]) * 10 * fine
                dy = (mouse.position[1] - self._start_mouse[1]) * 10 * fine
                if not self._pivot:
                    return

                # Blender-like: dx -> Y, -dy -> X/Z
                if   self.transform_axis == 'x': delta = -dy * 45
                elif self.transform_axis == 'z': delta = -dy * 45
                else:                            delta =  dx * 45  # default Y

                if hk['control']:
                    step = 15
                    delta = round(delta / step) * step
                
                local_x = self._pivot_start_rot.xform(Vec3(1,0,0))
                local_y = self._pivot_start_rot.xform(Vec3(0,1,0))
                local_z = self._pivot_start_rot.xform(Vec3(0,0,1))

                step = Quat()
                if self.transform_axis == 'x':
                    step.setFromAxisAngle(delta, local_x)  # spin around local X-axis
                elif self.transform_axis == 'z':
                    step.setFromAxisAngle(delta, local_y)  # spin around local Z-axis
                else:
                    step.setFromAxisAngle(delta, local_z)  # spin around local Y-axis

                self._pivot.quaternion = self._pivot_start_rot * step

            else:
                for ent in self.selected_ents:
                    fine = 0.2 if hk['shift'] else 1.0
                    dx = (mouse.position[0] - self._start_mouse[0]) * 10 * fine
                    dy = (mouse.position[1] - self._start_mouse[1]) * 10 * fine

                    if self.transform_mode == 'move':
                        state = self._start_state[ent]
                        offset = Vec3(dx, dy, 0)
                        if self.transform_axis == 'x': offset = Vec3(dx, 0, 0)
                        elif self.transform_axis == 'y': offset = Vec3(0, dy, 0)
                        elif self.transform_axis == 'z': offset = Vec3(0, 0, dy)

                        new_pos = state['pos'] + offset
                        if hk['control']:
                            snap = 0.5
                            new_pos = Vec3(
                                round(new_pos.x / snap) * snap, # type: ignore
                                round(new_pos.y / snap) * snap, # type: ignore
                                round(new_pos.z / snap) * snap, # type: ignore
                            )
                        ent.position = new_pos

                    elif self.transform_mode == 'scale':
                        factor = 1 + dx * 0.1
                        factor = max(0.01, factor)
                        if hk['control']:
                            factor = round(factor, 1)

                        if self.transform_axis == 'x':
                            ent.scale_x = self._start_scale[0] * factor
                        elif self.transform_axis == 'y':
                            ent.scale_y = self._start_scale[1] * factor
                        elif self.transform_axis == 'z':
                            ent.scale_z = self._start_scale[2] * factor
                        else:
                            mult_x = getattr(ent, "card_height", 1)
                            mult_y = getattr(ent, "card_length", 1)
                            ent.scale = (self._start_scale.x * factor * mult_x,
                                         self._start_scale.y * factor * mult_y,
                                         self._start_scale.z * factor)

    def input(self, key):
        super().input(key)
        # print("DEBUG key:", key)

        # camera view modes
        if key == 'f1': self.mode = "view"; print("Mode: VIEW")
        if key == 'f2': self.mode = "save"; print("Mode: SAVE/LOAD")

        if hk["end"]: self._handle_view(1, Vec3(0, 0, 0))
        if hk["page down"]: self._handle_view(3, Vec3(0, 90, 0))
        if hk["home"]: self._handle_view(7, Vec3(90, 0, 0))
        if hk['5']: 
            camera.orthographic = not camera.orthographic
            camera.fov = 1 if camera.orthographic else 90
            print("Orthographic:", camera.orthographic)

        if hk['4'] and hk['left arrow']: self.rotation_y += 15
        if hk['6'] and hk['right arrow']: self.rotation_y -= 15
        if hk['8'] and hk['up arrow']: self.rotation_x += 15
        if hk['2'] and hk['down arrow']: self.rotation_x -= 15

        # Blender-style transforms
        self.selected_ents = [e for e in scene.entities if getattr(e, "selected", False)]
        if self._pivot:
            self.selected_ents += [e for e in self._pivot.children if getattr(e, "selected", False)]

        if self.selected_ents:
            # when entering rotate mode
            # TODO: unify and generalize transforms
            if key == 'r':
                # if we are already in a transform, cancel it first
                if self.transform_mode:
                    self.cancel_transform()

                self.transform_mode = 'rotate'
                self.transform_axis = None
                self._start_mouse = mouse.position

                # snapshot for cancel/axis lock
                self.transforms_snapshot()

                # group center
                center = Vec3(sum([e.world_position for e in self.selected_ents], Vec3(0,0,0)) / len(self.selected_ents))

                # make pivot
                self._pivot = Entity(position=center, model="cube", scale=0.05, color=color.rgba(0, 0, 0, 0.2)) # type: ignore
                self._pivot.quaternion = self.average_quats()
                self._pivot_start_rot = self._pivot.quaternion # baseline

                # [ ] TODO: Clean parenting mess
                if self._original_parents:
                    self._original_parents = {}

                # reparent selected
                for ent in self.selected_ents:
                    self._original_parents[ent] = ent.world_parent
                    ent.world_parent = self._pivot


                print("Transform mode: ROTATE (pivot parenting)")

            # TODO: generalize transforms around self origin
            if key in ('g','s'):
                if self.transform_mode: # if we are already in a transform, cancel it first
                    self.cancel_transform()

                self.transform_mode = {'g':'move','s':'scale'}[key]
                self.transform_axis = None
                self._start_mouse = mouse.position
                self.transforms_snapshot()
                print(f"Transform mode: {self.transform_mode.upper()} (free)")

            # Select transform axis/mode
            if key in ('x','y','z') and self.transform_mode:
                self.sel_transform_mode(key)

            # Apply Transform
            if key in ('enter','return','left mouse down') and self.transform_mode:
                self.apply_transform()
            
            # Clear selected if not mid-transform
            elif key in('left mouse down') and not mouse.hovered_entity:
                self.clear_selected()

            # Cancel transform
            if key in ['escape', "right mouse down"] and self.transform_mode:
                self.cancel_transform()

            # Focus on selected entities combined origin
            if key in ['.', 'delete']:
                self.focus_selected()

            # Copy selected entities
            if key == 'c' and hk['control'] and self.selected_ents:
                self.clipboard_copy()

            # Paste selected entities
            if key == 'v' and hk['control'] and hasattr(self, '_clipboard'):
                self.clipboard_paste()

            # Delete selected entities
            if key == '*':
                self.delete_cards()

    def transforms_snapshot(self):
        self._start_state = {
            ent: {
                'pos': Vec3(ent.position),
                'rot': Vec3(ent.rotation),
                'scale': Vec3(ent.scale),
            } for ent in self.selected_ents
        }

    def sel_transform_mode(self, key):
        # If we are in rotate mode, reset the pivot's rotation
        if self.transform_mode == 'rotate' and self._pivot:
            self._pivot.quaternion = self._pivot_start_rot

        else:
            for ent in self.selected_ents:
                state = self._start_state[ent]
                ent.position = state["pos"]
                ent.rotation = state["rot"]
                ent.scale = state["scale"]
                self.transform_axis = key
                print(f"Axis locked to {key.upper()}")

        # Set the new axis and reset the mouse start position to prevent jumps
        self.transform_axis = key
        self._start_mouse = mouse.position
        if self._debug:
            print(f"Axis locked to {key.upper()}")

    def focus_selected(self):
        self.position = sum([e.world_position for e in self.selected_ents], Vec3(0,0,0)) / len(self.selected_ents)
        if self._debug: 
            print("Focused on selected")

    def delete_cards(self):
        for ent in self.selected_ents:
            # delete all selected Cards
            if ent.__class__.__name__ == "Card":
                ent.destroy()
                ent = None

            if self._debug and not ent: 
                print("Deleted:", type(ent).__name__)
                
        self.clear_selected()

    def clipboard_copy(self):
        self._clipboard = []
        for ent in self.selected_ents:
            self._clipboard.append({
                        'class_type': ent.__class__.__name__,
                        'model': getattr(ent, 'model', None),
                        'texture': getattr(ent, 'texture', None),
                        'color': getattr(ent, 'color', None),
                        'scale': Vec3(ent.scale),
                        'rotation': Vec3(ent.rotation),
                        'position': Vec3(ent.position),
                    })
        print("Copied entities to clipboard")

    def clipboard_paste(self):
        all_data = self._clipboard
        for ent in self.selected_ents:
            ent.selected = False
        for data in all_data:
            if data["class_type"] == "Entity":
                new_ent = Entity(
                    model=data['model'],
                    texture=data['texture'],
                    color=data['color'],
                    scale=data['scale'],
                    rotation=data['rotation'],
                    position=data['position'],
                    parent=scene,
                )
            elif data["class_type"] == "Card":
                new_ent = Card(
                    model=data['model'],
                    front_texture=data['texture'],
                    color=data['color'],
                    scale=data['scale'],
                    rotation=data['rotation'],
                    position=data['position'],
                    parent=scene,
                )
            new_ent.selected = True
            print("Pasted entity")
            self.selected_ents.append(new_ent)

    def apply_transform(self):
        self.restore_parenting()

        if self._pivot:
            destroy(self._pivot)
            self._pivot = None

        self.transform_mode = None
        self.transform_axis = None

        if self._debug: print(f"Applied {self.transform_mode} on {self.transform_axis or 'free'} axis")

    def clear_selected(self):
        for ent in self.selected_ents:
            setattr(ent, "selected", False)

        self.selected_ents.clear()

    def cancel_transform(self):
        if self._debug: print("Transform cancelled")

        self.restore_parenting()

        for ent in self.selected_ents:
            state = self._start_state.get(ent)
            
            if not state:
                continue

            ent.position = state["pos"]
            ent.rotation = state["rot"]
            ent.scale = state["scale"]

        self.transform_mode = None
        self.transform_axis = None

        if self._pivot:
            destroy(self._pivot)
            self._pivot = None

    def restore_parenting(self):
        """Safely restore world_parent for all selected entities."""
        if not self.selected_ents:
            return
        
        for ent in list(self.selected_ents):
            if not ent:  # entity itself gone
                continue

            parent = self._original_parents.get(ent, scene)
            if not parent:
                parent = scene

            try:
                ent.world_parent = parent
            except Exception as e:
                print(f"Failed to restore parent for {ent}: {e}")

        self._original_parents.clear()

    def _handle_view(self, slot: int, rotation: Vec3):
        if self.mode == "view":
            self.rotation = rotation
        elif self.mode == "save":
            if slot in self.saved_views:
                pos, rot = self.saved_views[slot]
                self.position = pos
                self.rotation = rot
                print(f"Loaded camera slot {slot}")
            else:
                self.saved_views[slot] = (self.position, self.rotation)
                print(f"Saved camera slot {slot}")
            print("Orthographic:", self.orthographic)

    def wrap_mouse(self, margin=0.04): # [x] todo: fix (I fixed it poorly)
        """Blender-like cursor wrapping at window borders."""
        self._mouse_last_pos = mouse.position

        if not mouse.locked:   # only when unlocked
            # Horizontal wrapping
            if mouse.x <= window.left[0] + margin:
                mouse.x = window.right[0] - margin
            elif mouse.x >= window.right[0] - margin:
                mouse.x = window.left[0] + margin

            # Vertical wrapping
            if mouse.y <= window.bottom[1] + margin:
                mouse.y = window.top[1] - margin
            elif mouse.y >= window.top[1] - margin:
                mouse.y = window.bottom[1] + margin

        if mouse.is_outside:
            mouse.position = self._mouse_last_pos
            if self._debug: print(f'[DEBUG] mouse left window')

    @staticmethod
    def slerp_custom(q1: Quat, q2: Quat, t: float) -> Quat:
        # Ensure shortest path
        dot = q1.dot(q2)
        if dot < 0.0:
            # flip one to take the shorter arc
            q2 = Quat(-q2.get_w(), -q2.get_x(), -q2.get_y(), -q2.get_z())
            dot = -dot

        # clamp dot
        if dot > 0.9995:
            # If very close, use linear interpolation and normalize
            result = q1 + (q2 - q1) * t
            result.normalize()
            return result

        theta_0 = math.acos(dot)        # angle between quaternions
        sin_theta_0 = math.sin(theta_0)

        theta = theta_0 * t
        sin_theta = math.sin(theta)

        s0 = math.sin(theta_0 - theta) / sin_theta_0
        s1 = sin_theta / sin_theta_0

        return (q1 * s0) + (q2 * s1)

    def average_quats(self):
        # collect quaternions
        quats = [e.quaternion for e in self.selected_ents]
        if not quats:
            return Quat()
        
        # first quat
        final_quat = quats[0]

        for i in range(1, len(quats)):
            # guard lock
            if final_quat.dot(quats[i]) < 0.0:
                quats[i] = -quats[i]

            # next quat, avg as 1/2, 1/3, 1/4 ... 1/n
            final_quat = self.slerp_custom(final_quat, quats[i], 1.0 / (i + 1))
            final_quat.normalize()

        return final_quat

        # # sum components
        # w = sum(q.w for q in quats)
        # x = sum(q.x for q in quats)
        # y = sum(q.y for q in quats)
        # z = sum(q.z for q in quats)

        # # normalize back to unit quaternion
        # length = (w*w + x*x + y*y + z*z) ** 0.5
        # if length == 0:
        #     return Vec3(0,0,0)

        # w /= length; x /= length; y /= length; z /= length

        # # make a quaternion again
        # return Quat(w, x, y, z)
    
    # better representation of mean, doesn't work properly, idk, prob global space bullshit
    def average_quaternion_markley(self):
        quats = [e.quaternion for e in self.selected_ents]

        if not quats:
            return Quat()  # identity

        # Collect normalized [w,x,y,z] rows
        rows = []
        for q in quats:
            w, x, y, z = q.get_w(), q.get_x(), q.get_y(), q.get_z()
            v = np.array([w, x, y, z], dtype=np.float64)
            n = np.linalg.norm(v)
            if n == 0: 
                continue
            rows.append(v / n)

        if not rows:
            return Quat()

        Q = np.stack(rows)                           # shape: (N,4)
        A = (Q.T @ Q) / Q.shape[0]                   # 4x4 symmetric accumulator
        vals, vecs = np.linalg.eigh(A)               # guaranteed real-symmetric
        avg = vecs[:, vals.argmax()]                 # principal eigenvector

        # Fix hemisphere relative to first input
        if np.dot(avg, Q[0]) < 0:
            avg = -avg

        # RETURN ORDER: if your Quat ctor is (w,x,y,z), use this:
        return Quat(float(avg[0]), float(avg[1]), float(avg[2]), float(avg[3]))
        
    
if __name__ == "__main__":
    from ursina import Ursina, EditorCamera, Entity
    from painting_on_water.camera_outline import outline_camera_prep
    from painting_on_water.gentity import GEntity
    from painting_on_water.scene_manager import SceneManager
    from painting_on_water.ui import SceneUI 

    app = Ursina(msaa=4, position=(100, 200))

    camera.fov = 75

    camera_editor = BlenderCamera()

    outline_camera_prep()

    scn_manager = SceneManager()
    ui = SceneUI(scn_manager)

    app.run()
