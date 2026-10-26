/* X1-inspired capabilities over original X4 movement/projectile routines.
 * Permanent campaign upgrades are never cleared. Only the current player's
 * transient capabilities and scoped native reads are adapted. */
#include "mmx4_x1.h"
#include "mmx4_coop_internal.h"
#include "mod_runtime.h"
#include "mod_plugins.h"
#include <string.h>

#define PLAYER MMX4_PLAYER
#define PLAY MMX4_PLAY
static unsigned native_call,virtual_zero;

int mmx4_x1_enabled(unsigned character) {
    return character<2 && mod_runtime_snapshot_package_active(character?
        "mmx4.character.x1-zero":"mmx4.character.x1-x");
}
int mmx4_x1_buster_context(void) {return virtual_zero!=0;}
int mmx4_x1_native_ready(void) {return !native_call;}
void mmx4_x1_native_reset(void) {native_call=virtual_zero=0;}
void mmx4_x1_enforce_current(void) {
    if(!mmx4_x1_enabled(psx_mod_read_byte(PLAYER+2)))return;
    /* A7/B8 are per-body copies of the saved armor bytes. The original
     * progress remains in PLAY+47/48 for later boots with this mod disabled. */
    psx_mod_write_byte(PLAYER+0xA7,0);
    psx_mod_write_byte(PLAYER+0xB8,0);
}

