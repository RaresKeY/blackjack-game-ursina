from ursina import Entity, Vec3, color, mouse, camera, scene, destroy, held_keys
from panda3d.core import SamplerState, BitMask32
from painting_on_water.animators import TransformAnimator
from painting_on_water import resource_path_rel
import sys
import os

BIT = BitMask32.bit(1) # outline show/hide
# PATH_C = "Assets/Cards/" # TODO: remove testing, uncomment final, works with /tmp root? probably ursina recursively looking
PATH_C = resource_path_rel("Assets/Cards/")

CARD_HEIGHT = 1000 / 1050
CARD_LENGTH = 1000 / 750

class Card(Entity):
    def __init__(self, front_texture, back_texture=PATH_C + "card_back/zback.png", debug=False, **kwargs):
        self.card_height = 1000 / 1050
        self.card_length = 1000 / 750

        # consume custom params out of kwargs so they don’t leak into Entity
        self.collider_path = kwargs.pop("collider_path", "")
        self.class_type = kwargs.pop("class_type", "")
        self.selectable = kwargs.pop("selectable", False)
        self.movable = kwargs.pop("movable", False)
        self.custom_class_param = kwargs.pop("custom_class_param", {})

        # card specific when spawned by manager
        kwargs.pop("model", None)
        kwargs.pop("texture", None)
        kwargs.pop("scale", None)
        kwargs.pop("collider", None)

        # pass persist to save in scene/level
        self.persist = kwargs.pop('persist', True)

        super().__init__(
            model="quad",
            texture=front_texture,
            scale=Vec3(1 * self.card_height, 1 * self.card_length, 1),
            collider="box",
            **kwargs
        )
        # Back side
        self.back_side = Entity(
            model="quad",
            texture=back_texture,
            rotation_y=180,
            parent=self
        )

        self._debug = debug

        self._prev_traverse_target = None # revert mouse traverse
        self._drag_plane = None # perpendicular to the camera, card depth
        self._fixed_depth = None
        self._snap_object = self
        self.dragging = False
        self.drag_offset = Vec3(0, 0, 0) # grab card where you grab it
        self.selected = False

        # transforms
        self._original_rot = self.rotation
        self._original_pos = self.position
        self._original_scale = self.scale

        # Apply filtering right away
        self._set_filtering()

        # set outline as hidde for object
        self.hide(BIT)

    def __str__(self):
        return self.custom_class_param["name"]
    
    def _set_filtering(self):
        """Apply texture filtering + anisotropy to both sides of the card."""
        tex_front: Texture = self.model.getTexture()   # type: ignore
        if tex_front:   
            # geometry

            # texture
            tex_front.setMinfilter(SamplerState.FT_linear_mipmap_linear) # trilinear
            tex_front.setMagfilter(SamplerState.FT_linear) # bilinear
            tex_front.setAnisotropicDegree(16)# anisotropic filtering (angle)
            tex_front.setWrapU(SamplerState.WM_clamp)
            tex_front.setWrapV(SamplerState.WM_clamp)

        tex_back = self.back_side.model.getTexture()   # type: ignore
        if tex_back:
            tex_back.setMinfilter(SamplerState.FT_linear_mipmap_linear)
            tex_back.setMagfilter(SamplerState.FT_linear)
            tex_back.setAnisotropicDegree(16)
            tex_back.setWrapU(SamplerState.WM_clamp)
            tex_back.setWrapV(SamplerState.WM_clamp)


    # Object-aligned plane drag logic
    def _begin_drag_on_selected_surface(self, surface=None):
        if surface is None:
            surface = self._snap_object

        # ray through card
        # compute position on plane based on ray (from camera)
        # select offset point on card with previous logic
        # use given drag plane directly for mouse
        # drag across selected plane with prebious logic
        
        return
    

    # Screen-aligned plane drag logic
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
        
    def input(self, key):
        main_script = os.path.basename(sys.argv[0])   # e.g. "blender_cam.py"

        if self.hovered and key == "left mouse down":
            if not held_keys['shift']: # type: ignore
                for e in scene.entities:
                    other_sel = getattr(e, "selected", None)
                    if other_sel:
                        e.selected = False

            self.selected = True
            print("DEBUG:", self.position)

        if main_script == "blender_cam.py":
            return
        
        # similar logic to blender_cam.py
        # TODO: re-implement for gameplay with surface choosing
        if self.hovered and key == "left mouse down":
            self._begin_drag_on_screen_plane()
            if not held_keys['shift']: # type: ignore
                for e in scene.children:
                    other_sel = getattr(e, "selected", None)
                    if other_sel:
                        e.selected = False

            self.selected = True
        
        if key == "left mouse up":
            self._end_drag_on_screen_plane()

        if key == "escape":
            self.selected = False

    def move_to(self, new_pos):
        self.position = new_pos

    def move_anim(self, target, duration):
        self.add_script(TransformAnimator(target, duration))

    def rotate(self, new_rot):
        self.rotation = new_rot

    def size(self, new_scale):
        self.scale = new_scale

    def reset_transform(self):
        self.rotation = self._original_rot
        self.position = self._original_pos
        self.scale = self._original_scale

    def lock_transform(self):
        self._original_rot = self.rotation
        self._original_pos = self.position
        self._original_scale = self.scale

    def update(self):
        """Highlight the card when hovered."""
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

    def destroy(self):
        """Cleanly remove the card and its extras."""
        # clean up drag plane if one exists
        if self._drag_plane is not None:
            destroy(self._drag_plane)
            self._drag_plane = None

        # clean up back side (in case it's not parented correctly)
        if self.back_side is not None and not self.back_side.parent:
            destroy(self.back_side)
            self.back_side = None

        # finally destroy this entity itself
        destroy(self)


if __name__ == "__main__":
    from ursina import Ursina, EditorCamera
    from ursina.curve import in_out_expo
    from panda3d.core import SamplerState, Texture, BitMask32
    from painting_on_water.camera_outline import outline_camera_prep

    app = Ursina(msaa=4)

    outline_camera_prep() # outline + camera settings

    # new cards
    new_card = Card(PATH_C + "card_pack/QH.png")
    new_card.scale = 0
    target1 = Entity(position=(2, 1, 0), scale=Vec3(1 * CARD_HEIGHT, 1 * CARD_LENGTH, 1), rotation=(45, 20, 0))  # type: ignore

    another_new_card = Card(PATH_C + "card_pack/QC.png", x=2)
    another_new_card.scale = 0
    target2 = Entity(position=(0, 1, 1), scale=Vec3(1 * CARD_HEIGHT, 1 * CARD_LENGTH, 1), rotation=(0, 30, 0))  # type: ignore

    EditorCamera()

    def input(key):
        if key == 'space':
            new_card.position = (0, 0, 0)
            new_card.scale = 0
            new_card.rotation = (0, 0, 0)
            new_card.add_script(TransformAnimator(target1, duration=1.5, curve=in_out_expo))

            another_new_card.position = (2, 0, 0)
            another_new_card.scale = 0
            another_new_card.rotation = (0, 0, 0)
            another_new_card.add_script(TransformAnimator(target2, duration=1.5, curve=in_out_expo))


    app.run()