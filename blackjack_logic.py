# [x] III. Optional Topic (Advanced Level) – Blackjack
# Goal: build the Blackjack game engine using functions.

# The main program must call only 2 functions:
#   player = seat_player(name, budget)
#   run_blackjack(player)

# The rest should be organized through functions.
# The program must run step by step, stopping whenever user input is required
# (e.g., when deciding whether to “Hit” or “Hold”).

"""
## Flow

First: prompt AI as such:
    Explain blackjack rules in an organized manner
Second: Organize rules manually and make functions as you go

## Blackjack Rules:

Traditional: 1 deck 
Modern: 4-8 decks

Players: 1-7 players against dealer

[x] Objectives:
    [x] Get a hand closer to 21 than house
    [x] Do not go over 21

[x] Card Values:
    [x] Number Cards: 2-10 - face value
    [x] Face Cards: (J, Q, K): 10 points
    [x] Ace (A): 1 or 11 (whichever benefits the player's hand)

[x] Initial Deal:
    [x] Each player gets 2 cards face up
    [x] Dealer gets:
        - 1 card face up (the "upcard")
        - 1 card face down (the "hole card")
    [x] Order:
        - each player gets 1 face up card
        - dealer gets 1 card face up (the "upcard")
        - each player gets 1 face up card
        - dealer gets 1 card face down (the "hole card")

[x] Betting (before any cards are dealt)

TODO: Add proper lose condition
[ ] Dealer peeks at the hole card. If it completes a blackjack, 
the dealer flips it over immediately → all players without blackjack lose instantly.

[x] Player's Turn:
    Each Player decides:
    [x] - Hit: take another card
    [x] - Stand (Hold): keep current hand
    [x] - Double Down (optional rule): 
        double the bet, take one card only, then stand
    [ ] - Split (optional rule):
        if both cards are the same value, 
        split into two hands (requires another bet)
    Player continues until they 'Stand' or 'Bust'

[x] Dealer's Turn:
    - Dealer reveals his hole card
    - Must hit until reaching 17 or higher (rules vary)

[x] Resolution - Compare Hands:
    - Player Hand > Dealer Hand -> Player wins
    - Dealer Hand > Player Hand -> Dealer wins
    - Tie -> Push (no one wins, bet returned)
"""

import random
import math
from painting_on_water import vinput

# [x] top-level TODO: test play flow
# [x] top-level TODO: wrap input prompts with validations (generalized function)
# [ ] top-level TODO: re-make with Game class to hold deck, players, dealers and state, easier than passing dicts

# real randomness from the OS entropy pool
sys_rand = random.SystemRandom()

# useful lists
NUMBER_CARDS = [str(i) for i in range(2, 11)]
FACE_CARDS = ['J', 'Q', 'K']
ACE = ['A']
SUITS = ["♠️", "♣️", "♥️", "♦️"]
RANKS = NUMBER_CARDS + FACE_CARDS + ACE

# one full deck
ORIGIN_DECK = [card + ' ' + suit + ' ' for card in RANKS for suit in SUITS]

# debug stuff, verbosity
DEBUG = True

