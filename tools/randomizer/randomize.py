#!/usr/bin/env python3
"""Randomizer: writes randomized copies of the game's data from a seed, without touching res/.

    randomize.py SEED [OUTPUT]          # OUTPUT defaults to build/randomized

configure.py runs this for `configure.py --randomize SEED` and packs the archives of the directories below from the
copies instead of from res/. The same seed always gives the same data.

What changes, and where the copy goes (OUTPUT/<path under the repository>):

- res/field/encounters: the species of every wild encounter slot, with its levels.
- res/trainers/data: the species of every Pokémon of every trainer, with its level. Forms, genders and ability
  slots go back to their defaults, since the new species may not have them.
- res/pokemon: each species' abilities (and hidden ability), the moves of its level-up learnset, and the items it
  holds when wild. A species' first move is always a damaging one.
- res/field/shops: the items of the Poké Marts. Poké Balls stay, so that catching stays possible.
- res/field/events: the items lying on the ground (NPCs of global script 2000).

Items are chosen from the ones that aren't key items, TMs or HMs. Species are 1 to 649 (Bulbasaur to Genesect), so
legendary Pokémon can appear anywhere.
"""
import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.data.gen_constants import load as load_list  # noqa: E402
from tools.data import item_data, move_data, species_data  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = ROOT / "build" / "randomized"

LAST_SPECIES = 649
STRUGGLE = "MOVE_STRUGGLE"
KEPT_BALLS = {"ITEM_POKE_BALL", "ITEM_GREAT_BALL", "ITEM_ULTRA_BALL"}
GROUND_ITEM_SCRIPT = 2000

# The directories that get a randomized copy, and the files of them that the packers read
COPIED = {
    "res/field/encounters": ("*.json",),
    "res/trainers/data": ("*.json",),
    "res/field/shops": ("*.json",),
    "res/field/events": ("*.json",),
    "res/pokemon": ("*.json", "*.csv"),
}


class Pools:
    """The species, abilities, moves and items that the randomizer picks from."""

    def __init__(self):
        species = load_list("species")
        self.species = sorted(name for name, value in species.items() if 1 <= value <= LAST_SPECIES)
        self.abilities = sorted(name for name, value in load_list("abilities").items() if value > 0)
        moves = load_list("moves")
        self.moves = sorted(name for name, value in moves.items() if value > 0 and name != STRUGGLE)
        self.damaging_moves = [name for name in self.moves if self.move_power(name) > 0]
        items = load_list("items")
        self.items = sorted(name for name, value in items.items() if value > 0 and self.item_usable(name))

    @staticmethod
    def move_power(move: str) -> int:
        path = ROOT / "res/moves" / move_data.directory(move) / "data.json"
        return json.loads(path.read_text(encoding="utf-8")).get("power") or 0

    @staticmethod
    def item_usable(item: str) -> bool:
        path = ROOT / "res/items" / item_data.directory(item) / "data.json"
        if not path.is_file():
            return False
        return not json.loads(path.read_text(encoding="utf-8")).get("important", False)


def stream(seed: str, section: str) -> random.Random:
    """A generator of its own for each section, so that changing one doesn't change the others."""
    return random.Random(f"{seed}:{section}")


def is_slot(value) -> bool:
    return (isinstance(value, list) and len(value) == 3 and isinstance(value[0], str)
            and value[0].startswith("SPECIES_") and all(isinstance(v, int) for v in value[1:]))


def randomize_encounters(data, pools: Pools, rng: random.Random) -> int:
    """Replaces the species of every [species, min_level, max_level] slot. Returns how many."""
    count = 0
    if is_slot(data):
        data[0] = rng.choice(pools.species)
        return 1
    children = data.values() if isinstance(data, dict) else data if isinstance(data, list) else []
    for child in children:
        count += randomize_encounters(child, pools, rng)
    return count


def randomize_trainer(data: dict, pools: Pools, rng: random.Random) -> int:
    for member in data.get("party", []):
        member["species"] = rng.choice(pools.species)
        member["form"] = 0
        member["gender"] = 0
        member["ability"] = 0
    return len(data.get("party", []))


