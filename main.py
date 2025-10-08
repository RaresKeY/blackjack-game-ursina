from panda3d.core import loadPrcFileData
loadPrcFileData("", "framebuffer-multisample 1")
loadPrcFileData("", "multisamples 8")   # 4, 8, or 16 if GPU supports
from pathlib import Path
from ursina import Ursina, Entity, Audio, Vec3, MeshCollider, Text, Button, DirectionalLight, AmbientLight, \
    time, color, application, \
    invoke, load_model, destroy, \
    window, camera, scene
from ursina.shaders import fxaa_shader, ssao_shader
from ursina.curve import in_out_circ, in_out_expo, in_out_quint
from panda3d.core import BitMask32
from painting_on_water.camera_outline import outline_camera_prep
from painting_on_water.card import Card
from painting_on_water.gentity import GEntity
from painting_on_water.scene_manager import SceneManager
from painting_on_water.animators import TransformAnimator
from painting_on_water.lut_tables_2 import LTable
from blackjack_logic import BlackjackLogic
from painting_on_water.camera_manager import CameraMan
from painting_on_water.blender_cam import BlenderCamera
from painting_on_water.simple_scheduler import ScheduleSeq
from painting_on_water import resource_path_rel
import os, math, random, json, copy

PATH_C = resource_path_rel("Assets/Cards/")
PATH_T = resource_path_rel("Assets/Table/")
PATH_D = resource_path_rel("Assets/Data/")

# PATH_C = "Assets/Cards/"
# PATH_T = "Assets/Table/"
# PATH_D = "Assets/Data/"

BIT = BitMask32.bit(1) # outline show/hide
DEBUG = False

MARGIN = 0.005

TOP_LEFT = (-0.5, 0.5)
TOP_CENTER = (0, 0.5)
TOP_RIGHT = (0.5, 0.5)

BOTTOM_LEFT = (-0.5, -0.5)
BOTTOM_CENTER = (0, -0.5)
BOTTOM_RIGHT = (0.5, -0.5)

CENTER_LEFT = (-0.5, 0)
CENTER = (0, 0)
CENTER_RIGHT = (0.5, 0)

CARD_HEIGHT = 1000 / 1050
CARD_LENGTH = 1000 / 750

# [x] todo: Reset slots
# [x] todo: Print Busted on screen (over everything) 
# [ ] TODO: add variable bets and betting logic and timing
# [ ] TODO: make clean Table asset

os.makedirs('models_compressed/Assets/Table', exist_ok=True)
os.makedirs('models_compressed/Assets/Cards/card_pack', exist_ok=True)

def find_runtime_root() -> Path:
    # e.g. /tmp/onefile_xxx/painting_on_water/main.py -> climb until we see Assets
    here = Path(__file__).resolve()
    for d in [here.parent, here.parent.parent, here.parent.parent.parent]:
        if (d / "Assets").exists():
            return d
    return here.parent

RUNTIME_ROOT = find_runtime_root()
application.asset_folder = RUNTIME_ROOT
os.chdir(RUNTIME_ROOT)  # <-- makes open('Assets/...') work

with open(Path(PATH_D + "card_positions_4_test.json"), 'r') as f:
    table_card_slots = json.load(f)

sys_rand = random.SystemRandom()

app = Ursina(development_mode=False, borderless=False, fullscreen=False)

outline_camera_prep() # outline + camera settings
lut_table = LTable(step=0.01, radians=True)

# cameras = {
#     "default": {
#         "position": camera.position,
#         "rotation": camera.rotation
#         },yes
#     "start_game": {
#         "position": Vec3(0.49305558, -1.2152778, -6.113426),
#         "rotation": Vec3(0, 45, 0)
#     }
# }

def preload_deck(folder=Path(PATH_C) / "card_pack",
                 center=Vec3(0,0,0)):
    textures = [os.path.join(folder, f) for f in os.listdir(folder) if f.endswith(".png")]
    textures.sort()
    cards = []
    for tex in textures:
        card = Card(front_texture=resource_path_rel(tex), position=center, rotation=(0,0,0), 
                    custom_class_param={"name": str(tex).removesuffix(".png").removeprefix(str(folder) + '/')})
        
        # print(f"DEBUG (tex): {resource_path_rel(tex)}")
        # print(f"DEBUG (folder): {folder}")
        card.scale=0
        cards.append(card)
        
    sys_rand.shuffle(cards)
    return cards

