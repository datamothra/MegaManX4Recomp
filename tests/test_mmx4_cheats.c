/* Policy tests run without game data. With an explicit original PS-X EXE,
 * execute bounded original instructions for resource choice, palette copy,
 * selector clearing, capsule eligibility/grant and Nova gating/energy.
 * The tiny fixture runner rejects all instructions outside its tested subset;
 * it is not a gameplay emulator or a replacement implementation of the code. */
#include "mmx4_cheats.h"
#include "mod_plugins.h"
#include "mod_runtime.h"
#include "mod_snapshot.h"
#include "cpu_state.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define CHECK(x) do { if (!(x)) { fprintf(stderr,"line %d: %s\n",__LINE__,#x); return 1; } } while (0)
#define REQUIRE(x) do { if (!(x)) { fprintf(stderr,"line %d: %s\n",__LINE__,#x); abort(); } } while (0)
#define PLAY 0x801721C0u
#define PLAYER 0x801418C8u
#define ULTIMATE_PACKAGE "mmx4.cheat.ultimate-armor"
#define BLACK_PACKAGE "mmx4.cheat.black-zero"
#define ULTIMATE_PLUGIN "mmx4.ultimate_armor"
#define BLACK_PLUGIN "mmx4.black_zero"

static uint8_t ram[2u * 1024u * 1024u], scratch[1024];
static unsigned local_ultimate, local_black, coop_active, online_profile;
static unsigned projected_second, registration_failures;
static unsigned x1_enabled[2],x1_virtual;
int mmx4_x1_enabled(unsigned character) {return character<2 && x1_enabled[character];}
int mmx4_x1_buster_context(void) {return x1_virtual;}
static unsigned guest_calls, requested_character, native_loaded;
typedef struct { const char *id; uint32_t address; PSXModFunctionEntryCallback callback; } Entry;
typedef struct { const char *id; uint32_t address; PSXModFunctionFilterCallback callback; } Filter;
typedef struct { const char *id; PSXModActivationCallback callback; } Activation;
typedef struct { const char *id; PSXModSnapshotProvider provider; } Provider;
typedef struct { const char *id; PSXModActivationCallback callback; } Restore;
static Entry entries[32]; static unsigned entry_count;
static Filter filters[4]; static unsigned filter_count;
static Activation activations[2]; static unsigned activation_count;
static Provider providers[2]; static unsigned provider_count;
static Restore restores[2]; static unsigned restore_count;

