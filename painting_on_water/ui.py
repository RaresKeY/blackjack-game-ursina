from ursina import *  # type: ignore
import painting_on_water.scene_manager as scene_manager

TEXT_SIZE = 1
MARGIN = .01

TOP_LEFT = (-0.5, 0.5)
TOP_CENTER = (0, 0.5)
TOP_RIGHT = (0.5, 0.5)

BOTTOM_LEFT = (-0.5, -0.5)
BOTTOM_CENTER = (0, -0.5)
BOTTOM_RIGHT = (0.5, -0.5)

CENTER_LEFT = (-0.5, 0)
CENTER = (0, 0)
CENTER_RIGHT = (0.5, 0)

class SceneUI:
    """
    UI with top-left toolbar buttons and simple modal windows.
    """
    def __init__(self, scene_manager):
        self.scene_manager = scene_manager
        self._popup_root = None
        self._toolbar = []

        # camera pos and rot saves MOVED TO camera_manager.py
        # self.camera_saves = []
        # self.toggle_camera_num = True

        # --- Toolbar (top-left buttons with simple colors) ---
        btn_save = self.add_button_top_left("Save", base_color=color.azure, on_click=self.show_save_popup)
        btn_load = self.add_button_top_left("Load", last_btn=btn_save, base_color=color.orange, on_click=self.show_load_popup)
        btn_delete = self.add_button_top_left("Delete", last_btn=btn_load, base_color=color.red, on_click=self.show_delete_popup)
        btn_clear = self.add_button_top_left("Clear", last_btn=btn_delete, base_color=color.red, on_click=self.clear_scene)
        btn_spawn = self.add_button_top_left("Spawn", last_btn=btn_clear, base_color=color.orange, on_click=self.show_spawn_popup)
        # btn_save_cam = self.add_button_top_left("Save Cam", last_btn=btn_spawn, base_color=color.orange, on_click=self.save_cam)

        # Blackjack Choices
        self.blackjack_choice = self.blackjack_choices()

        self._key_listener = Entity()
        self._key_listener.input = self._handle_key_input

    @staticmethod
    def add_button_top_left(text: str, *, last_btn=None, on_click=None, base_color=color.azure):
        """Helper to add a button aligned top-left with spacing and simple colors."""
        btn = Button(
            text=text,
            parent=camera.ui,
            text_size=TEXT_SIZE,
            color=base_color, # type: ignore
        )
        btn.fit_to_text(padding=(Vec2(Text.size, Text.size/1.5)))

        if on_click:
            btn.on_click = on_click
        if last_btn:
            btn.x = last_btn.x + last_btn.scale_x/2 + btn.scale_x/2 + MARGIN
            btn.y = last_btn.y
        else:
            btn.x = window.top_left[0] + btn.scale_x/2
            btn.y = window.top_left[1] - btn.scale_y/2
        return btn

    def _handle_key_input(self, key):
        if key == 'escape' and self._popup_root:
            self.close_modal()

        # if self.toggle_camera_num:
        #     if key in [str(x) for x in (range(1, len(self.camera_saves) + 1))]:
        #         self.load_cam(int(key) - 1)


    # ---------- Modal Helpers ----------

    def _open_modal(self):
        self.close_modal()

        self._popup_root = Entity(parent=camera.ui)

        # --- Main Panel ---
        panel = Entity(
            parent=self._popup_root,
            model='quad',
            scale=(.6, .6),  # type: ignore
            color=color.black66,
        )
        return panel

    def close_modal(self):
        if not self._popup_root:
            return
        destroy(self._popup_root)
        self._popup_root = None
        for b in self._toolbar:
            b.enabled = True

    # ---------- Save Popup ----------

    def show_save_popup(self):
        panel = self._open_modal()

        Text('Save Scene', parent=panel, y=.4, scale=3, color=color.white, origin=CENTER)
        Text('Name:', parent=panel, y=.2, x=-.4, origin=(-.5, 0), color=color.white, scale=2.2)

        field = InputField(parent=panel, y=.05, scale=(.8, .12))

        def do_save():
            name = (field.text or '').strip()
            if name:
                self.scene_manager.save_scene(name)
                print('Scene saved as', name)
            self.close_modal()

        Button('Cancel', parent=panel, y=-.35, x=-.2, scale=(.3, .12),
               color=color.red, on_click=self.close_modal)  # type: ignore
        Button('Save', parent=panel, y=-.35, x=.2, scale=(.3, .12),
               color=color.azure, on_click=do_save)  # type: ignore

    # ---------- Load Popup ----------

    def show_load_popup(self):
        panel = self._open_modal()
        Text('Load Scene', parent=panel, origin=CENTER, y=.4, scale=4, color=color.white)

        names = list(getattr(self.scene_manager, '_levels', {}).keys())

        if not names:
            Text('No saved scenes found.', parent=panel, y=0, color=color.white)
            Button('Close', parent=panel, y=-.35, scale=(.3, .12),
                   color=color.red, on_click=self.close_modal)  # type: ignore
            return

        list_container = Entity(parent=panel, y=.2)

        for i, name in enumerate(names):
            Button(
                text=name,
                parent=list_container,
                y=-i * .12,
                scale=(.8, .1),
                color=color.orange,  # type: ignore
                on_click=Func(self._load_and_close, name),
            )

        Button('Cancel', parent=panel, y=-.35, scale=(.3, .12),
               color=color.red, on_click=self.close_modal)  # type: ignore

    def _load_and_close(self, name: str):
        print('Loading scene:', name)
        self.scene_manager.clear_scene()
        self.scene_manager.load_scene(name)
        self.close_modal()

    # ---------- Delete Popup ----------

    def show_delete_popup(self):
        panel = self._open_modal()
        Text('Delete Scene', parent=panel, y=.4, scale=1.5, color=color.white)

        names = list(getattr(self.scene_manager, '_levels', {}).keys())
        if not names:
            Text('No saved scenes found.', parent=panel, y=0, color=color.white)
            Button('Close', parent=panel, y=-.35, scale=(.3, .12),
                   color=color.red, on_click=self.close_modal)  # type: ignore
            return

        list_container = Entity(parent=panel, y=.2)

        for i, name in enumerate(names):
            Button(
                text=f"Delete {name}",
                parent=list_container,
                y=-i * .12,
                scale=(.8, .1),
                color=color.red,  # type: ignore
                on_click=Func(self._delete_and_close, name),
            )

        Button('Cancel', parent=panel, y=-.35, scale=(.3, .12),
               color=color.red, on_click=self.close_modal)  # type: ignore

    def _delete_and_close(self, name: str):
        print('Deleting scene:', name)
        self.scene_manager.delete_scene(name)
        self.close_modal()

    # ---------- Clear Scene ----------

    def clear_scene(self):
        print('Clearing current scene...')
        self.scene_manager.clear_scene()

    # ---------- Spawn Popup ----------

    def show_spawn_popup(self):
        panel = self._open_modal()

        Text('Spawn Card', parent=panel, y=.4, scale=4, color=color.white, origin=CENTER)

        # Input field with clear contrast
        field = InputField(
            parent=panel,
            y=.05,
            scale=(.8, .12),
        )

        def do_spawn():
            value = (field.text or '').strip()
            if value:
                self.scene_manager.spawn_card(value)
                print('Spawned card with:', value)
            self.close_modal()

        Button('Cancel', parent=panel, y=-.35, x=-.2, scale=(.3, .12),
               color=color.red, on_click=self.close_modal)  # type: ignore
        Button('Spawn', parent=panel, y=-.35, x=.2, scale=(.3, .12),
               color=color.lime, on_click=do_spawn)  # type: ignore



    def create_level_buttons(self):
        lvl_btns = []
        size = 5
        for i in range(size):
            lvl_btns.append(Button("Test"))

        for btn in lvl_btns:
            btn.highlight_scale = 0.5
            btn.scale = 0.5
            btn.fit_to_text()
            btn.origin=TOP_LEFT

        return lvl_btns

    def blackjack_choices(self):
        button_group1 = ButtonGroup(["Hit", "Double Down", "Stand"],
                                position=BOTTOM_CENTER, 
                                origin=BOTTOM_CENTER,
                                selected_color=color.black,
                                highlight_color=color.black,
                                min_selection=0)
                    
        return button_group1

    def select_force(self):
        selected = None
        if getattr(self.blackjack_choice, "selected"):
            selected = self.blackjack_choice.selected[0]
            for btn in self.blackjack_choice.selected:
                btn.highlight_color=color.rgba(0.2, 0.2, 0.2, 1)

            self.blackjack_choice.selected=[]

        if selected:
            print(selected)
        return selected


if __name__ == "__main__":
    from ursina import Ursina, EditorCamera
    from painting_on_water.scene_manager import SceneManager
    from painting_on_water.camera_outline import outline_camera_prep

    app = Ursina(msaa=4)
    EditorCamera()

    outline_camera_prep()

    scn_manager = SceneManager()
    scn_manager.load_scene("blackjack")
    ui = SceneUI(scn_manager)

    app.run()