def value_check(v):
    if isinstance(v, (float, int)) and math.isnan(v):
        raise ValueError(f"NaN detected in {v}")
    if isinstance(v, (float, int)) and math.isinf(v):
        raise ValueError(f"Inf detected in {v}")

class TornadoController(Entity):
    def __init__(self, center=Vec3(0,0,0),
                 radius_x=2.0, radius_y=3.0, radius_z=2.0,
                 turns=12, duration=1.2, delay=0.02,
                 card_height=1000/1050, card_length=1000/750,
                 debug=DEBUG):
        super().__init__(position=center)
        self.cards = []
        self.active = False
        self.radius_x = radius_x
        self.radius_y = radius_y
        self.radius_z = radius_z
        self.turns = turns
        self.duration = duration
        self.delay = delay
        self.card_height = card_height
        self.card_length = card_length
        self.anchors = []
        self.debug = debug

    def add_cards(self, cards):
        self.cards = cards
        total = len(cards)

        golden_angle = math.pi * (3 - math.sqrt(5))
        jitter_strength = 0.05      # tweak for randomness
        sphere_radius = 1           # new global radius control

        for i, card in enumerate(cards):
            t = (i + 0.5) / total
            
            # uniform z in [-1,1], jittered
            z = 1 - 2 * t
            z += random.uniform(-jitter_strength, jitter_strength) / total
            z = max(-1, min(1, z))  # clamp

            phi = lut_table.acos_lut(z)
            value_check(phi)
            theta = i * golden_angle + random.uniform(-jitter_strength, jitter_strength)

            # Cartesian coords, scaled by sphere_radius
            x = lut_table.sin_lut(phi) * lut_table.cos_lut(theta) * sphere_radius * self.radius_x
            value_check(x)
            y = z * sphere_radius * self.radius_y * 0.7
            zv = lut_table.sin_lut(phi) * lut_table.sin_lut(theta) * sphere_radius * self.radius_z
            value_check(zv)

            target = Entity(
                position=Vec3(x, y, zv),
            )
            self.anchors.append(target)

            target.parent = self
            target.scale = Vec3(CARD_HEIGHT, CARD_LENGTH, 0.1)
            target.rotation = Vec3(random.uniform(-15, 15),
                                   random.uniform(0, 360),
                                   random.uniform(-15, 15))
            
            target.name = card.custom_class_param["name"]
            target.hide(BIT)

            # DEBUG POINT 
            if self.debug:
                print("\n TARGET_NAME", target.name)
                debug_point = Entity(model="sphere", world_parent=target, scale=Vec3(0.1, 0.1, 0.1), 
                                    position=Vec3(target.x, target.y+2, target.z),
                                    color=color.yellow)

            card.scale = 0
            card.rotation = (0, 0, 0)
            card.original_anchor = target

            # animate into place
            animator = TransformAnimator(target, duration=self.duration, curve=in_out_expo)
            invoke(card.add_script, animator, delay=i*self.delay)

        # activate spin after all cards placed
        invoke(setattr, self, "active", True, delay=total*self.delay + self.duration)

        # parent cards to anchors after animations are down to avoid explosion
        try:
            invoke(lambda: reparent(self.cards, self.anchors), delay=total*self.delay + self.duration)
            [card.show(BIT) for card in self.cards]
            [anchor.show(BIT) for anchor in self.anchors]
        except Exception as e:
            print("Reparent failed, most likely a timing issue with the hit_anim in main seq", e)

    def remove_card(self, card, target_slots):
        self.cards.remove(card)
        target_slots.append(card)

    def update(self):
        if not self.active:
            return

        # spin tornado globally
        self.rotation_y += time.dt * 3 # type: ignore

        # wobble anchors locally
        for anchor in self.anchors:
            anchor.rotation_x += lut_table.sin_lut(time.time() * 2 + id(anchor) % 10) * 0.05
            value_check(anchor.rotation_x)
            anchor.rotation_z += lut_table.cos_lut(time.time() * 1.5 + id(anchor) % 7) * 0.05
            value_check(anchor.rotation_z)