int mod_runtime_snapshot_package_active(const char *id) {
    if (online_profile) return !strcmp(id,"mmx4.coop");
    if (!strcmp(id,ULTIMATE_PACKAGE)) return local_ultimate;
    if (!strcmp(id,BLACK_PACKAGE)) return local_black;
    if (!strcmp(id,"mmx4.coop")) return coop_active;
    return 0;
}
int mmx4_coop_projected(void) { return (int)projected_second; }
int psx_mod_register_function_entry_plugin(const char *id, uint32_t address, PSXModFunctionEntryCallback cb) {
    /* Real runtime registration rejects a second same-plugin/address hook.
     * These existing co-op owner hooks must never be shadowed or displaced. */
    if (!strcmp(id,"mmx4.coop") && (address==0x80035240u ||
        address==0x800C62DCu || address==0x800C6EDCu)) {
        ++registration_failures; return 0;
    }
    for(unsigned i=0;i<entry_count;++i) if (!strcmp(entries[i].id,id) && entries[i].address==address) {
        ++registration_failures; return 0;
    }
    REQUIRE(entry_count < sizeof entries / sizeof entries[0]);
    entries[entry_count++] = (Entry){id,address,cb}; return 1;
}
int psx_mod_register_function_filter_plugin(const char *id, uint32_t address, PSXModFunctionFilterCallback cb) {
    REQUIRE(filter_count < sizeof filters / sizeof filters[0]);
    filters[filter_count++] = (Filter){id,address,cb}; return 1;
}
int psx_mod_register_activation_plugin(const char *id, PSXModActivationCallback cb) {
    REQUIRE(activation_count < sizeof activations / sizeof activations[0]);
    activations[activation_count++] = (Activation){id,cb}; return 1;
}
int psx_mod_register_snapshot_guard(const char *id, int (*ready)(void), uint32_t version,
                                  int (*validate)(const uint8_t *,uint32_t)) {
    REQUIRE(provider_count < sizeof providers / sizeof providers[0]);
    providers[provider_count++] = (Provider){id,{version,NULL,NULL,validate,NULL,ready}}; return 1;
}
int psx_mod_register_savestate_plugin(const char *id, PSXModActivationCallback callback) {
    REQUIRE(restore_count<2);restores[restore_count++]=(Restore){id,callback};return 1;
}
static uint8_t *byte_at(uint32_t address) {
    uint32_t physical = address & 0x1FFFFFFFu;
    if (physical < sizeof ram) return ram + physical;
    REQUIRE(address >= 0x1F800000u && address - 0x1F800000u < sizeof scratch);
    return scratch + address - 0x1F800000u;
}
uint8_t psx_mod_read_byte(uint32_t address) { return *byte_at(address); }
void psx_mod_write_byte(uint32_t address, uint8_t value) { *byte_at(address) = value; }
uint16_t psx_mod_read_half(uint32_t a) { return (uint16_t)(psx_mod_read_byte(a) | psx_mod_read_byte(a+1) << 8); }
void psx_mod_write_half(uint32_t a, uint16_t v) { psx_mod_write_byte(a,(uint8_t)v); psx_mod_write_byte(a+1,(uint8_t)(v>>8)); }
uint32_t psx_mod_read_word(uint32_t a) { return psx_mod_read_half(a) | (uint32_t)psx_mod_read_half(a+2) << 16; }
void psx_mod_write_word(uint32_t a, uint32_t v) { psx_mod_write_half(a,(uint16_t)v); psx_mod_write_half(a+2,(uint16_t)(v>>16)); }

static PSXModFunctionFilterCallback filter_for(const char *id) {
    for (unsigned i=0;i<filter_count;++i) if (!strcmp(filters[i].id,id)) return filters[i].callback;
    REQUIRE(0); return NULL;
}
static void entry_for(const char *id, uint32_t address, CPUState *cpu) {
    for (unsigned i=0;i<entry_count;++i)
        if (!strcmp(entries[i].id,id) && entries[i].address == address) {
            entries[i].callback(cpu,address); return;
        }
    REQUIRE(0);
}
static void activate(const char *id) {
    for (unsigned i=0;i<activation_count;++i) if (!strcmp(activations[i].id,id)) {
        activations[i].callback(); return;
    }
    REQUIRE(0);
}

/* Run only until a specified boundary BEFORE that instruction. Branches and
 * R3000A register loads retain their delay slots. No peripheral/timing model
 * is needed for these pure RAM code paths. */
