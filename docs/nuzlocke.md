# Nuzlocke challenge and randomizer

Two build options turn the game into a randomized Nuzlocke. Both make the ROMs not match, so the build skips the
matching checks (see [Modified builds](building.md#modified-builds)). Configure again without them to get the matching
build back.

```sh
python3 configure.py --nuzlocke                  # the challenge's rules
python3 configure.py --randomize SEED            # the randomizer, with any text as the seed
python3 configure.py --nuzlocke --randomize SEED # both
ninja
```

The TV in the player's room (the Wii console, in Aspertia City's house) lists the rules in Spanish. Interact with it to
read them. The menu is part of every build, with or without the options.

## Randomizer

`tools/randomizer/randomize.py` writes randomized copies of the data under `build/randomized/`, and `configure.py` packs
the archives from the copies in place of `res/`, which is never changed. The same seed gives the same data, and another
seed gives other data. Run it alone to look at the result: `python3 tools/randomizer/randomize.py SEED OUTPUT_DIR`.

| What | Where | How |
| --- | --- | --- |
| Wild Pokémon | `res/field/encounters` | Each slot's species, with its levels, from every species 1 to 649, so legendary Pokémon can appear anywhere |
| Trainers' and leaders' teams | `res/trainers/data` | Each Pokémon's species, with its level. Form, gender and ability slot go back to the default |
| Abilities | `res/pokemon/*/data.json` | Both abilities and the hidden one of every species |
| Moves | `res/pokemon/*/data.json` | The moves of every level-up learnset, with the first one always damaging |
| Items held by wild Pokémon | `res/pokemon/*/data.json` | Each item a species holds, from the items that are not key items, TMs or HMs |
| Poké Mart items | `res/field/shops` | Every item except the Poké, Great and Ultra Balls, so that catching stays possible |
| Items on the ground | `res/field/events` | The item of every item ball (an NPC of global script 2000) |

Not randomized: the starter Pokémon (the selection screen shows fixed models of Snivy, Tepig and Oshawott, so a
different Pokémon would not be the one shown), the TMs' and tutors' moves, items given by scripts or found hidden,
and the Pokémon given in events.

## Rules

The rules are applied by the code under `#ifdef NUZLOCKE`. The TV lists all of them.

| Rule | How it is applied | Where |
| --- | --- | --- |
| First Pokémon of each place | A wild battle uses up its place's encounter when it starts, and a Poké Ball never catches in a place whose encounter was used. A place is a `place` of `res/field/zones`, so the floors of a cave count once | `nuzlocke_field.h`, `event_battle.c`, `btl_server_flow_sub.c` |
| Death | After a battle, a Pokémon at 0 HP leaves the party for good (it is released) | `Nuzlocke_OnBattleReturn` |
| Mandatory nicknames | The nickname is always asked after a catch, and a cancelled entry or the species' name asks again | `event_battle_return.c` |
| Fixed battle style | `Config_GetBattleStyle` is always Set, and the options screen can't change it | `config.c`, `config_panel.c` |
| Game over | If every Pokémon has fainted, the challenge is lost: a flag is set, no more Pokémon can be caught, and the TV says so. Nothing is deleted | `Nuzlocke_OnBattleReturn` |
| Level cap | No experience passes the strongest Pokémon of the next Gym Leader (13, 18, 24, 30, 33, 39, 48, 51 for 0 to 7 badges, then the Champion's 59). The Rare Candy does nothing | `btl_server_flow.c`, `nuzlocke.h`, `pml_item.c` |
| Shiny | A shiny Pokémon can always be caught and doesn't use its place's encounter | `Nuzlocke_PrepareWildBattle` |
| Legendary ban | The 48 legendary and 18 pseudo-legendary species of `nuzlocke_data.h` can't be caught, and don't use the place's encounter | `Nuzlocke_PrepareWildBattle` |
| No healing items | The HP and PP restoring and the status restoring pockets of the battle bag stay empty. Held items still work, and so do the Pokémon Centers | `b_bag_item.c` |
| Randomized wild Pokémon, moves, abilities, trainers, items | The randomizer, above | `tools/randomizer/` |

Limits to know:

- A caught Pokémon that can't go to the party goes to a box as usual. A Pokémon that dies is released, not boxed.
- Wild battles all count, scripted ones too. Wild and trainer battles kill Pokémon, but the battles of facilities such as
  the Battle Subway, link battles and the capture demonstration don't (`BTL_TYPE_FACILITY`, `BTL_TYPE_COMM`).
- The game-over rule can't restart the game. It marks the challenge as lost.
- The level cap stops experience, so a Pokémon can sit at the cap with its bar full. Levels above the cap that come from
  elsewhere (a trade, a Pokémon already above it) are not lowered.
- The state is in saved event flags that no script, event or code names: `NUZLOCKE_FAILED_FLAG` (0x01f2) and one flag
  per place from 0x01f3 to 0x044b (`include/nuzlocke_data.h`). The save keeps its layout.
- `include/nuzlocke_data.h` is generated: `python3 tools/randomizer/gen_nuzlocke_data.py`.
- None of this has been run in the game yet, only assembled, packed and checked for syntax. Test each rule.