def reparent(ent, target_ent):
    print("Card reparented:", ent, "to", target_ent)
    if isinstance(ent, list) and isinstance(target_ent, list):
        if len(ent) != len(target_ent):
            raise ValueError("Lists must have the same length")
        for e, t in zip(ent, target_ent):
            e.world_parent = t
    elif isinstance(ent, list):
        for e in ent:
            e.world_parent = target_ent
    elif isinstance(target_ent, list):
        for t in target_ent:
            ent.world_parent = t  # ambiguous: last assignment wins
    else:
        ent.world_parent = target_ent

deck = []
def set_deck(new_cards):
    global deck
    deck = new_cards
    # print(deck)

def reset_ref_deck(ref_deck):
    ref_deck.clear()
    for card in deck:
        ref_deck.append(card.custom_class_param["name"])

def get_cards(ref_deck):
    for card in deck:
        ref_deck.append(card.custom_class_param["name"])

def get_card(card_name):
    for card in deck:
        if card.custom_class_param["name"] == card_name:
            break

    return card

def animate_hit(player, slot, target_slots):
    global card_tornado
    current_card = get_card(player["cards"][-1]) # TODO: FIX BUSTED CHECK
    card_tornado.remove_card(current_card, target_slots)

    # card_helper = Entity(position=current_card.world_position,
    #                      rotation=current_card.world_rotation,
    #                      scale=Vec3(CARD_HEIGHT, CARD_LENGTH, 0))
    
    current_card.world_parent = scene

    entity_pos = Entity(position=slot["position"], rotation=slot["rotation"])
    entity_pos.scale = (CARD_HEIGHT, CARD_LENGTH, 0.1)
    
    print("Target world_rot:", entity_pos.rotation)
    print("pos:", entity_pos.position)
    print("scale:", entity_pos.scale)
    
    current_card.add_script(TransformAnimator(entity_pos, duration=1, curve=in_out_expo))

    # print(current_card.scripts)
    # game_ticker.add_action(lambda: destroy(entity_pos))

def update_player_score(score):
    player_score.text = f"Score: {score}"

def update_dealer_score(score):
    dealer_score.text = f"Dealer Score: {score}"

def update_player_bet(bet):
    player_bet.text = f"Bet: {bet}"

def update_player_money(money):
    player_money.text = f"Money: {money}"

# table asset
table = GEntity(model=os.path.join(PATH_T + "Table.obj"),
                texture=os.path.join(PATH_T + "table_texture2.png"),
                movable=False,
                scale=7.6,
                y=-6)

# add simplified table collider
table.collider = MeshCollider(table, mesh=load_model(os.path.join(PATH_T + "Table_Collider.obj")), center=Vec3(0,0,0))

# new cards
new_card = Card(os.path.join(PATH_C + "card_pack/QH.png"))
another_new_card = Card(os.path.join(PATH_C + "card_pack/QC.png"), x=2)

# Menu UI
menu = Entity(parent=camera.ui)
camera.fov = 30

scn_manager = SceneManager()

# tornado
card_tornado = TornadoController(center=Vec3(0,2,0))

# text score
player_score = Text(f"Score: {0}", position=window.bottom, origin=(0.0, -0.5), scale=1.7)
player_money = Text(f"Money: {0}", position=(window.top_left.x, window.top_left.y - 0.001))
player_bet = Text(f"Bet: {0}", position=(player_money.x, player_money.y - player_money.height - 0.001))

# hide on start menu
player_score.disable()
player_money.disable()
player_bet.disable()

# buttons hit|stand|view
btn_hit = Button("Hit", position=window.bottom_left, scale=1, text_size=1)
btn_hit.fit_to_text()
btn_hit.origin=(-0.5, -0.5)
btn_hit.position += btn_hit.scale * 4

btn_stand = Button("Stand", position=Vec3(btn_hit.position), scale=1, text_size=1)
btn_stand.fit_to_text()
btn_stand.origin=(TOP_CENTER)
btn_stand.y -= MARGIN * 2
btn_stand.x += btn_hit.scale_x/2

