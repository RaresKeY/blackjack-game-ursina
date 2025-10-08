from ursina import Entity, Ursina, EditorCamera, color, time, slerp, lerp, scene
from ursina.curve import in_out_expo, in_out_quint, in_out_back

# TODO: fix relative and world transforms proper
# right now it needs world target always

class TransformAnimator:
    def __init__(self, target: Entity, duration=1.0, curve=in_out_expo, debug=False):
        self.target = target
        self.duration = duration
        self.curve = curve
        self.t = 0
        self.done = False
        self.initialized = False
        self.debug = debug

        if debug:
            original_update = self.update
            def wrapped_update():
                print("1", end='')
                if self.done: 
                    if self.debug: print(f"Removing {self} from {self.entity}")   # type: ignore
                return original_update()
            self.update = wrapped_update

    def _capture_start_state(self):
        self.start_pos = self.entity.world_position     # type: ignore
        self.start_scale = self.entity.world_scale      # type: ignore
        self.start_rot = self.entity.quaternion         # type: ignore # entity.getQuat(scene) # entity.quaternion

        self.target_pos = self.target.world_position
        self.target_scale = self.target.world_scale
        self.target_rot = self.target.quaternion

        self.initialized = True

    def update(self):
        if self.done:
            self.entity.scripts.remove(self)   # type: ignore
            return

        if not self.initialized:
            if not hasattr(self, "entity"):
                return
            self._capture_start_state()

        self.t += time.dt / self.duration   # type: ignore
        if self.t >= 1:
            self.t = 1
            self.done = True

        # apply curve
        eased_t = self.curve(self.t)

        # Lerp position and scale
        self.entity.world_position = lerp(self.start_pos, self.target_pos, eased_t)  # type: ignore
        self.entity.world_scale = lerp(self.start_scale, self.target_scale, eased_t) # type: ignore

        # Slerp rotation
        q = slerp(self.start_rot, self.target_rot, eased_t)
        self.entity.quaternion = q # type: ignore # .quaternion = q


class OneValueAnimator:
    def __init__(self, prop: str, target_value, duration=1.0, curve=in_out_expo, debug=False):
        self.prop = prop                # property name as string
        self.target_value = target_value
        self.duration = duration
        self.curve = curve
        self.t = 0
        self.done = False
        self.start_value = None
        self.initialized = False
        self.debug = debug

    def _capture_start(self):
        # self.entity is auto set by Ursina 
        self.start_value = getattr(self.entity, self.prop) # type: ignore
        self.initialized = True

    def update(self):
        if self.done:
            self.entity.scripts.remove(self)  # type: ignore
            return

        if not self.initialized:
            if not hasattr(self, "entity"):
                return
            self._capture_start()

        self.t += time.dt / self.duration  # type: ignore
        if self.t >= 1:
            self.t = 1
            self.done = True

        eased_t = self.curve(self.t)
        new_val = lerp(self.start_value, self.target_value, eased_t)
        setattr(self.entity, self.prop, new_val)  # type: ignore

        if self.debug:
            print(f"{self.entity} {self.prop}: {getattr(self.entity, self.prop)}")  # type: ignore



# cool ones:
#   in_out_back
#   in_out_expo

if __name__ == "__main__":
    from painting_on_water.card import Card

    app = Ursina()

    animated = Card(front_texture="KH.png", position=(-2, -1, 0))  # type: ignore
    target = Entity(position=(2, 1, 0), scale=1, rotation=(45, 90, 0))  # type: ignore
    target.scale = animated.scale
    animated.scale= 0
    # print(animated.scripts)

    EditorCamera()

    def input(key):
        if key == 'space':
            animated.position = (-2, -1, 0)
            animated.scale = 0
            animated.rotation = (0, 0, 0)
            animated.add_script(TransformAnimator(target, duration=1.5, curve=in_out_expo, debug=True))

    app.run()
