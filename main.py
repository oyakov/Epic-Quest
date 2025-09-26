import math
import random
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import pygame


SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 768
FPS = 60

GLOBAL_MAP_BACKGROUND = (20, 28, 44)
TACTICAL_BG = (15, 18, 26)
GRID_COLOR = (48, 54, 69)
HERO_COLOR = (114, 205, 255)
ENEMY_COLOR = (218, 85, 81)
TEXT_COLOR = (230, 230, 230)
HIGHLIGHT_COLOR = (247, 226, 107)
OVERLAY_BG = (14, 14, 18, 220)


@dataclass
class Stats:
    max_hp: int = 30
    attack: int = 5
    defense: int = 2
    initiative: int = 3

    def add(self, other: "Stats") -> "Stats":
        return Stats(
            max_hp=self.max_hp + other.max_hp,
            attack=self.attack + other.attack,
            defense=self.defense + other.defense,
            initiative=self.initiative + other.initiative,
        )

    def with_bonus(
        self,
        *,
        hp: int = 0,
        attack: int = 0,
        defense: int = 0,
        initiative: int = 0,
    ) -> "Stats":
        return Stats(
            max_hp=self.max_hp + hp,
            attack=self.attack + attack,
            defense=self.defense + defense,
            initiative=self.initiative + initiative,
        )


@dataclass
class Item:
    name: str
    slot: str
    rarity: str
    hp_bonus: int = 0
    attack_bonus: int = 0
    defense_bonus: int = 0
    initiative_bonus: int = 0
    description: str = ""

    def bonus_stats(self) -> Stats:
        return Stats(
            max_hp=self.hp_bonus,
            attack=self.attack_bonus,
            defense=self.defense_bonus,
            initiative=self.initiative_bonus,
        )


class Inventory:
    def __init__(self) -> None:
        self.slots: Dict[str, Optional[Item]] = {
            "weapon": None,
            "armor": None,
            "trinket": None,
        }
        self.bag: List[Item] = []

    def equipped_items(self) -> List[Item]:
        return [item for item in self.slots.values() if item]

    def add(self, item: Item) -> None:
        if item.slot in self.slots and self.slots[item.slot] is None:
            self.slots[item.slot] = item
        else:
            self.bag.append(item)

    def summary_lines(self) -> List[str]:
        lines = ["Equipped:"]
        for slot, item in self.slots.items():
            if item:
                lines.append(f"  {slot.title()}: {item.name} ({item.rarity})")
            else:
                lines.append(f"  {slot.title()}: empty")
        if self.bag:
            lines.append("")
            lines.append("Backpack:")
            for item in self.bag:
                lines.append(f"  {item.name} ({item.rarity})")
        else:
            lines.append("")
            lines.append("Backpack is empty.")
        return lines


@dataclass
class Talent:
    key: str
    name: str
    description: str
    hp_bonus: int = 0
    attack_bonus: int = 0
    defense_bonus: int = 0
    initiative_bonus: int = 0
    acquired: bool = False

    def apply(self, stats: Stats) -> Stats:
        if not self.acquired:
            return stats
        return stats.with_bonus(
            hp=self.hp_bonus,
            attack=self.attack_bonus,
            defense=self.defense_bonus,
            initiative=self.initiative_bonus,
        )


class TalentTree:
    def __init__(self) -> None:
        self.talents: Dict[str, Talent] = {
            "blade_mastery": Talent(
                key="blade_mastery",
                name="Blade Mastery",
                description="+2 Attack from rigorous sword training.",
                attack_bonus=2,
            ),
            "shield_wall": Talent(
                key="shield_wall",
                name="Shield Wall",
                description="+2 Defense by learning dwarven guard stances.",
                defense_bonus=2,
            ),
            "veterans_vigor": Talent(
                key="veterans_vigor",
                name="Veteran's Vigor",
                description="+10 Max HP from hardened adventures.",
                hp_bonus=10,
            ),
            "swift_foot": Talent(
                key="swift_foot",
                name="Swift Foot",
                description="+1 Initiative for faster turns.",
                initiative_bonus=1,
            ),
        }

    def acquire(self, key: str) -> bool:
        talent = self.talents.get(key)
        if talent and not talent.acquired:
            talent.acquired = True
            return True
        return False

    def apply(self, stats: Stats) -> Stats:
        for talent in self.talents.values():
            stats = talent.apply(stats)
        return stats

    def ordered(self) -> List[Talent]:
        return list(self.talents.values())