btn_toggle_view = Button("View", position=Vec3(btn_stand.position), scale=1, text_size=1)
btn_toggle_view.fit_to_text()
btn_toggle_view.origin=(TOP_CENTER)
btn_toggle_view.y -= (MARGIN * 2) + btn_stand.scale_y

btn_hit_fin_pos = Entity(position=btn_hit.position, scale=btn_hit.scale, rotation=btn_hit.rotation, 
                         parent=btn_hit.parent, world_parent=btn_hit.world_parent)

btn_stand_fin_pos = Entity(position=btn_stand.position, scale=btn_stand.scale, rotation=btn_stand.rotation, 
                           parent=btn_stand.parent, world_parent=btn_stand.world_parent)

btn_toggle_view_fin_pos = Entity(position=btn_toggle_view.position, scale=btn_toggle_view.scale, rotation=btn_toggle_view.rotation, 
                           parent=btn_toggle_view.parent, world_parent=btn_toggle_view.world_parent)

btn_hit.position = (-2, btn_hit.y)
btn_stand.position = (-2, btn_stand.y)
btn_toggle_view.position = (-2, btn_toggle_view.y)

# hide on start menu
# btn_hit.disable()
# btn_stand.disable()

# camera prep
camera_man = CameraMan()
camera_man.load_cam('0')
# camera.fov = 50

CARD_HEIGHT = 1000 / 1050
CARD_LENGTH = 1000 / 750

# PLAYER SLOTS
slots_player_1 = [x for x in table_card_slots["group_0"].values()]
temp_list = []
for p in slots_player_1:
    new_p = copy.deepcopy(p)
    new_p["position"][2] += CARD_HEIGHT + 0.7
    temp_list.append(new_p)

slots_player_1 += temp_list

for slot in slots_player_1:
    slot["occupied"] = 0
# --------------------------
# print(slots_player_1)

# DEALER SLOTS
slots_dealer_1 = [x for x in table_card_slots["group_3"].values()]
temp_list = []
for p in slots_dealer_1:
    new_p = copy.deepcopy(p)
    new_p["position"][2] += CARD_HEIGHT + 0.7
    temp_list.append(new_p)

slots_dealer_1 += temp_list

for slot in slots_dealer_1:
    slot["occupied"] = 0
# --------------------------
# print(slots_dealer_1)

# DEALER TEXT
dealer_score_pos = slots_dealer_1[-1]["position"]
dealer_score_pos[0] -= .9
dealer_score_pos[1] += 0.4
dealer_score_pos[2] += 4
final_delar_score_pos = copy.deepcopy(dealer_score_pos)
final_delar_score_pos_obj = Entity(position=final_delar_score_pos, scale=Vec3(20, 20, 20))
dealer_score_pos [0] -= 20

dealer_obj = Entity(position=dealer_score_pos, scale=Vec3(20, 20, 20))
dealer_score = Text(f"Dealer Score: {0}", world=True, scale=1, parent=dealer_obj)
dealer_obj.hide(BIT)
dealer_score.hide(BIT)
dealer_score.disable()

def get_next_slot(slots):
    for index, slot in enumerate(slots):
        if slot["occupied"] == 0:
            slot["occupied"] = 1
            return index