static int native_step(CPUState *cpu,uint32_t address) {
    if(native_call || psx_mod_local_view_scope())return 0;
    unsigned character=psx_mod_read_byte(PLAYER+2);
    if(!mmx4_x1_enabled(character))return 0;
    int movement=address==0x800312B4u;
    if(!movement) {
        psx_mod_counter_add("mmx4.x1.buster-updates",1);
        uint32_t actor=cpu->gpr[4];
        if(actor>=0x801406F8u && actor<0x801410B8u &&
           (actor-0x801406F8u)%0x9Cu==0 && !psx_mod_read_byte(actor+4)) {
            unsigned type=psx_mod_read_byte(actor+1);
            psx_mod_counter_add(type==18?"mmx4.x1.full-shots":
                type==9?"mmx4.x1.medium-shots":"mmx4.x1.normal-shots",1);
        }
    }
    /* Keep authored doors, vehicles, story actions, arrivals and death on
     * their logical character. Only ordinary on-foot Zero control becomes
     * native buster control. X's normal weapon selection remains available. */
    if(movement && (cpu->gpr[4]!=PLAYER ||
       psx_mod_read_byte(PLAYER+5)<2 || psx_mod_read_byte(PLAYER+5)>15 ||
       psx_mod_read_byte(PLAYER+0xC5))) {
        mmx4_x1_enforce_current();return 0;
    }
    uint32_t resources[4];
    if(character && !mmx4_x1_x_resources(resources)) {
        /* Never fall back to an ordinary Zero saber update while an X1
         * body waits for its native buster resources at stage enrollment. */
        mmx4_x1_enforce_current();
        psx_mod_counter_add("mmx4.x1.waiting-for-buster-resources",1);
        cpu->gpr[2]=0;return 1;
    }
    uint8_t armor[2]={psx_mod_read_byte(PLAY+0x47),psx_mod_read_byte(PLAY+0x48)};
    uint8_t campaign=psx_mod_read_byte(PLAY+0x43),code=psx_mod_read_byte(PLAY+0x37);
    uint8_t weapon=psx_mod_read_byte(PLAY+0x60);
    uint32_t scratch[4],stats=psx_mod_read_word(PLAYER+0x30);
    uint32_t foot_delta=(psx_mod_read_byte(PLAYER+0x15)&0x20u)?0xFFFF0000u:0x10000u;
    static const unsigned offsets[4]={0x14,0x1C,0x24,0x28};
    native_call=1;virtual_zero=character;
    psx_mod_write_byte(PLAY+0x47,0);psx_mod_write_byte(PLAY+0x48,0);
    psx_mod_write_byte(PLAY+0x37,0);mmx4_x1_enforce_current();
    if(character) {
        for(unsigned i=0;i<4;++i) {
            scratch[i]=psx_mod_read_word(0x1F800000u+offsets[i]);
            psx_mod_write_word(0x1F800000u+offsets[i],resources[i]);
        }
        psx_mod_write_byte(PLAYER+2,0);psx_mod_write_byte(PLAY+0x43,0);
        psx_mod_write_byte(PLAY+0x60,0);psx_mod_write_byte(PLAYER+0x93,0);
        psx_mod_write_word(PLAYER+0x30,0x80119DF0u);
        if(movement) {
            /* Native Zero's foot origin is one pixel above X's. */
            psx_mod_write_word(PLAYER+12,psx_mod_read_word(PLAYER+12)+foot_delta);
            psx_mod_write_word(PLAYER+28,psx_mod_read_word(PLAYER+28)+foot_delta);
        }
    }
    uint32_t result=psx_mod_call_guest(cpu,address,cpu->gpr[31],
        cpu->gpr[4],cpu->gpr[5],cpu->gpr[6],cpu->gpr[7]);
    if(character) {
        if(movement) {
            psx_mod_write_word(PLAYER+12,psx_mod_read_word(PLAYER+12)-foot_delta);
            psx_mod_write_word(PLAYER+28,psx_mod_read_word(PLAYER+28)-foot_delta);
        }
        psx_mod_write_byte(PLAYER+2,(uint8_t)character);
        psx_mod_write_word(PLAYER+0x30,stats);
        for(unsigned i=0;i<4;++i)psx_mod_write_word(0x1F800000u+offsets[i],scratch[i]);
        psx_mod_write_byte(PLAY+0x43,campaign);psx_mod_write_byte(PLAY+0x60,weapon);
    }
    psx_mod_write_byte(PLAY+0x47,armor[0]);psx_mod_write_byte(PLAY+0x48,armor[1]);
    psx_mod_write_byte(PLAY+0x37,code);mmx4_x1_enforce_current();
    virtual_zero=native_call=0;
    cpu->gpr[2]=result;return 1;
}
static int armor_draw(CPUState *cpu,uint32_t address) {
    (void)address;
    if(cpu->gpr[4]!=PLAYER || !mmx4_x1_enabled(psx_mod_read_byte(PLAYER+2)))return 0;
    cpu->gpr[2]=0;return 1;
}
static int aerial_ability(CPUState *cpu,uint32_t address) {
    (void)address;
    if(cpu->gpr[4]!=PLAYER || (!virtual_zero &&
       !mmx4_x1_enabled(psx_mod_read_byte(PLAYER+2))))return 0;
    /* Retail 8003484C enters air dash; 800347D0 enters double jump.
     * Neither belongs to these X1 forms. Ground dash and wall kicks use
     * separate native entry points and retain their ordinary controls. */
    cpu->gpr[2]=0;return 1;
}
static void enforce(CPUState *cpu,uint32_t address) {
    (void)cpu;(void)address;mmx4_x1_enforce_current();
}
static void iris_buster_hit(CPUState *cpu,uint32_t address) {
    (void)address;
    if(!mmx4_x1_enabled(1) || psx_mod_local_view_scope() ||
       (!virtual_zero && psx_mod_read_byte(PLAYER+2)!=1) ||
       psx_mod_read_byte(PLAY)!=6 || psx_mod_read_byte(PLAY+0x0C)!=11 ||
       psx_mod_read_byte(PLAY+0x0D) || cpu->gpr[2]!=0xFFu)return;
    uint32_t actor=cpu->gpr[4],type=cpu->gpr[6],table=cpu->gpr[7];
    if(actor<0x8013BED0u || actor>=0x8013DC10u || (actor-0x8013BED0u)%0x9Cu ||
       !psx_mod_read_byte(actor) || psx_mod_read_byte(actor+1)!=66 ||
       psx_mod_read_byte(actor+2)>1 || (type!=0 && type!=9 && type!=18) ||
       (table!=0x80107DFCu && table!=0x80107E84u))return;
    /* Iris has no retail buster entries. Use the same native Zero reaction
     * rows as the existing co-op X admission, retaining her armor exposure,
     * actual attack identity/consumption and the separate cooldown table.
     * This hook also operates in solo Zero's campaign. */
    unsigned entry=type==0?32u:24u;
    cpu->gpr[2]=psx_mod_read_byte(table+entry*2u);
    cpu->gpr[7]=table+(entry-type)*2u;
    psx_mod_counter_add("mmx4.x1.iris-buster-hits",1);
}
PSX_MOD_CONSTRUCTOR(mmx4_register_x1_capabilities) {
    static const char *const plugins[]={"mmx4.x1_x","mmx4.x1_zero"};
    for(unsigned i=0;i<2;++i) {
        psx_mod_register_function_filter_plugin(plugins[i],0x800312B4u,native_step);
        psx_mod_register_function_filter_plugin(plugins[i],0x800922D8u,native_step);
        psx_mod_register_function_filter_plugin(plugins[i],0x80092648u,native_step);
        psx_mod_register_function_filter_plugin(plugins[i],0x800257BCu,armor_draw);
        psx_mod_register_function_filter_plugin(plugins[i],0x8003484Cu,aerial_ability);
        psx_mod_register_function_filter_plugin(plugins[i],0x800347D0u,aerial_ability);
        psx_mod_register_function_entry_plugin(plugins[i],0x80035EF0u,enforce);
    }
    psx_mod_register_instruction_plugin("mmx4.x1_zero",0x8002DE84u,0xA0820063u,iris_buster_hit);
}