class Player:
    def __init__(self) -> None:
        self.base_stats = Stats()
        self.current_hp = self.base_stats.max_hp
        self.inventory = Inventory()
        self.talents = TalentTree()
        self.level = 1
        self.xp = 0
        self.talent_points = 1

    @property
    def stats(self) -> Stats:
        stats = self.base_stats
        for item in self.inventory.equipped_items():
            stats = stats.add(item.bonus_stats())
        stats = self.talents.apply(stats)
        if self.current_hp > stats.max_hp:
            self.current_hp = stats.max_hp
        return stats

    def heal_full(self) -> None:
        self.current_hp = self.stats.max_hp

    def gain_xp(self, amount: int) -> None:
        self.xp += amount
        while self.xp >= self.xp_to_next_level:
            self.xp -= self.xp_to_next_level
            self.level += 1
            self.talent_points += 1

    @property
    def xp_to_next_level(self) -> int:
        return 100 + (self.level - 1) * 50

    def is_alive(self) -> bool:
        return self.current_hp > 0


@dataclass
class Location:
    name: str
    description: str
    difficulty: int
    position: Tuple[int, int]
    discovered: bool = True

    def enemy_count(self) -> int:
        return max(1, self.difficulty + random.randint(0, 1))


@dataclass
class Enemy:
    name: str
    hp: int
    attack: int
    defense: int
    initiative: int
    position: Tuple[int, int]

    def is_adjacent_to(self, other: Tuple[int, int]) -> bool:
        return abs(self.position[0] - other[0]) + abs(self.position[1] - other[1]) == 1