static int native_run(CPUState *cpu, uint32_t start, uint32_t stop1, uint32_t stop2) {
    uint32_t pc=start, branch_target=0, load_value=0;
    unsigned branch_pending=0, load_register=0;
    for (unsigned steps=0;steps<2048;++steps) {
        if (pc==stop1 || (stop2 && pc==stop2)) { cpu->pc=pc; return 1; }
        uint32_t instruction=psx_mod_read_word(pc), op=instruction>>26;
        unsigned rs=(instruction>>21)&31,rt=(instruction>>16)&31,rd=(instruction>>11)&31;
        uint32_t left=cpu->gpr[rs],right=cpu->gpr[rt],result=0,target=0,new_load=0;
        int32_t immediate=(int16_t)instruction;
        unsigned written=0,new_branch=0,new_load_register=0;
        switch (op) {
        case 0:
            switch (instruction&63) {
            case 0: written=rd;result=right<<((instruction>>6)&31);break;
            case 8: target=left;new_branch=1;break;
            case 0x21: written=rd;result=left+right;break;
            case 0x24: written=rd;result=left&right;break;
            case 0x25: written=rd;result=left|right;break;
            case 0x2B: written=rd;result=left<right;break;
            default: goto unsupported;
            } break;
        case 2: target=((pc+4)&0xF0000000u)|((instruction&0x03FFFFFFu)<<2);new_branch=1;break;
        case 3: target=((pc+4)&0xF0000000u)|((instruction&0x03FFFFFFu)<<2);new_branch=1;written=31;result=pc+8;break;
        case 4: if(left==right){target=pc+4+(uint32_t)(immediate*4);new_branch=1;}break;
        case 5: if(left!=right){target=pc+4+(uint32_t)(immediate*4);new_branch=1;}break;
        case 9: written=rt;result=left+(uint32_t)immediate;break;
        case 0xB: written=rt;result=left<(uint32_t)immediate;break;
        case 0xC: written=rt;result=left&(instruction&0xFFFF);break;
        case 0xD: written=rt;result=left|(instruction&0xFFFF);break;
        case 0xF: written=rt;result=instruction<<16;break;
        case 0x20: new_load_register=rt;new_load=(uint32_t)(int32_t)(int8_t)psx_mod_read_byte(left+(uint32_t)immediate);break;
        case 0x23: new_load_register=rt;new_load=psx_mod_read_word(left+(uint32_t)immediate);break;
        case 0x24: new_load_register=rt;new_load=psx_mod_read_byte(left+(uint32_t)immediate);break;
        case 0x25: new_load_register=rt;new_load=psx_mod_read_half(left+(uint32_t)immediate);break;
        case 0x28: psx_mod_write_byte(left+(uint32_t)immediate,(uint8_t)right);break;
        case 0x29: psx_mod_write_half(left+(uint32_t)immediate,(uint16_t)right);break;
        case 0x2B: psx_mod_write_word(left+(uint32_t)immediate,right);break;
        default: goto unsupported;
        }
        if (branch_pending && new_branch) goto unsupported;
        if (load_register && load_register != written) cpu->gpr[load_register]=load_value;
        if (written) cpu->gpr[written]=result;
        load_register=new_load_register;load_value=new_load;
        uint32_t next=branch_pending?branch_target:pc+4;
        branch_pending=new_branch;branch_target=target;pc=next;
        cpu->gpr[0]=0;
        continue;
unsupported:
        fprintf(stderr,"unsupported fixture instruction %08x at %08x\n",instruction,pc);return 0;
    }
    fprintf(stderr,"native fixture exceeded bounded instruction budget\n");return 0;
}

uint32_t psx_mod_call_guest(CPUState *cpu, uint32_t function, uint32_t return_address,
                           uint32_t a0,uint32_t a1,uint32_t a2,uint32_t a3) {
    REQUIRE(function==0x800297D8u && return_address==cpu->gpr[31]);
    REQUIRE(a0==cpu->gpr[4]&&a1==cpu->gpr[5]&&a2==cpu->gpr[6]&&a3==cpu->gpr[7]);
    REQUIRE(!mmx4_cheats_snapshot_ready());
    for (unsigned i=0;i<provider_count;++i) {
        REQUIRE(!providers[i].provider.ready());
    }
    /* Recursive registrations from the other enabled package/co-op must
     * decline interception, leaving one original selector invocation. */
    for (unsigned i=0;i<filter_count;++i) REQUIRE(!filters[i].callback(cpu,function));
    ++guest_calls;
    CPUState saved=*cpu;
    if (native_loaded) {
        REQUIRE(native_run(cpu,function,0x8002985Cu,0));
        REQUIRE(psx_mod_read_byte(PLAY+0x43)==requested_character);
        REQUIRE(!psx_mod_read_byte(PLAY+0x37));
    } else {
        psx_mod_write_byte(PLAY+0x43,(uint8_t)requested_character);
        psx_mod_write_byte(PLAY+0x37,0); /* Original change-character clearing. */
    }
    *cpu=saved;return 0x13572468u;
}