def randomize_species(data: dict, pools: Pools, rng: random.Random) -> None:
    if "abilities" in data:
        first, second = rng.sample(pools.abilities, 2)
        data["abilities"] = [first, second]
    if data.get("hidden_ability"):
        data["hidden_ability"] = rng.choice(pools.abilities)
    held = data.get("held_items")
    if held:
        for slot, item in held.items():
            if item != "ITEM_NONE":
                held[slot] = rng.choice(pools.items)
    learnset = data.get("learnset")
    if learnset and learnset.get("by_level"):
        chosen: set[str] = set()
        for index, entry in enumerate(learnset["by_level"]):
            pool = pools.damaging_moves if index == 0 else pools.moves
            move = rng.choice(pool)
            while move in chosen:
                move = rng.choice(pool)
            chosen.add(move)
            entry[1] = move


def randomize_shops(data, pools: Pools, rng: random.Random) -> int:
    """Replaces the items of every list of the marts, except the Poké Balls. Returns how many."""
    count = 0
    if isinstance(data, list):
        if data and all(isinstance(item, str) and item.startswith("ITEM_") for item in data):
            used = set(data)
            for index, item in enumerate(data):
                if item in KEPT_BALLS:
                    continue
                new = rng.choice(pools.items)
                while new in used:
                    new = rng.choice(pools.items)
                used.add(new)
                data[index] = new
                count += 1
            return count
        for child in data:
            count += randomize_shops(child, pools, rng)
    elif isinstance(data, dict):
        for child in data.values():
            count += randomize_shops(child, pools, rng)
    return count


def randomize_events(data: dict, pools: Pools, rng: random.Random) -> int:
    """Replaces the item of every ground item (an NPC of global script 2000, whose first parameter is the item)."""
    items = load_list("items")
    count = 0
    for npc in data.get("npcs", []) if isinstance(data, dict) else []:
        if npc.get("script") == GROUND_ITEM_SCRIPT and npc.get("params") and npc["params"][0] > 0:
            npc["params"][0] = items[rng.choice(pools.items)]
            count += 1
    return count


def dumps(data) -> str:
    return json.dumps(data, indent=4, ensure_ascii=False) + "\n"


def write_if_changed(path: Path, text: str) -> None:
    """Writes a file only if it differs, so that the build doesn't repack what a new run left the same."""
    if path.is_file() and path.read_text(encoding="utf-8") == text:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def species_directories(pools: Pools) -> set[str]:
    return {species_data.directory(name) for name in pools.species}


def randomize(seed: str, root: Path = ROOT, output: Path = DEFAULT_OUTPUT) -> dict[str, int]:
    """Writes the randomized copies under output. Returns how many things of each kind it changed."""
    pools = Pools()
    summary = {"wild_slots": 0, "trainer_pokemon": 0, "species": 0, "shop_items": 0, "ground_items": 0}
    randomized_species = species_directories(pools)

    for directory, patterns in COPIED.items():
        source = root / directory
        for pattern in patterns:
            for path in sorted(source.rglob(pattern)):
                relative = path.relative_to(source)
                target = output / directory / relative
                text = path.read_text(encoding="utf-8")
                if path.suffix == ".json":
                    data = json.loads(text)
                    changed = False
                    if directory == "res/field/encounters":
                        n = randomize_encounters(data, pools, stream(seed, f"wild:{relative}"))
                        summary["wild_slots"] += n
                        changed = n > 0
                    elif directory == "res/trainers/data":
                        if isinstance(data, dict) and "party" in data:
                            summary["trainer_pokemon"] += randomize_trainer(data, pools, stream(seed, f"trainer:{relative}"))
                            changed = True
                    elif directory == "res/field/shops":
                        n = randomize_shops(data, pools, stream(seed, "shops"))
                        summary["shop_items"] += n
                        changed = n > 0
                    elif directory == "res/field/events":
                        n = randomize_events(data, pools, stream(seed, f"events:{relative}"))
                        summary["ground_items"] += n
                        changed = n > 0
                    elif directory == "res/pokemon" and relative.parts[0] in randomized_species:
                        if isinstance(data, dict) and any(k in data for k in ("abilities", "learnset", "held_items")):
                            randomize_species(data, pools, stream(seed, f"species:{relative}"))
                            summary["species"] += 1
                            changed = True
                    if changed:
                        text = dumps(data)
                write_if_changed(target, text)

    write_if_changed(output / "seed.txt", seed + "\n")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("seed")
    parser.add_argument("output", type=Path, nargs="?", default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    summary = randomize(args.seed, ROOT, args.output)
    print(f"Randomized with seed {args.seed!r} into {args.output}: " +
          ", ".join(f"{n} {kind.replace('_', ' ')}" for kind, n in summary.items()))


if __name__ == "__main__":
    main()