class GameBlackjack():
    def __init__(self):
        # game logic stuff
        self.game_ticker = ScheduleSeq()
        self.blackjack_table = BlackjackLogic()
        self.ref_deck = []
        self.game_running = False
        self.player = None
        self.resolution = "None"
        self.dealer = None
        self.reset_round_trg = False

    def start_game_seq(self):
        global deck, card_tornado

        self.game_running = True

        print("Game Started")
        # print(deck)

        # start music on loop
        music.play()

        # load scene
        # scn_manager.clear_scene() # breaks with full preload
        destroy(another_new_card)
        destroy(new_card)
        destroy(table)
        scn_manager.load_scene("g_card_pos")

        # hide menu
        start_editor.disable()
        start_game.disable()

        # enable text
        self.game_ticker.add_action(lambda: player_score.enable())
        self.game_ticker.add_action(lambda: player_money.enable())
        self.game_ticker.add_action(lambda: player_bet.enable())
        self.game_ticker.add_action(lambda: dealer_score.enable())

        # animate start
        self.game_ticker.add_action(lambda: camera_man.load_cam('0'))
        camera.animate("fov", 50, duration=1, curve=in_out_quint)
        self.game_ticker.add_action(do_nothing, 0.1)
        self.game_ticker.add_action(lambda: camera_man.load_cam_anim('1', 1), duration=0)
        self.game_ticker.add_action(lambda: card_tornado.add_cards(deck), duration=0)

        # animate buttons
        self.game_ticker.add_action(lambda: btn_hit.add_script(TransformAnimator(btn_hit_fin_pos)), 0.1)
        self.game_ticker.add_action(lambda: btn_stand.add_script(TransformAnimator(btn_stand_fin_pos)), 0.1)
        self.game_ticker.add_action(lambda: btn_toggle_view.add_script(TransformAnimator(btn_toggle_view_fin_pos)), 0.1)
        self.game_ticker.add_action(lambda: dealer_obj.add_script(TransformAnimator(final_delar_score_pos_obj)))

        self.game_ticker.add_action(do_nothing, 0.02 * 52 + 1.2) # DO NOT CHANGE DELAY, KEEP HARD CODED

        self.game_ticker.add_action(lambda: get_cards(self.ref_deck))
        self.game_ticker.add_action(lambda: print("game_ready"))

        # main round logic
        self.blackjack_table.seat_player("1", 5000)
        self.blackjack_table.seat_dealer("Dealer")

        self.player = self.blackjack_table.players[0]
        player_money.text = f"Money: {self.player["money"]}"
        self.player["bet"] = 100
        player_bet.text = f"Bet: {self.player["bet"]}"

        self.dealer = self.blackjack_table.dealer

        # player face up card
        self.game_ticker.add_action(lambda: do_hit(self.game_ticker, self.blackjack_table, 
                                                   self.player, self.ref_deck, slots_player_1))
        self.game_ticker.add_action(do_nothing, 0.2)

        # dealer face up card (the "upcard")
        self.game_ticker.add_action(lambda: do_hit_dealer(self.game_ticker, self.blackjack_table,
                                                          self.dealer, self.ref_deck, slots_dealer_1))
        self.game_ticker.add_action(do_nothing, 0.2)

        # player face up card
        self.game_ticker.add_action(lambda: do_hit(self.game_ticker, self.blackjack_table, 
                                                   self.player, self.ref_deck, slots_player_1))
        self.game_ticker.add_action(do_nothing, 0.2)

        # TODO: Put Tornado cards on ground for this select to hide card face 
        # dealer face down card (the "hole card")
        self.game_ticker.add_action(lambda: do_hit_dealer(self.game_ticker, self.blackjack_table,
                                                          self.dealer, self.ref_deck, slots_dealer_1, update_score=False))
        self.game_ticker.add_action(do_nothing, 0.1)
        self.game_ticker.add_action(self.assign_buttons)

    def disable_buttons(self):
        btn_hit.ignore_input = True # TODO: wrap the scheduler/invoke for these with disables/enables instead
        btn_stand.ignore_input = True

    def enable_buttons(self):
        btn_hit.ignore_input = False
        btn_stand.ignore_input = False

    def stand_sequence(self):
        # also just dealer sequence in general

        self.disable_buttons()

        # show hole card
        new_rot = Vec3(90.0, 180.0, -90.0)
        entity_pos = Entity(position=dealer_slots_cards[1].world_position,
                            rotation=new_rot,
                            scale=Vec3(CARD_HEIGHT, CARD_LENGTH, 0.1))

        dealer_slots_cards[1].add_script(TransformAnimator(entity_pos, duration=.3, curve=in_out_expo))

        self.dealer = self.blackjack_table.dealer
        update_dealer_score(self.dealer["score"]) # type: ignore

        if self.dealer["score"] > self.player["score"]: # type:ignore
            self.game_ticker.add_action(do_nothing, 0.9)
            self.game_ticker.add_action(self.final_seq)
        else:
            self.game_ticker.add_action(self.dealer_hit_loop)

    def the_check(self):
        if self.dealer["score"] < 17: # type: ignore
            self.game_ticker.add_action(self.dealer_hit_loop)
            self.game_ticker.add_action(lambda: print("DEALER:", self.dealer))
        else:
            self.game_ticker.add_action(do_nothing, 0.9)
            self.game_ticker.add_action(self.final_seq)

    def dealer_hit_loop(self):
        do_hit_dealer(self.game_ticker, self.blackjack_table, self.dealer, self.ref_deck, slots_dealer_1)
        self.game_ticker.add_action(do_nothing, 0.2)
        self.game_ticker.add_action(self.the_check)

    def final_seq(self):
        # resolution logic
        if self.player["score"] > self.dealer["score"] or not self.player["busted"] and self.dealer["busted"]: # type: ignore
            self.resolution = "won"
            self.blackjack_table.player_win(self.player)
        elif self.player["score"] < self.dealer["score"]  or self.player["busted"] and not self.dealer["busted"]: # type: ignore
            self.resolution = "lost"
            self.blackjack_table.player_lose(self.player)
        else:
            self.resolution = "tied"

        self.game_ticker.add_action(self.blackjack_table.refresh_deck)
        self.game_ticker.add_action(self.reset_round)

    def new_round(self):
        global deck, card_tornado

        update_player_score(0)
        update_dealer_score(0)

        self.game_ticker.add_action(lambda: reset_ref_deck(self.ref_deck))
        self.game_ticker.add_action(lambda: print("round_ready"))

        self.player = self.blackjack_table.players[0]
        player_money.text = f"Money: {self.player["money"]}"
        self.player["bet"] = 100
        player_bet.text = f"Bet: {self.player["bet"]}"

        # player face up card
        act = lambda: do_hit(self.game_ticker, self.blackjack_table, self.player, self.ref_deck, slots_player_1)
        self.game_ticker.add_action(act)
        self.game_ticker.add_action(do_nothing, 0.2)

        # dealer face up card (the "upcard")
        act = lambda: do_hit_dealer(self.game_ticker, self.blackjack_table, self.dealer, self.ref_deck, slots_dealer_1)
        self.game_ticker.add_action(act)
        self.game_ticker.add_action(do_nothing, 0.2)

        # player face up card
        act = lambda: do_hit(self.game_ticker, self.blackjack_table, self.player, self.ref_deck, slots_player_1)
        self.game_ticker.add_action(act)
        self.game_ticker.add_action(do_nothing, 0.2)

        # TODO: Put Tornado cards on ground for this select to hide card face 
        # dealer face down card (the "hole card")
        act = lambda: do_hit_dealer(self.game_ticker, self.blackjack_table, self.dealer, self.ref_deck, slots_dealer_1, update_score=False)
        self.game_ticker.add_action(act)
        self.game_ticker.add_action(do_nothing, 0.1)
        self.game_ticker.add_action(self.enable_buttons)


    def assign_buttons(self):
        btn_hit.on_click = lambda: do_hit(self.game_ticker, self.blackjack_table, self.player, self.ref_deck, slots_player_1)
        btn_stand.on_click = self.stand_sequence # TODO: fix, its temporary
        btn_toggle_view.on_click = self.toggle_view

    def toggle_view(self):
        if camera_man.current_view == '2':
            self.game_ticker.add_action(lambda: camera_man.load_cam_anim('1'), 1)
        else:
            self.game_ticker.add_action(lambda: camera_man.load_cam_anim('2'), 1)

    def listen_to_logic(self):
        if self.player:
            if self.player["busted"] and not self.reset_round_trg:
                self.game_ticker.add_action(lambda: print("Busted"))
                self.reset_round_trg = True
                self.game_ticker.add_action(self.reset_round)

    # resolution
    def reset_round(self):
        if self.player:
            self.game_ticker.add_action(do_nothing, 0.4)
            # print(self.player)
            # print(player_slots_cards)

            # reset
            invoke(self.reset_player, delay=(len(player_slots_cards)*0.1)+2)
            invoke(self.reset_dealer, delay=(len(player_slots_cards)*0.1)+2)
            invoke(self.new_round, delay=2.4)

            if self.player["busted"]:
                final_text = "BUSTED"
            else:
                final_text = self.resolution.upper()

            # Busted Text
            text = Text(final_text, scale=10, color=color.red, origin=CENTER)
            ent = Entity(model="quad", color=color.black50, parent=text, scale=Vec3(0.12, 0.04, 0.1))
            ent.hide(BIT)
            text.background_entity=ent

            invoke(lambda: destroy(text), delay=2.4)
            # [ ]TODO: disable buttons when text displayed

            # return player cards to tornado
            for i, card in enumerate(player_slots_cards):
                animator = TransformAnimator(card.original_anchor, duration=1, curve=in_out_expo)
                invoke(card.add_script, animator, delay=0.5+(i*0.1))
                invoke(lambda c=card: reparent(c, c.original_anchor), delay=1.01+0.5+(i*0.1))

            # return dealer cards to tornado
            for i, card in enumerate(dealer_slots_cards):
                animator = TransformAnimator(card.original_anchor, duration=1, curve=in_out_expo)
                invoke(card.add_script, animator, delay=0.5+(i*0.1))
                invoke(lambda c=card: reparent(c, c.original_anchor), delay=1.01+0.5+(i*0.1))

            # reset player slots
            for slot in slots_player_1:
                slot["occupied"] = 0

            # reset dealer slots
            for slot in slots_dealer_1:
                slot["occupied"] = 0

    def reset_player(self):
        self.blackjack_table.player_reset(self.player)
        self.reset_round_trg = False
        player_slots_cards.clear()

    def reset_dealer(self):
        self.blackjack_table.dealer_reset(self.dealer)
        self.reset_round_trg = False
        dealer_slots_cards.clear()

