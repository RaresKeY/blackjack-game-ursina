from ursina import Entity, Vec3, BoxCollider, color, shader, held_keys, mouse, camera, scene, destroy, load_model
from ursina.shaders import ssao_shader
from ursina.collider import MeshCollider
from panda3d.core import SamplerState, BitMask32

BIT = BitMask32.bit(1) # outline show/hide

class GEntity(Entity):
    def __init__(self, *, debug=False, **kwargs):
        # consume custom params out of kwargs so they don’t leak into Entity
        self.collider_path = kwargs.pop("collider_path", "")
        self.class_type = kwargs.pop("class_type", "")
        self.selectable = kwargs.pop("selectable", False)
        self.movable = kwargs.pop("movable", False)
        self.custom_class_param = kwargs.pop("custom_class_param", {})
        collider_value = kwargs.pop("collider", None)   # remove it before Entity sees it

        # pass persist to save in scene/level
        self.persist = kwargs.pop('persist', True)

        super().__init__(
            **kwargs
        )

        # construct collider from custom obj
        if collider_value == "collider" and self.collider_path:
            self.collider_mesh=load_model(self.collider_path)
            self.collider = MeshCollider(self, mesh=self.collider_mesh)
        
        self._prev_traverse_target = None # revert mouse traverse
        self._drag_plane = None # perpendicular to the camera, obj depth
        self._fixed_depth = None
        self._debug = debug
        self.dragging = False
        self.selected = False
        self.drag_offset = Vec3(0, 0, 0) # grab obj where you grab it

        # Pick update method at construction
        if self.movable:
            self.update = self._update_movable
            self.input = self._read_input
        elif self.selectable:
            self.update = self._update_selectable
            self.input = self._read_input
        # cleaner for no logic 
        # else:
        #     self.update = self._update_static

        # Apply filtering right away
        self._set_filtering()

        # set outline as hidde for object
        self.hide(BIT)

    def _set_filtering(self):
        """Apply texture filtering + anisotropy to both sides of the card."""
        if not self.model:
            return
        obj_texture: Texture = self.model.getTexture()   # type: ignore
        if obj_texture:   
            # geometry

            # texture
            obj_texture.setMinfilter(SamplerState.FT_linear_mipmap_linear) # trilinear
            obj_texture.setMagfilter(SamplerState.FT_linear) # bilinear
            obj_texture.setAnisotropicDegree(16)# anisotropic filtering (angle)
            obj_texture.setWrapU(SamplerState.WM_clamp)
            obj_texture.setWrapV(SamplerState.WM_clamp)

    # -------------------------------
    # Screen-aligned plane drag logic
    # -------------------------------

    def _begin_drag_on_screen_plane(self):
        """Create a huge invisible plane at this card's depth, aligned to the screen, and start dragging."""

        cam_forward = camera.forward.normalized()

        # Use click point depth instead of card center
        click_point = mouse.world_point if mouse.world_point is not None else self.world_position
        cam_to_click = click_point - camera.world_position
        self._fixed_depth = cam_to_click.dot(cam_forward)

        # Offset from where you grabbed to the card center
        self.drag_offset = self.world_position - click_point

        # Spawn plane at card depth, facing the camera
        self._drag_plane = Entity(
            parent=scene,
            model='quad',
            world_position=click_point,
            world_rotation=camera.world_rotation,
            scale=300, # type: ignore
            collider='box',
            color=color.hex('#ADD8E6'),
            alpha=0.25,
            visible=self._debug
        )
        self._drag_plane.hide(BIT)

        # Limit mouse raycasts to this plane so mouse.world_point hits it
        self._prev_traverse_target = mouse.traverse_target
        mouse.traverse_target = self._drag_plane

        self.dragging = True

    def _end_drag_on_screen_plane(self):
        """Restore previous mouse traverse target and remove the temporary plane."""
        self.dragging = False
        if self._prev_traverse_target is not None:
            mouse.traverse_target = self._prev_traverse_target
            self._prev_traverse_target = None
        if self._drag_plane is not None:
            destroy(self._drag_plane)
            self._drag_plane = None

    # -------------------------------

    def _compute_corrected_drag_point(self) -> Vec3 | None:
        """Project mouse ray onto fixed-depth plane, then apply grab offset."""
        if mouse.world_point is None:
            return None

        # Ray from camera through mouse hit
        r = (mouse.world_point - camera.world_position).normalized()
        cam_forward = camera.forward.normalized()
        denom = r.dot(cam_forward)

        if abs(denom) > 1e-6:
            t = self._fixed_depth / denom
            P_corr = camera.world_position + r * t
        else:
            P_corr = mouse.world_point

        if self._debug:
            print(f"fixed_depth={self._fixed_depth}, P_corr={P_corr}")

        return P_corr + self.drag_offset

    def _read_input(self, key):
        if self.hovered and key == "left mouse down":
            self._begin_drag_on_screen_plane()
            if not held_keys['shift']: # type: ignore
                # remove other selections if shift not held
                for e in scene.children:
                    other_sel = getattr(e, "selected", None)
                    if other_sel:
                        e.selected = False
            self.selected = True
        
        if key == "left mouse up":
            self._end_drag_on_screen_plane()

        if key == "escape":
            self.selected = False

    # --- update variants ---
    def _update_movable(self):
        """movable"""
        if self.hovered:
            self.show(BIT)
            # self.color = color.yellow
        elif not self.dragging and not self.selected:
            self.hide(BIT)
            # self.color = color.white

        # move logic
        if self.dragging and self._drag_plane is not None:
            self._drag_plane.world_rotation = camera.world_rotation
            corrected = self._compute_corrected_drag_point()
            if corrected is not None:
                self.world_position = corrected

    def _update_selectable(self):
        """selectable"""
        if self.hovered:
            self.show(BIT)
        else:
            self.hide(BIT)
    
    def _update_static(self):
        """stub for later static logic"""
        # no custom logic per frame
        return

if __name__ == "__main__":
    from ursina import Ursina, EditorCamera
    from ursina.shaders import ssao_shader
    from panda3d.core import SamplerState, Texture, BitMask32
    from camera_outline import outline_camera_prep

    app = Ursina(msaa=4)

    outline_camera_prep() # outline + camera settings

    path = "Assets/Table/"

    # test object
    table = GEntity(model=path + "Table.obj",
                    texture= path + "table_texture2.png",
                    movable=True)
    
    # add simplified collider
    table.collider = MeshCollider(table, mesh=load_model(path + "Table_Collider.obj"), center=Vec3(0,0,0))

    # Scene
    EditorCamera()

    # def update():
    #     """"""

    app.run()

