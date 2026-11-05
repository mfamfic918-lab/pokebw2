#ifndef POKEBW2_NUZLOCKE_H
#define POKEBW2_NUZLOCKE_H

// The Nuzlocke challenge's level cap, for the battle (docs/nuzlocke.md). Only a build with NUZLOCKE has it

#include "types.h"
#include "pml/personal.h"

#ifdef NUZLOCKE

// The highest level a Pokémon may have for each number of badges: the level of the next Gym Leader's strongest
// Pokémon (res/trainers/data/leader_*.json), and after the eighth badge the Champion's
static const u8 sNuzlockeLevelCaps[9] = { 13, 18, 24, 30, 33, 39, 48, 51, 59 };

static inline u32 Nuzlocke_GetLevelCap(u32 badges) {
    if (badges > 8) {
        badges = 8;
    }
    return sNuzlockeLevelCaps[badges];
}

// The most experience a Pokémon may have under a level cap: just short of the next level
static inline u32 Nuzlocke_GetExpLimit(u16 species, u16 form, u32 levelCap) {
    if (levelCap >= 100) {
        return 0xffffffff;
    }
    return PML_UtilGetPkmLvExp(species, form, levelCap + 1) - 1;
}

#endif // NUZLOCKE

#endif // POKEBW2_NUZLOCKE_H