static int policy(void) {
    CHECK(!registration_failures);
    CHECK(entry_count==15&&filter_count==3&&activation_count==2&&provider_count==2&&restore_count==2);
    CHECK(!strcmp(providers[0].id,ULTIMATE_PACKAGE)&&!strcmp(providers[1].id,BLACK_PACKAGE));
    CPUState cpu={0};cpu.gpr[4]=PLAY;cpu.gpr[31]=0x80012340u;
    mmx4_cheats_configure_coop(1,1);
    CHECK(!mmx4_cheats_character_enabled(0)&&!mmx4_cheats_character_enabled(1));
    psx_mod_write_byte(PLAY+0x37,0);
    mmx4_cheats_enforce_current();CHECK(!psx_mod_read_byte(PLAY+0x37));
    CHECK(!filter_for("mmx4.coop")(&cpu,0x800297D8u)&&!guest_calls);
    /* Native manual codes survive when mods don't force a code. */
    psx_mod_write_byte(PLAY+0x37,1);
    mmx4_cheats_enforce_current();CHECK(psx_mod_read_byte(PLAY+0x37)==1);
    local_ultimate=1;
    CHECK(mmx4_cheats_character_enabled(0)&&!mmx4_cheats_character_enabled(1));
    local_black=1;CHECK(mmx4_cheats_character_enabled(1));
    CHECK(!mmx4_cheats_character_enabled(2)&&!mmx4_cheats_character_enabled(~0u));
    for(unsigned character=0;character<2;++character) {
        x1_enabled[character]=1;CHECK(!mmx4_cheats_character_enabled(character));
        CHECK(mmx4_cheats_character_enabled(character^1u));x1_enabled[character]=0;
    }
    x1_virtual=1;CHECK(!mmx4_cheats_character_enabled(0) && !mmx4_cheats_character_enabled(1));
    x1_virtual=0;
    local_ultimate=local_black=0;coop_active=1;
    CHECK(mmx4_cheats_character_enabled(0)&&mmx4_cheats_character_enabled(1));
    activate(ULTIMATE_PLUGIN);activate(BLACK_PLUGIN);
    CHECK(mmx4_cheats_character_enabled(0)&&mmx4_cheats_character_enabled(1));
    mmx4_cheats_configure_coop(0,1);CHECK(!mmx4_cheats_character_enabled(0)&&mmx4_cheats_character_enabled(1));
    coop_active=0;CHECK(!mmx4_cheats_character_enabled(1));
    /* Forced profiles select agreed options; local standalone mods can't
     * silently alter an online session's characters. */
    local_ultimate=local_black=1;online_profile=1;
    CHECK(!mmx4_cheats_character_enabled(0)&&mmx4_cheats_character_enabled(1));
    mmx4_cheats_configure_coop(0,0);CHECK(!mmx4_cheats_character_enabled(0)&&!mmx4_cheats_character_enabled(1));
    online_profile=0;CHECK(mmx4_cheats_character_enabled(0)&&mmx4_cheats_character_enabled(1));
    /* A P2 actor scope can keep P1's campaign selection. Its disabled Black
     * Zero choice must stay disabled even while P1's Ultimate choice is on. */
    coop_active=1;projected_second=1;local_black=0;mmx4_cheats_configure_coop(1,0);
    psx_mod_write_byte(PLAY+0x43,0);psx_mod_write_byte(PLAYER+2,1);psx_mod_write_byte(PLAY+0x37,0);
    mmx4_cheats_enforce_current();CHECK(!psx_mod_read_byte(PLAY+0x37));
    entry_for("mmx4.coop",0x800361F8u,&cpu);CHECK(!psx_mod_read_byte(PLAY+0x37));
    CHECK(!filter_for("mmx4.coop")(&cpu,0x800297D8u)&&!guest_calls);
    /* Stale projection statics from a disabled old co-op session must not
     * suppress a standalone option in the current single-player session. */
    coop_active=0;local_black=1;psx_mod_write_byte(PLAY+0x43,1);
    mmx4_cheats_enforce_current();CHECK(psx_mod_read_byte(PLAY+0x37)==1);
    projected_second=0;
    uint8_t protected_body[0xE4];memset(protected_body,0x5A,sizeof protected_body);
    memcpy(byte_at(PLAYER),protected_body,sizeof protected_body);
    for(unsigned character=0;character<2;++character) {
        psx_mod_write_byte(PLAY+0x43,(uint8_t)character);
        for (unsigned i=0;i<entry_count;++i) {
            psx_mod_write_byte(PLAY+0x37,0);entries[i].callback(&cpu,entries[i].address);
            CHECK(psx_mod_read_byte(PLAY+0x37)==1);
            CHECK(!memcmp(byte_at(PLAYER),protected_body,sizeof protected_body));
        }
    }
    for(unsigned i=0;i<provider_count;++i) {
        const PSXModSnapshotProvider *p=&providers[i].provider;uint8_t data=1;
        CHECK(p->version==1&&!p->bytes&&!p->write&&!p->read&&p->ready());
        CHECK(p->validate(&data,1)&&!p->validate(&data,0));data=0;CHECK(!p->validate(&data,1));
        CHECK(!p->validate(NULL,1)&&!p->validate(&data,2));
        psx_mod_write_byte(PLAY+0x37,0);restores[i].callback();
        CHECK(psx_mod_read_byte(PLAY+0x37)==1);
    }
    /* Reapply the newly selected character after native clears the flag. */
    local_black=0;requested_character=1;
    CHECK(filter_for(ULTIMATE_PLUGIN)(&cpu,0x800297D8u));
    CHECK(guest_calls==1&&cpu.gpr[2]==0x13572468u&&!psx_mod_read_byte(PLAY+0x37));
    requested_character=0;
    CHECK(filter_for(ULTIMATE_PLUGIN)(&cpu,0x800297D8u));
    CHECK(guest_calls==2&&psx_mod_read_byte(PLAY+0x37)==1&&mmx4_cheats_snapshot_ready());
    CHECK(cpu.gpr[4]==PLAY&&cpu.gpr[31]==0x80012340u);
    local_black=1;requested_character=1;
    CHECK(filter_for(BLACK_PLUGIN)(&cpu,0x800297D8u));
    CHECK(guest_calls==3&&psx_mod_read_byte(PLAY+0x37)==1);
    local_ultimate=local_black=0;mmx4_cheats_configure_coop(0,0);
    CHECK(!mmx4_cheats_character_enabled(0)&&!mmx4_cheats_character_enabled(1));
    /* Restore applies a newly enabled palette without resetting the body or
     * trusting invalid scratch resource pointers. */
    psx_mod_write_byte(PLAY,6);psx_mod_write_byte(PLAY+0x43,1);
    psx_mod_write_word(0x1F800024u,0x801E0000u);psx_mod_write_word(0x1F800028u,0x801E0400u);
    for(unsigned i=0;i<16;++i)psx_mod_write_half(0x801E0000u+13*32+i*2,(uint16_t)(0x6300+i));
    local_black=1;restores[1].callback();
    for(unsigned i=0;i<16;++i)CHECK(psx_mod_read_half(0x801E0400u+i*2)==0x6300+i);
    CHECK(!memcmp(byte_at(PLAYER),protected_body,sizeof protected_body));
    psx_mod_write_word(0x1F800024u,0x1F801000u);restores[1].callback();
    psx_mod_write_word(0x1F800028u,0);restores[1].callback();
    local_black=0;
    return 0;
}