def do_nothing():
    pass

def do_hit(game_ticker, blackjack_table, player, ref_deck, slots, update_score=True):
    slot = get_next_slot(slots)

    # run logic
    game_ticker.add_action(lambda: blackjack_table.hit(player, ref_deck, 1, True))
    game_ticker.add_action(lambda: blackjack_table.process_turn(player))
    game_ticker.add_action(lambda: animate_hit(player, slots[slot], player_slots_cards), duration=0.4)

    # update text
    game_ticker.add_action(lambda: update_player_bet(player["bet"]))
    game_ticker.add_action(lambda: update_player_money(player["money"]))

    if update_score:
        game_ticker.add_action(lambda: update_player_score(player["score"]))

def do_hit_dealer(game_ticker, blackjack_table, dealer, ref_deck, slots, update_score=True):
    slot = get_next_slot(slots)

    # run logic
    game_ticker.add_action(lambda: blackjack_table.hit(dealer, ref_deck, 1, True))
    game_ticker.add_action(lambda: blackjack_table.process_turn(dealer))
    game_ticker.add_action(lambda: animate_hit(dealer, slots[slot], dealer_slots_cards), duration=0.4)

    # update text
    if update_score:
        game_ticker.add_action(lambda: update_dealer_score(dealer["score"]))