class TacticalEncounter:
    def __init__(self, player: Player, location: Location) -> None:
        self.player = player
        self.location = location
        self.grid_size = (12, 8)
        self.tile_size = 64
        self.hero_pos = [self.grid_size[0] // 2, self.grid_size[1] - 2]
        self.turn = "player"
        self.enemies: List[Enemy] = self._spawn_enemies()
        self.log: List[str] = [f"You enter {location.name}! Prepare for battle."]
        self.victory = False
        self.defeat = False

    def _spawn_enemies(self) -> List[Enemy]:
        enemies: List[Enemy] = []
        for _ in range(self.location.enemy_count()):
            hp = random.randint(12, 20) + self.location.difficulty * 4
            attack = 3 + self.location.difficulty
            defense = 1 + self.location.difficulty // 2
            initiative = 2
            x = random.randint(1, self.grid_size[0] - 2)
            y = random.randint(1, 2)
            enemies.append(
                Enemy(
                    name="Orc Marauder",
                    hp=hp,
                    attack=attack,
                    defense=defense,
                    initiative=initiative,
                    position=(x, y),
                )
            )
        return enemies

    def move_player(self, dx: int, dy: int) -> None:
        if self.turn != "player":
            return
        new_x = max(0, min(self.grid_size[0] - 1, self.hero_pos[0] + dx))
        new_y = max(0, min(self.grid_size[1] - 1, self.hero_pos[1] + dy))
        if not any(enemy.position == (new_x, new_y) for enemy in self.enemies):
            self.hero_pos = [new_x, new_y]

    def player_attack(self) -> None:
        if self.turn != "player":
            return
        for enemy in self.enemies:
            if enemy.is_adjacent_to(tuple(self.hero_pos)):
                damage = max(0, self.player.stats.attack - enemy.defense)
                damage = max(1, damage)
                enemy.hp -= damage
                self.log.append(f"You strike {enemy.name} for {damage} damage.")
                if enemy.hp <= 0:
                    self.log.append(f"{enemy.name} falls!")
                break
        self.enemies = [enemy for enemy in self.enemies if enemy.hp > 0]
        if not self.enemies:
            self.victory = True
            self.log.append("The battle is won!")
        self.turn = "enemies"

    def end_player_turn(self) -> None:
        if self.turn == "player":
            self.turn = "enemies"

    def update(self) -> None:
        if self.turn == "enemies":
            for enemy in self.enemies:
                self._enemy_take_turn(enemy)
            self.turn = "player"
        if self.player.current_hp <= 0:
            self.defeat = True

    def _enemy_take_turn(self, enemy: Enemy) -> None:
        hero_pos = tuple(self.hero_pos)
        if enemy.is_adjacent_to(hero_pos):
            damage = max(0, enemy.attack - self.player.stats.defense)
            damage = max(1, damage)
            self.player.current_hp -= damage
            self.log.append(f"{enemy.name} hits you for {damage} damage!")
            return
        dx = int(math.copysign(1, hero_pos[0] - enemy.position[0])) if enemy.position[0] != hero_pos[0] else 0
        dy = int(math.copysign(1, hero_pos[1] - enemy.position[1])) if enemy.position[1] != hero_pos[1] else 0
        target = (enemy.position[0] + dx, enemy.position[1] + dy)
        if target != hero_pos and not any(e.position == target for e in self.enemies):
            enemy.position = target

    def generate_loot(self) -> Item:
        rarity_roll = random.random()
        if rarity_roll > 0.92:
            rarity = "epic"
        elif rarity_roll > 0.78:
            rarity = "rare"
        elif rarity_roll > 0.45:
            rarity = "uncommon"
        else:
            rarity = "common"
        slot = random.choice(["weapon", "armor", "trinket"])
        bonus = self.location.difficulty * 2
        item = Item(
            name=f"{rarity.title()} {slot.title()}",
            slot=slot,
            rarity=rarity,
            attack_bonus=bonus if slot == "weapon" else bonus // 2,
            defense_bonus=bonus if slot == "armor" else bonus // 3,
            hp_bonus=bonus * 3 if slot == "trinket" else bonus,
            description="Forged in the fires of the Elder Days.",
        )
        return item


class Game:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("Epic Quest")
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("ubuntu", 20)
        self.title_font = pygame.font.SysFont("georgia", 32)
        self.running = True
        self.player = Player()
        self.locations = self._create_locations()
        self.selected_location_index = 0
        self.state = "global_map"
        self.encounter: Optional[TacticalEncounter] = None
        self.show_inventory = False
        self.show_talents = False

    def _create_locations(self) -> List[Location]:
        return [
            Location(
                name="Hobbiton",
                description="Peaceful fields hiding ancient secrets.",
                difficulty=1,
                position=(200, 520),
            ),
            Location(
                name="Bree",
                description="Crossroads town with many travelers.",
                difficulty=1,
                position=(380, 460),
            ),
            Location(
                name="Weathertop",
                description="Ruined watchtower claimed by goblins.",
                difficulty=2,
                position=(520, 360),
            ),
            Location(
                name="Rivendell",
                description="Elven refuge amidst waterfalls.",
                difficulty=2,
                position=(700, 300),
            ),
            Location(
                name="Misty Pass",
                description="Treacherous pass patrolled by orcs.",
                difficulty=3,
                position=(540, 220),
            ),
            Location(
                name="Moria Gates",
                description="Ancient dwarven halls overrun by shadows.",
                difficulty=4,
                position=(420, 180),
            ),
            Location(
                name="Lorien",
                description="Golden forest of timeless guardians.",
                difficulty=3,
                position=(780, 220),
            ),
            Location(
                name="Rohan Plains",
                description="Horse-lords rally against raiders.",
                difficulty=3,
                position=(660, 440),
            ),
            Location(
                name="Helm's Deep",
                description="Stone fortress resisting the dark tide.",
                difficulty=4,
                position=(620, 520),
            ),
            Location(
                name="Minas Tirith",
                description="White city standing firm against Mordor.",
                difficulty=5,
                position=(800, 540),
            ),
            Location(
                name="Mordor",
                description="Land of shadow and fire.",
                difficulty=6,
                position=(920, 420),
            ),
        ]

    def run(self) -> None:
        while self.running:
            self.clock.tick(FPS)
            self.handle_events()
            self.update()
            self.draw()
        pygame.quit()

    def handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_i:
                    self.show_inventory = not self.show_inventory
                elif event.key == pygame.K_t:
                    self.show_talents = not self.show_talents
                elif self.show_talents and pygame.K_1 <= event.key <= pygame.K_9:
                    self.spend_talent_point(event.key - pygame.K_1)
                elif self.state == "global_map":
                    self.handle_global_key(event.key)
                elif self.state == "tactical":
                    self.handle_tactical_key(event.key)

    def handle_global_key(self, key: int) -> None:
        if key in (pygame.K_LEFT, pygame.K_UP):
            self.selected_location_index = (self.selected_location_index - 1) % len(self.locations)
        elif key in (pygame.K_RIGHT, pygame.K_DOWN):
            self.selected_location_index = (self.selected_location_index + 1) % len(self.locations)
        elif key == pygame.K_RETURN:
            location = self.locations[self.selected_location_index]
            self.encounter = TacticalEncounter(self.player, location)
            self.state = "tactical"

    def handle_tactical_key(self, key: int) -> None:
        if not self.encounter:
            return
        if self.encounter.turn != "player":
            return
        if key == pygame.K_UP:
            self.encounter.move_player(0, -1)
        elif key == pygame.K_DOWN:
            self.encounter.move_player(0, 1)
        elif key == pygame.K_LEFT:
            self.encounter.move_player(-1, 0)
        elif key == pygame.K_RIGHT:
            self.encounter.move_player(1, 0)
        elif key == pygame.K_SPACE:
            self.encounter.player_attack()
        elif key == pygame.K_TAB:
            self.encounter.end_player_turn()

    def update(self) -> None:
        if self.state == "tactical" and self.encounter:
            self.encounter.update()
            if self.encounter.victory:
                self.on_victory()
            elif self.encounter.defeat:
                self.on_defeat()

    def on_victory(self) -> None:
        if not self.encounter:
            return
        loot = self.encounter.generate_loot()
        self.player.inventory.add(loot)
        xp_gain = 50 + self.encounter.location.difficulty * 25
        self.player.gain_xp(xp_gain)
        self.player.heal_full()
        self.encounter.log.append(f"You claim {loot.name}! ({loot.rarity})")
        self.encounter.log.append(f"You gain {xp_gain} XP.")
        self.state = "global_map"
        self.encounter = None

    def on_defeat(self) -> None:
        self.state = "global_map"
        self.player.current_hp = max(1, self.player.stats.max_hp // 2)
        self.encounter = None

    def draw(self) -> None:
        if self.state == "global_map":
            self.draw_global_map()
        elif self.state == "tactical" and self.encounter:
            self.draw_tactical_map()
        pygame.display.flip()

    def draw_global_map(self) -> None:
        self.screen.fill(GLOBAL_MAP_BACKGROUND)
        pygame.draw.rect(self.screen, (35, 45, 60), (80, 120, SCREEN_WIDTH - 160, SCREEN_HEIGHT - 180), border_radius=30)
        for index, location in enumerate(self.locations):
            x, y = location.position
            radius = 16 + location.difficulty * 2
            color = (90 + location.difficulty * 20, 110, 160)
            pygame.draw.circle(self.screen, color, (x, y), radius)
            if index == self.selected_location_index:
                pygame.draw.circle(self.screen, HIGHLIGHT_COLOR, (x, y), radius + 4, 3)
            label = self.font.render(location.name, True, TEXT_COLOR)
            self.screen.blit(label, (x - label.get_width() // 2, y - radius - 22))

        header = self.title_font.render("The Realms of the West", True, TEXT_COLOR)
        self.screen.blit(header, (SCREEN_WIDTH // 2 - header.get_width() // 2, 24))

        location = self.locations[self.selected_location_index]
        panel_rect = pygame.Rect(60, SCREEN_HEIGHT - 140, SCREEN_WIDTH - 120, 100)
        pygame.draw.rect(self.screen, (26, 30, 42), panel_rect, border_radius=18)
        name_text = self.font.render(f"{location.name} (Danger {location.difficulty})", True, TEXT_COLOR)
        desc_text = self.font.render(location.description, True, TEXT_COLOR)
        self.screen.blit(name_text, (panel_rect.x + 20, panel_rect.y + 14))
        self.screen.blit(desc_text, (panel_rect.x + 20, panel_rect.y + 48))

        stats = self.player.stats
        stats_text = self.font.render(
            f"HP {self.player.current_hp}/{stats.max_hp}  ATK {stats.attack}  DEF {stats.defense}  INIT {stats.initiative}  LVL {self.player.level}",
            True,
            TEXT_COLOR,
        )
        self.screen.blit(stats_text, (panel_rect.x + 20, panel_rect.y + 72))
        xp_text = self.font.render(
            f"XP: {self.player.xp}/{self.player.xp_to_next_level}  Talent Points: {self.player.talent_points}",
            True,
            TEXT_COLOR,
        )
        self.screen.blit(xp_text, (panel_rect.x + 420, panel_rect.y + 72))

        if self.show_inventory:
            self.draw_inventory_overlay()
        if self.show_talents:
            self.draw_talent_overlay()

    def draw_tactical_map(self) -> None:
        encounter = self.encounter
        assert encounter is not None
        self.screen.fill(TACTICAL_BG)
        width = encounter.grid_size[0] * encounter.tile_size
        height = encounter.grid_size[1] * encounter.tile_size
        offset_x = (SCREEN_WIDTH - width) // 2
        offset_y = 80
        for y in range(encounter.grid_size[1]):
            for x in range(encounter.grid_size[0]):
                rect = pygame.Rect(
                    offset_x + x * encounter.tile_size,
                    offset_y + y * encounter.tile_size,
                    encounter.tile_size,
                    encounter.tile_size,
                )
                pygame.draw.rect(self.screen, GRID_COLOR, rect, 1)

        hero_rect = pygame.Rect(
            offset_x + encounter.hero_pos[0] * encounter.tile_size + 8,
            offset_y + encounter.hero_pos[1] * encounter.tile_size + 8,
            encounter.tile_size - 16,
            encounter.tile_size - 16,
        )
        pygame.draw.rect(self.screen, HERO_COLOR, hero_rect)

        for enemy in encounter.enemies:
            rect = pygame.Rect(
                offset_x + enemy.position[0] * encounter.tile_size + 10,
                offset_y + enemy.position[1] * encounter.tile_size + 10,
                encounter.tile_size - 20,
                encounter.tile_size - 20,
            )
            pygame.draw.rect(self.screen, ENEMY_COLOR, rect)

        hud_rect = pygame.Rect(40, 20, SCREEN_WIDTH - 80, 40)
        pygame.draw.rect(self.screen, (26, 30, 42), hud_rect, border_radius=12)
        stats = self.player.stats
        hud_text = self.font.render(
            f"HP {self.player.current_hp}/{stats.max_hp}  ATK {stats.attack}  DEF {stats.defense}  INIT {stats.initiative}  Turn: {encounter.turn.title()}",
            True,
            TEXT_COLOR,
        )
        self.screen.blit(hud_text, (hud_rect.x + 14, hud_rect.y + 10))

        log_rect = pygame.Rect(40, SCREEN_HEIGHT - 200, SCREEN_WIDTH - 80, 160)
        pygame.draw.rect(self.screen, (26, 30, 42), log_rect, border_radius=12)
        for i, line in enumerate(encounter.log[-6:]):
            text = self.font.render(line, True, TEXT_COLOR)
            self.screen.blit(text, (log_rect.x + 14, log_rect.y + 14 + i * 22))

        if self.show_inventory:
            self.draw_inventory_overlay()
        if self.show_talents:
            self.draw_talent_overlay()

    def draw_inventory_overlay(self) -> None:
        surface = pygame.Surface((SCREEN_WIDTH - 200, SCREEN_HEIGHT - 200), pygame.SRCALPHA)
        surface.fill(OVERLAY_BG)
        lines = self.player.inventory.summary_lines()
        for i, line in enumerate(lines):
            text = self.font.render(line, True, TEXT_COLOR)
            surface.blit(text, (30, 30 + i * 24))
        self.screen.blit(surface, (100, 100))

    def draw_talent_overlay(self) -> None:
        surface = pygame.Surface((SCREEN_WIDTH - 200, SCREEN_HEIGHT - 200), pygame.SRCALPHA)
        surface.fill(OVERLAY_BG)
        header = self.title_font.render("Talent Tree", True, TEXT_COLOR)
        surface.blit(header, (30, 20))
        for i, talent in enumerate(self.player.talents.ordered()):
            status = "Learned" if talent.acquired else "Locked"
            text = self.font.render(f"[{i + 1}] {talent.name} - {status}", True, TEXT_COLOR)
            surface.blit(text, (30, 80 + i * 60))
            desc_lines = wrap_text(talent.description, 46)
            for j, line in enumerate(desc_lines):
                desc_text = self.font.render(line, True, TEXT_COLOR)
                surface.blit(desc_text, (60, 104 + i * 60 + j * 20))
        footer = self.font.render("Press number key to learn talent if you have points.", True, TEXT_COLOR)
        surface.blit(footer, (30, surface.get_height() - 50))
        points = self.font.render(f"Talent Points: {self.player.talent_points}", True, TEXT_COLOR)
        surface.blit(points, (surface.get_width() - 240, 24))
        self.screen.blit(surface, (100, 100))

    def spend_talent_point(self, index: int) -> None:
        talents = self.player.talents.ordered()
        if 0 <= index < len(talents) and self.player.talent_points > 0:
            talent = talents[index]
            if self.player.talents.acquire(talent.key):
                self.player.talent_points -= 1


def wrap_text(text: str, width: int) -> List[str]:
    words = text.split()
    lines: List[str] = []
    current = []
    while words:
        word = words.pop(0)
        current.append(word)
        if sum(len(w) for w in current) + len(current) - 1 > width:
            current.pop()
            lines.append(" ".join(current))
            current = [word]
    if current:
        lines.append(" ".join(current))
    return lines


def main() -> None:
    game = Game()
    game.run()


if __name__ == "__main__":
    main()