static uint32_t le32(const uint8_t *p) { return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24; }
static int load_original(const char *path) {
    FILE *f=fopen(path,"rb");CHECK(f);uint8_t header[2048];
    CHECK(fread(header,1,sizeof header,f)==sizeof header);
    CHECK(!memcmp(header,"PS-X EXE",8));uint32_t address=le32(header+0x18),size=le32(header+0x1C);
    CHECK(address==0x80010000u&&size>0xC0000u&&size<=sizeof ram-(address&0x1FFFFFFFu));
    memset(ram,0,sizeof ram);memset(scratch,0,sizeof scratch);
    CHECK(fread(byte_at(address),1,size,f)==size);CHECK(!fclose(f));
    /* Reject another executable rather than silently testing wrong bytes. */
    CHECK(psx_mod_read_word(0x80012EB8u)==0x3C028017u);
    CHECK(psx_mod_read_word(0x800297D8u)==0x27BDFFE8u);
    CHECK(psx_mod_read_word(0x800361F8u)==0x27BDFFE8u);
    CHECK(psx_mod_read_word(0x800C709Cu)==0xA022196Fu);
    native_loaded=1;return 0;
}
static CPUState fixture_cpu(void) {
    CPUState cpu={0};cpu.gpr[29]=0x801FF000u;cpu.gpr[4]=PLAYER;return cpu;
}
static int original_contract(const char *path) {
    CHECK(!load_original(path));
    local_ultimate=local_black=coop_active=online_profile=projected_second=0;mmx4_cheats_configure_coop(0,0);
    CPUState cpu=fixture_cpu();
    psx_mod_write_byte(PLAY+0x43,0);psx_mod_write_byte(PLAY+0x37,0);
    entry_for(ULTIMATE_PLUGIN,0x80012EB8u,&cpu);
    CHECK(native_run(&cpu,0x80012EB8u,0x80012EF0u,0)&&cpu.gpr[4]==0x4Bu);
    local_ultimate=1;cpu=fixture_cpu();
    entry_for(ULTIMATE_PLUGIN,0x80012EB8u,&cpu);
    CHECK(native_run(&cpu,0x80012EB8u,0x80012EF0u,0)&&cpu.gpr[4]==0x4Eu);
    /* Enabling eligibility alone does not grant armor or Nova. */
    CHECK(!psx_mod_read_byte(PLAYER+0xA7)&&!psx_mod_read_byte(PLAYER+0xB8));
    cpu=fixture_cpu();psx_mod_write_byte(PLAYER+0xA8,0x30);psx_mod_write_half(PLAYER+0x80,0x40);
    CHECK(native_run(&cpu,0x800375B4u,0x8003764Cu,0x800376F4u)&&cpu.pc==0x800376F4u);
    psx_mod_write_byte(PLAY+0x43,1);local_black=1;cpu=fixture_cpu();
    entry_for(BLACK_PLUGIN,0x80012EB8u,&cpu);
    CHECK(native_run(&cpu,0x80012EB8u,0x80012EF0u,0)&&cpu.gpr[4]==0x4Du);
    /* The actual original palette helper copies all16 colors from row13. */
    const uint32_t source=0x801E0000u,destination=0x801E0400u;
    psx_mod_write_word(0x1F800024u,source);psx_mod_write_word(0x1F800028u,destination);
    for(unsigned i=0;i<16;++i) {
        psx_mod_write_half(source+i*2,(uint16_t)(0x1200+i));
        psx_mod_write_half(source+13*32+i*2,(uint16_t)(0x6300+i));
    }
    for(unsigned enabled=0;enabled<2;++enabled) {
        local_black=enabled;psx_mod_write_byte(PLAY+0x37,0);cpu=fixture_cpu();
        entry_for(BLACK_PLUGIN,0x800361F8u,&cpu);
        CHECK(native_run(&cpu,0x800362B0u,0x800362D0u,0));
        for(unsigned i=0;i<16;++i) CHECK(psx_mod_read_half(destination+i*2)==(enabled?0x6300u:0x1200u)+i);
    }
    /* Execute the original selector's real clear, then our post-call policy. */
    cpu=fixture_cpu();cpu.gpr[4]=PLAY;cpu.gpr[31]=0x80012340u;
    psx_mod_write_byte(PLAY+0x43,0);psx_mod_write_byte(PLAY+0x29,0);
    psx_mod_write_half(0x80166C0Cu,0x3000);requested_character=1;local_black=1;
    CHECK(filter_for(BLACK_PLUGIN)(&cpu,0x800297D8u)&&psx_mod_read_byte(PLAY+0x37)==1);
    psx_mod_write_byte(PLAY+0x29,1);psx_mod_write_half(0x80166C0Cu,0xC000);requested_character=0;
    CHECK(filter_for(ULTIMATE_PLUGIN)(&cpu,0x800297D8u)&&psx_mod_read_byte(PLAY+0x37)==1);
    /* The special code changes a native capsule to the Ultimate grant, with
     * the original requirement that X has not acquired armor already. */
    const uint32_t capsule=0x801D0000u;
    psx_mod_write_byte(PLAYER+2,0);psx_mod_write_byte(capsule+2,0);
    uint8_t piece=psx_mod_read_byte(0x8010D3D0u);CHECK(piece!=0);
    for(unsigned enabled=0;enabled<2;++enabled) {
        local_ultimate=enabled;psx_mod_write_byte(PLAY+0x37,0);psx_mod_write_byte(PLAYER+0xA7,piece);
        cpu=fixture_cpu();cpu.gpr[4]=capsule;entry_for(ULTIMATE_PLUGIN,0x800C62DCu,&cpu);
        CHECK(native_run(&cpu,0x800C63BCu,0x800C647Cu,0));
        /* Both cases reject this already-owned piece. The special code
         * rejects any existing armor, rather than granting it directly. */
        CHECK(cpu.gpr[5]==1);
    }
    psx_mod_write_byte(PLAYER+0xA7,0);local_ultimate=1;cpu=fixture_cpu();cpu.gpr[4]=capsule;
    entry_for(ULTIMATE_PLUGIN,0x800C62DCu,&cpu);
    CHECK(native_run(&cpu,0x800C63BCu,0x800C647Cu,0)&&cpu.gpr[5]==0);
    /* Native capsule acquisition, rather than the mod, grants all armor. */
    cpu=fixture_cpu();cpu.gpr[16]=capsule;entry_for(ULTIMATE_PLUGIN,0x800C6EDCu,&cpu);
    CHECK(!psx_mod_read_byte(PLAYER+0xA7)&&!psx_mod_read_byte(PLAYER+0xB8));
    CHECK(native_run(&cpu,0x800C7084u,0x800C7130u,0));
    CHECK(psx_mod_read_byte(PLAYER+0xA7)==0x0F&&psx_mod_read_byte(PLAYER+0xB8)==2);
    /* Nova remains gated by original armor, full energy, attack and collision
     * state. Once legitimately granted, code-enabled Nova keeps its energy. */
    cpu=fixture_cpu();CHECK(native_run(&cpu,0x800375B4u,0x8003764Cu,0x800376F4u)&&cpu.pc==0x8003764Cu);
    psx_mod_write_byte(PLAYER+0x89,2);cpu=fixture_cpu();
    CHECK(native_run(&cpu,0x800375B4u,0x8003764Cu,0x800376F4u)&&cpu.pc==0x800376F4u);
    psx_mod_write_byte(PLAYER+0x89,0);psx_mod_write_byte(PLAYER+0xA8,0x2F);cpu=fixture_cpu();
    CHECK(native_run(&cpu,0x800375B4u,0x8003764Cu,0x800376F4u)&&cpu.pc==0x800376F4u);
    for(unsigned enabled=0;enabled<2;++enabled) {
        local_ultimate=enabled;psx_mod_write_byte(PLAY+0x37,0);psx_mod_write_byte(PLAYER+0xA8,0x30);
        cpu=fixture_cpu();cpu.gpr[16]=PLAYER;entry_for(ULTIMATE_PLUGIN,0x800375B4u,&cpu);
        CHECK(native_run(&cpu,0x80037684u,0x8003769Cu,0));
        CHECK(psx_mod_read_byte(PLAYER+0xA8)==(enabled?0x30:0));
    }
    /* Ordinary capsules continue granting their authored piece only. */
    local_ultimate=0;psx_mod_write_byte(PLAY+0x37,0);psx_mod_write_byte(PLAYER+0xA7,0);psx_mod_write_byte(PLAYER+0xB8,0);
    cpu=fixture_cpu();cpu.gpr[16]=capsule;
    CHECK(native_run(&cpu,0x800C7084u,0x800C7130u,0));
    CHECK(psx_mod_read_byte(PLAYER+0xA7)==piece&&psx_mod_read_byte(PLAYER+0xB8)!=2);
    puts("original X4 character-code contracts passed");return 0;
}
int main(int argc,char **argv) {
    CHECK(!policy());
    if(argc>1) { CHECK(argc==2);CHECK(!original_contract(argv[1])); }
    puts("X4 independent character-code policy checks passed");return 0;
}