blackjack_game = GameBlackjack()

player_slots_cards = []
dealer_slots_cards = []

start_game = Button("Start Game", parent=menu, position=(-0.65, .25), scale=(0.2, 0.1), on_click=blackjack_game.start_game_seq)
start_editor = Button("Editor", parent=menu, position=(-0.65, .10), scale=(0.2, 0.1))
menu.hide(BIT)

# Scene
BlenderCamera()
DirectionalLight(y=2, z=3, shadows=True)
AmbientLight(color=color.rgba(100,100,100,0.5))

# Music
music = Audio('Assets/Audio/game_background_song_fade.wav', loop=True, autoplay=False)

# Sky()
camera.clip_plane_far=500

paused = False

class FocusWatcher(Entity):
    """reliable for wayland/xwayland"""
    def __init__(self):
        super().__init__()
        self.ignore_paused = True  # stays active while paused

    def update(self):
        global paused
        focused = base.win.getProperties().getForeground() # type: ignore
        if not focused and not paused:
            paused = True
            application.pause()
            print("Paused: lost focus")
        elif focused and paused:
            paused = False
            application.resume()
            print("Resumed: regained focus")

FocusWatcher()  # single instance handles it

def update():
    if not blackjack_game.game_running:
        new_card.rotation_y += 0.1
        new_card.rotation_x += 0.2
    else:
        blackjack_game.listen_to_logic()

    if blackjack_game.game_ticker:
        blackjack_game.game_ticker.update()

set_deck(preload_deck())

# print("MSAA samples in main window:", base.win.getFbProperties().getMultisamples())
app.run()