class BlackjackLogic:
    def __init__(self):
        self.players = []
        self.dealer = []
        self.deck = []

    def check_hand(self, hand: list[str]) -> dict:
        """return 'bust' or card score if not bust"""

        # convert cards to score
        score = 0
        ace_count = 0
        for card in hand:
            card = card[:-1] # SPECIFIC TO ursina game
            if card in FACE_CARDS:
                score += 10
            elif card in ACE:
                ace_count += 1
            elif card in NUMBER_CARDS:
                score += int(card)

        # determine aces score
        score += ace_count # default to one
        for _ in range(ace_count):
            if score + 10 <= 21:
                score += 10 # change to 11 if beneficial
        
        return {"score": score, "busted": score > 21}

    def hit(self, player: dict, deck: list, count: int = 1, debug=False):
        """change player hand in place, remove from deck in place"""
        for _ in range(count):
            random_card = sys_rand.choice(deck)
            deck.remove(random_card)
            player["cards"].append(random_card)
            if debug:
                print(f"You hit {random_card}")


    def initial_deal(self, players: list[dict], dealer: dict, deck: list):
        """order matters:
        - each player gets 1 face up card
        - dealer gets 1 card face up (the "upcard")
        - each player gets 1 face up card
        - dealer gets 1 card face down (the "hole card")
        """

        # first deal players face up
        for player in players:
            self.hit(player, deck)

        # second deal house face up
        self.hit(dealer, deck)

        # third deal players face up
        for player in players:
            self.hit(player, deck)

        # fourth deal house face down
        random_card = sys_rand.choice(deck)
        deck.remove(random_card)
        dealer["hole_card"] = random_card


    def seat_player(self, name: str, budget: float):
        """add player to list using decided struct"""
        new_player = {
            "name": name,
            "money": budget,
            "bet": None, # (float)
            "cards": [],
            "score": None, # (int) card from check_hand()
            "stand": False, # indicates player turn is over
            "busted": False # check_hand()
        }
        self.players.append(new_player)


    def seat_dealer(self, name: str):
        """organized way to get fresh dealer"""
        dealer = {
            "name": name,
            "money": math.inf,
            "bet": 0, # placeholder to avoid errors
            "cards": [],
            "score": 0, # (int) card from check_hand()
            "hole_card": None,
            "stand": False, # indicates dealer turn is over
            "busted": False # check_hand()
        }

        self.dealer = dealer
        return dealer


    def run_action_player(self, action: str, player:dict, deck: list, debug=DEBUG):
        """specific player action logic, calls process_turn()"""
        # TODO: introduce AI mapping resolution

        mapped_actions = {'1': "hit",         "hit": "hit", 
                        '2': "stand",       "stand": "stand",
                        '3': "double_down", "double down": "double_down",
                        '4': "split",       "split": "split",
                        }

        if action in mapped_actions:
            action = mapped_actions[action.casefold()]
        else:
            return "not_mapped"

        if action == "hit":
            if debug: print("Hit!")
            self.hit(player, deck, 1)

        elif action == "stand":
            if debug: print("Stand!")
            player["stand"] = True

        elif action == "double_down" and player["money"] >= player["bet"] * 2:
            if debug: print("Double Down!")
            self.hit(player, deck, 1)
            player["bet"] = player["bet"] * 2
            player["stand"] = True
        
        self.process_turn(player)
        return
        # not implemented
        if action == "split":
            if debug: print("Split!")
            if len(player["cards"]) == 2 and player["cards"][0] == player["cards"][1]:
                print("POSSIBLE (NOT YET IMPLEMENTED)")


    def player_bust(self, player, debug=DEBUG):
        """boilerplate bust code"""
        if debug:
            print(f"Player {player["name"]} busted with score {player["score"]},",
                f"losing {player["bet"]}$")
            print(player["cards"])
        player["busted"] = True
        player["stand"] = True
        player["money"] -= player["bet"]
        player["bet"] = 0
        # player["score"] = 0
        # player["cards"] = [] # TODO: fix temp fix


    def player_win(self, player, debug=DEBUG):
        """boilerplate win code"""
        if debug:
            print(f"Player {player["name"]} won with score {player["score"]},",
                f"winning {player["bet"]}$")
            print(player["cards"])
        player["busted"] = False
        player["stand"] = False
        player["money"] += player["bet"]
        player["bet"] = 0
        player["score"] = 0
        player["cards"] = []


    def player_lose(self, player, debug=DEBUG):
        """boilerplate lose code"""
        if debug:
            print(f"Player {player["name"]} lost with score {player["score"]}, ",
                f"losing {player["bet"]}$")
        player["busted"] = False
        player["stand"] = False
        player["money"] -= player["bet"]
        player["bet"] = 0
        player["score"] = 0
        player["cards"] = []


    def player_reset(self, player, debug=DEBUG):
        """boilerplate player reset code"""
        if debug:
            print(f"Player {player["name"]} reset")
        player["busted"] = False
        player["stand"] = False
        player["score"] = None
        player["cards"] = []


    def dealer_reset(self, dealer, debug=DEBUG):
        """boilerplate dealer reset code"""
        if debug:
            print(f"Dealer {dealer["name"]} reset")
        dealer["busted"] = False
        dealer["stand"] = False
        dealer["score"] = None
        dealer["hole_card"] = None
        dealer["cards"] = []

    def process_turn(self, player, debug=DEBUG):
        """boilerplate processing code, safe to use anywhere and twice"""
        result = self.check_hand(player["cards"])
        player["score"] = result["score"]
        if result["busted"]:
            self.player_bust(player)
        else:
            if debug:
                # TODO: change flavour text for dealer
                print(f"\nPlayer {player["name"]} score: {player["score"]}")
                print(f"{player["cards"]}")


    def run_blackjack_console(self, players: list, dealer: dict, deck: list):
        """contains main game logic for one round"""

        # betting 
        for player in players:
            bet_amount = vinput(f"{player["name"]}, please make a bet({player["money"]}$): ",
                                        pattern=r'^\d+(\.\d+)?$', # integers, floats, decimal point
                                        condition=lambda t: float(t) <= player['money']).casefold().strip()
            bet_amount = float(bet_amount)
            print(player["money"])
            print(bet_amount <= player["money"])
            player["bet"] = bet_amount if 0 <= bet_amount <= player["money"] else 0
            print(f"Player {player["name"]} bet {player["bet"]}\n")

        # initial deal logic
        self.initial_deal(players, dealer, deck)

        # initial busted and score check TODO: remove busted logic, add dealer 21 logic
        for player in players:
            self.process_turn(player)

        remaining_players = [player for player in players if not player["busted"]]

        # reveal house's face-up card prior to player turn
        print(f"\nDealer has {dealer["cards"][0]} as well as one hidden card")
        self.process_turn(dealer, debug=False)
        print(f"Dealer's partial total: {dealer["score"]}")

        # game start, players turn
        for player in remaining_players:
            print(f"\nPlayer {player["name"]} you have:"
                f"\nCash left: {player["money"] - player["bet"]}$"
                f"\nBet: {player["bet"]}$"
                f"\nScore: {player["score"]}"
                f"\n  {player["cards"]}\n"
                )
            print("Available Actions:\n",
                "1.Hit\n2.Stand\n3.Double Down\n4.Split\n", sep='')
            
            while(not player["stand"]):
                player_action = vinput("Action: ", pattern=r"^(1|2|3|4|hit|stand|double down|split)$").lower().strip()
                self.run_action_player(player_action, player, deck) # processes turn as well

        remaining_players = [player for player in players if not player["busted"]]

        # dealers turn
        print("\n\nDealer's Turn\n")
        print(f"Dealer's hidden card is {dealer["hole_card"]}")
        dealer["cards"].append(dealer["hole_card"])
        self.process_turn(dealer, debug=False)
        print(f"Dealer has score {dealer["score"]}")
        print(dealer["cards"], '\n')

        if not dealer["busted"]:
            print(f"Dealer's total: {dealer["score"]}")
            while (dealer["score"] < 17 and not dealer["busted"]):
                self.hit(dealer, deck, 1)
                self.process_turn(dealer)

        # resolution
        if not dealer["busted"]:
            print(f"Dealer's total: {dealer["score"]}")
            for player in remaining_players:
                if player["score"] > dealer["score"]:
                    self.player_win(player)
                elif player["score"] < dealer["score"]:
                    self.player_lose(player)
                else:
                    print(f"Player {player["name"]} tied with the house")
                    self.player_reset(player)
        else:
            print("\nRemaining players win!")
            print([player["name"] + " " for player in remaining_players])
            for player in remaining_players:
                self.player_win(player)

        for player in players:
            self.player_reset(player)

        self.dealer_reset(dealer)

        return
    
    def refresh_deck(self, modern_variant=False):
        self.deck = ORIGIN_DECK * 8 if modern_variant else ORIGIN_DECK

    def main_game_logic(self):
        # example one game with one round

        # get fresh deck
        modern_variant = False
        self.deck = ORIGIN_DECK * 8 if modern_variant else ORIGIN_DECK

        # get fresh players list
        self.players = []

        # example seat players
        self.seat_player("Player", float(sys_rand.randint(2000, 8000)), self.players) # type: ignore

        # seat dealer
        self.dealer = self.seat_dealer("Dealer")

        # shuffle deck
        sys_rand.shuffle(self.deck)

        # start round example
        # run_blackjack_console(players, new_dealer, deck)

        # keep the game rolling
        keep_on = True
        while keep_on:
            self.run_blackjack_console(self.players, new_dealer, self.deck) # type: ignore
            if sum([player["money"] for player in self.players]) <= 0.0:
                return
            keep_on = True if vinput("Keep Playing?(yes/no): ", pattern=r'^(yes|no)$').lower().strip() == "yes" else False
            self.refresh_deck()
            sys_rand.shuffle(self.deck) # shuffle


if __name__ == "__main__":
    blackjack_table = BlackjackLogic()
    blackjack_table.main_game_logic()