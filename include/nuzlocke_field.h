#ifndef POKEBW2_NUZLOCKE_FIELD_H
#define POKEBW2_NUZLOCKE_FIELD_H

// The Nuzlocke challenge's rules that the field applies around a battle (docs/nuzlocke.md): the first wild encounter of
// each place, the legendary ban, the death of the fainted and the lost challenge. Only a build with NUZLOCKE has them,
// and only event_battle.c includes this, since it has the tables

#include "types.h"

#ifdef NUZLOCKE

#include "battle/btl_setup.h"
#include "constants/battle.h"
#include "constants/pokemon.h"
#include "field/field.h"
#include "nuzlocke_data.h"
#include "pml/poke_party.h"
#include "save/event_work.h"
#include "system/game_data.h"
#include "system/game_system.h"

static inline BOOL Nuzlocke_IsBannedSpecies(u16 species) {
    int i;

    for (i = 0; i < NUZLOCKE_BANNED_COUNT; i++) {
        if (sNuzlockeBannedSpecies[i] == species) {
            return TRUE;
        }
    }
    return FALSE;
}

// Decides at the start of a wild battle whether the Pokémon can be caught, and uses up the place's encounter. A shiny
// can always be caught and doesn't use the place up, and a banned species can't be caught and doesn't either
static inline void Nuzlocke_PrepareWildBattle(GameSystem *gsys, Field *field, BtlSetup *setup) {
    EventWork *eventWork = GameData_GetEventWork(GSYS_GetGameData(gsys));
    PartyPkm *pkm = PokeParty_GetPkm(BtlSetup_GetParty(setup, 1), 0);
    u16 zone = Field_GetPlayerStateZoneID(field);
    u16 flag;

    if (EventWork_FlagGet(eventWork, NUZLOCKE_FAILED_FLAG)) {
        BtlSetup_SetFlag(setup, BTL_SETUP_FLAG_NO_CAPTURE);
        return;
    }
    if (PokeParty_IsRare(pkm)) {
        return;
    }
    if (Nuzlocke_IsBannedSpecies(PokeParty_GetParam(pkm, PKM_PARAM_SPECIES, NULL))) {
        BtlSetup_SetFlag(setup, BTL_SETUP_FLAG_NO_CAPTURE);
        return;
    }
    if (zone >= NUZLOCKE_ZONE_COUNT) {
        return;
    }
    flag = sNuzlockePlaceFlags[sNuzlockeZonePlaces[zone]];
    if (EventWork_FlagGet(eventWork, flag)) {
        BtlSetup_SetFlag(setup, BTL_SETUP_FLAG_NO_CAPTURE);
    } else {
        EventWork_FlagSet(eventWork, flag);
    }
}

// After a wild or trainer battle has been written back to the party: a Pokémon that fainted is dead and leaves the
// party for good, and a party that has all fainted loses the challenge (it is left alone, for the blackout)
static inline void Nuzlocke_OnBattleReturn(GameData *gameData, BtlSetup *setup) {
    PokeParty *party = GameData_GetParty(gameData);
    EventWork *eventWork = GameData_GetEventWork(gameData);
    int count = PokeParty_GetPkmCount(party);
    int fainted = 0;
    int i;

    if (setup->battleType != BTL_TYPE_WILD && setup->battleType != BTL_TYPE_TRAINER) {
        return;
    }
    if (EventWork_FlagGet(eventWork, NUZLOCKE_FAILED_FLAG)) {
        return;
    }
    for (i = 0; i < count; i++) {
        if (PokeParty_GetParam(PokeParty_GetPkm(party, i), PKM_PARAM_HP, NULL) == 0) {
            fainted++;
        }
    }
    if (fainted == count) {
        EventWork_FlagSet(eventWork, NUZLOCKE_FAILED_FLAG);
        return;
    }
    for (i = count - 1; i >= 0; i--) {
        if (PokeParty_GetParam(PokeParty_GetPkm(party, i), PKM_PARAM_HP, NULL) == 0) {
            PokeParty_RemovePkm(party, i);
        }
    }
}

#endif // NUZLOCKE

#endif // POKEBW2_NUZLOCKE_FIELD_H
