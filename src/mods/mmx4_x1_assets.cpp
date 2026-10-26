// Supplied fan sheets remain unchanged. Atlas rectangles feed immutable PSX
// texture banks; logical character/story state stays separate from the art.
#include "mmx4_x1.h"
extern "C" {
#include "mmx4_coop_assets.h"
#include "mmx4_coop_internal.h"
}
#include "mod_plugins.h"
#include "mod_runtime.h"
#include "mod_snapshot.h"
#include "texture_image_decode.h"
#include <array>
#include <vector>
#include <cstring>
#include <cstdio>
#include <stdexcept>

namespace {
constexpr uint32_t Player=0x801418C8u,Play=0x801721C0u,Scratch=0x1F800000u;
constexpr uint16_t FirstBank=0x2000;
constexpr uint32_t ArenaBytes=0x10000;
struct X1Frame {unsigned character,x,y,w,h;};
struct X1Sequence {unsigned character;const char *name;unsigned first,count;};
#include "mmx4_x1_frame_data.h"
constexpr unsigned FrameCount=sizeof X1Frames/sizeof X1Frames[0];
static_assert(FrameCount*2<=0x4000,"X1 banks must not overlap co-op texture banks");
std::array<DecodedTextureImage,2> images;
std::array<std::vector<uint16_t>,FrameCount*2> pixels;
std::array<bool,FrameCount*2> defined{};
std::vector<uint8_t> xArchive,zeroArchive;
uint32_t xGuest=0,arena=0;
unsigned drawing=0;
struct Cursor {uint32_t frame=0,used=0;};
std::array<Cursor,2> cursors,localCursors;

uint32_t word(const uint8_t *p) {
    return uint32_t(p[0])|uint32_t(p[1])<<8|uint32_t(p[2])<<16|uint32_t(p[3])<<24;
}
void put(uint8_t *p,uint32_t value) {
    for(unsigned i=0;i<4;++i)p[i]=uint8_t(value>>(8*i));
}
unsigned sequence(unsigned character,const char *name,unsigned index) {
    for(const auto &s:X1Sequences)
        if(s.character==character && !std::strcmp(s.name,name))return s.first+index%s.count;
    for(const auto &s:X1Sequences)if(s.character==character)return s.first;
    return 0;
}
void loadImage(unsigned character,const char *resource) {
    if(!images[character].rgba.empty())return;
    const uint8_t *data=nullptr;uint64_t size=0;std::string error;
    if(!psx_mod_current_resource_bytes(resource,&data,&size) || size>2*1024*1024 ||
       !texture_image_decode(data,size,16*1024*1024,images[character],error))
        throw std::runtime_error("X1 character sprite resource: "+error);
    auto &im=images[character];
    if(im.width!=(character?1023u:1200u) || im.height!=(character?567u:1700u))
        throw std::runtime_error("X1 character sprite dimensions do not match reviewed atlas");
}
void copyGuest(uint32_t address,const uint8_t *data,uint32_t count) {
    for(uint32_t i=0;i<count;++i)psx_mod_write_byte(address+i,data[i]);
}
void installXResources() {
    if(!xGuest || xArchive.empty())return;
    Mmx4Asset body{},assembly{},colors{};
    if(!mmx4_coop_arc_asset(xArchive.data(),xArchive.size(),2,&body) || body.type!=2 || !body.size || body.size>0x34000 ||
       !mmx4_coop_arc_asset(xArchive.data(),xArchive.size(),9,&assembly) || assembly.type!=3 || !assembly.size || assembly.size>0xC000 ||
       !mmx4_coop_arc_asset(xArchive.data(),xArchive.size(),0,&colors) || colors.type!=9 || colors.size<32 || colors.size>0x1000)
        throw std::runtime_error("Original X buster resource layout rejected");
    copyGuest(xGuest,body.data,body.size);copyGuest(xGuest+0x34000,assembly.data,assembly.size);
    copyGuest(xGuest+0x40000,colors.data,colors.size);
    copyGuest(xGuest+0x41000,colors.data,32);
}
void prepareNativeX() {
    if(mod_runtime_snapshot_package_active("mmx4.coop"))return;
    uint32_t size=0;
    if(!psx_mod_read_disc_file("ARC/PL00_U.ARC",nullptr,0,&size) || size>2*1024*1024)
        throw std::runtime_error("Cannot read original X buster resources");
    xArchive.resize(size);
    if(!psx_mod_read_disc_file("ARC/PL00_U.ARC",xArchive.data(),size,&size))
        throw std::runtime_error("Cannot read original X buster archive");
    xGuest=psx_mod_alloc_guest_memory(0x42000,16);
    if(!xGuest)throw std::runtime_error("No space for original buster resources");
    installXResources();
    /* The buster keeps X's original effects while character voices remain
     * Zero's. Reuse the qualified private VAB/sample residency path. */
    if(!mmx4_coop_audio_activate() ||
       !mmx4_coop_audio_prepare(0,xArchive.data(),uint32_t(xArchive.size()),0))
        throw std::runtime_error("Cannot prepare original buster sounds");
    size=0;
    if(!psx_mod_read_disc_file("ARC/PL01_U.ARC",nullptr,0,&size) || size>2*1024*1024)
        throw std::runtime_error("Cannot read original Zero voice resources");
    zeroArchive.resize(size);
    if(!psx_mod_read_disc_file("ARC/PL01_U.ARC",zeroArchive.data(),size,&size) ||
       !mmx4_coop_audio_prepare(1,zeroArchive.data(),size,0))
        throw std::runtime_error("Cannot prepare original Zero voice resources");
}
void ensureArena() {
    if(!arena)arena=psx_mod_alloc_texture_packet_memory(4*ArenaBytes,16);
    if(!arena)throw std::runtime_error("No X1 sprite packet arena");
}
void restore() {
    defined.fill(false);localCursors={};drawing=0;mmx4_x1_native_reset();
    installXResources();
    if(!mod_runtime_snapshot_package_active("mmx4.coop"))
        psx_mod_set_texture_bank_resolver(mmx4_x1_resolve_texture);
}
void reset() {
    images={};pixels={};defined.fill(false);xArchive.clear();zeroArchive.clear();xGuest=arena=0;
    if(!mod_runtime_snapshot_package_active("mmx4.coop"))mmx4_coop_audio_reset();
    cursors={};localCursors={};drawing=0;mmx4_x1_native_reset();
}
void activateX() {
    loadImage(0,"sprites");ensureArena();restore();
    psx_mod_counter_add("mmx4.x1.x-activated",1);
}
void activateZero() {
    loadImage(1,"sprites");loadImage(0,"projectiles");ensureArena();prepareNativeX();restore();
    psx_mod_counter_add("mmx4.x1.zero-activated",1);
}
bool trailActor(uint32_t actor) {
    return actor>=0x80141AB0u && actor<0x80141BD0u && (actor-0x80141AB0u)%0x60u==0;
}
bool bodyActor(uint32_t actor) {
    return actor==Player || actor==0x80175D58u || trailActor(actor);
}
bool shotActor(uint32_t actor) {
    if(actor<0x801406F8u || actor>=0x801410B8u || (actor-0x801406F8u)%0x9Cu)return false;
    unsigned type=psx_mod_read_byte(actor+1);
    return type==0 || type==9 || type==18;
}
bool glowActor(uint32_t actor) {
    return actor==0x8013E470u || actor==0x8013E4C0u;
}
unsigned pose(uint32_t actor,unsigned character) {
    unsigned animation=psx_mod_read_byte(actor+0x45)&0x3Fu;
    if(shotActor(actor)) {
        unsigned type=psx_mod_read_byte(actor+1);
        return sequence(0,character?"zero_shot":"shot",type==18?2:type==9?1:0);
    }
    if(trailActor(actor))return sequence(character,"dash",animation);
    if(actor==0x80175D58u)return sequence(character,"idle",animation);
    unsigned action=psx_mod_read_byte(actor+5);
    bool firing=psx_mod_read_byte(actor+0x91) || psx_mod_read_byte(actor+0x92);
    if(psx_mod_read_byte(actor+4)==2)return sequence(character,"hurt",animation);
    if(action<2 || action==20)return sequence(character,"arrive",animation);
    if(action==3 || action==4)return sequence(character,firing?"run_fire":"run",animation);
    if(action==6 || action==7 || action==8) {
        /* X4 restarts its animation phase at each ascent/descent/landing
         * controller. A whole-sheet modulo restarts takeoff art in midair
         * and again on the floor. Keep those native controller phases in
         * their corresponding portions of the supplied animation. */
        const char *name=firing?"jump_fire":"jump";
        if(action==6)return sequence(character,name,animation<4?animation:3);
        if(action==7) {
            unsigned phase=animation<4?animation:3;
            return sequence(character,name,4u+(character?phase*2u:phase));
        }
        /* Zero's sheet has no labelled landing cycle; use the appropriate
         * grounded pose rather than drawing a takeoff pose on the floor. */
        if(character)return sequence(character,firing?"fire":"idle",0);
        unsigned last=firing?3u:2u;
        return sequence(character,name,8u+(animation<last?animation:last));
    }
    if(action==10 || action==13)return sequence(character,firing?"jump_fire":"jump",animation);
    if(action==9 || action==11)return sequence(character,"wall",animation);
    if(action==14 || action==15)return sequence(character,"ladder",animation);
    if(action==12)return sequence(character,firing?"dash_fire":"dash",animation);
    if(firing)return sequence(character,"fire",animation);
    return sequence(character,"idle",animation);
}
void triangle(uint32_t at,uint32_t next,int x,int y,unsigned w,unsigned h,
              unsigned a,unsigned b,unsigned c,bool mirror,bool flipY,uint16_t bank,bool ghost,uint32_t tint) {
    const unsigned vertex[3]={a,b,c};
    psx_mod_write_word(at,0x09000000u|(next&0xFFFFFFu));
    for(unsigned i=0;i<3;++i) {
        unsigned v=vertex[i];
        uint32_t rgb=ghost?0x00606060u:tint;
        uint32_t color=i==0?(ghost?0x36000000u:0x34000000u)|rgb:rgb|
            (uint32_t(i==1?bank&255u:bank>>8)<<24);
        unsigned u=(v&1u)?w:0;if(mirror)u=w-u;
        unsigned ty=(v>>1)?h:0;if(flipY)ty=h-ty;
        uint32_t uv=u|(ty<<8);
        if(i==1)uv|=0x100u<<16;
        psx_mod_write_word(at+4+i*12,color);
        psx_mod_write_word(at+8+i*12,uint16_t(x+(v&1u)*w)|uint32_t(uint16_t(y+(v>>1)*h))<<16);
        psx_mod_write_word(at+12+i*12,uv);
    }
}
int autoRender(CPUState *cpu,uint32_t address) {
    (void)address;
    if(!mmx4_x1_render(cpu,cpu->gpr[4],psx_mod_read_byte(Player+2)))return 0;
    cpu->gpr[2]=0;return 1;
}
bool soloAudio() {return mmx4_x1_enabled(1) && !mod_runtime_snapshot_package_active("mmx4.coop");}
uint32_t snapshotBytes() {
    Mmx4SnapshotIO io{};io.ok=1;io.mode=MMX4_SNAPSHOT_COUNT;io.pos=16;
    if(soloAudio())mmx4_coop_audio_snapshot(&io);
    return io.ok?io.pos:0;
}
int snapshotWrite(uint8_t *out,uint32_t len) {
    if(!out || len!=snapshotBytes())return 0;
    for(unsigned i=0;i<2;++i) {put(out+i*8,cursors[i].frame);put(out+i*8+4,cursors[i].used);}
    Mmx4SnapshotIO io{};io.ok=1;io.mode=MMX4_SNAPSHOT_WRITE;io.out=out;io.len=len;io.pos=16;
    if(soloAudio())mmx4_coop_audio_snapshot(&io);
    return io.ok && io.pos==len;
}
int snapshotValidate(const uint8_t *data,uint32_t len) {
    if(!data || len!=snapshotBytes() || word(data+4)>ArenaBytes/80 || word(data+12)>ArenaBytes/80)return 0;
    Mmx4SnapshotIO io{};io.ok=1;io.mode=MMX4_SNAPSHOT_VALIDATE;io.in=data;io.len=len;io.pos=16;
    if(soloAudio())mmx4_coop_audio_snapshot(&io);
    return io.ok && io.pos==len;
}
void snapshotRead(const uint8_t *data,uint32_t len) {
    for(unsigned i=0;i<2;++i) {cursors[i].frame=word(data+i*8);cursors[i].used=word(data+i*8+4);}
    Mmx4SnapshotIO io{};io.ok=1;io.mode=MMX4_SNAPSHOT_READ;io.in=data;io.len=len;io.pos=16;
    if(soloAudio())mmx4_coop_audio_snapshot(&io);
}
int snapshotReady() {return !drawing && mmx4_x1_native_ready() && (!soloAudio() || mmx4_coop_audio_snapshot_ready());}
}

extern "C" int mmx4_x1_x_resources(uint32_t out[4]) {
    if(mod_runtime_snapshot_package_active("mmx4.coop"))return mmx4_coop_x1_resources(out);
    if(!xGuest)return 0;
    out[0]=xGuest;out[1]=xGuest+0x34000;out[2]=xGuest+0x40000;out[3]=xGuest+0x41000;
    return 1;
}
extern "C" int mmx4_x1_resolve_texture(uint16_t id) {
    if(id<FirstBank || id-FirstBank>=FrameCount*2)return 0;
    unsigned index=id-FirstBank;bool ghost=index>=FrameCount;
    const auto &frame=X1Frames[index%FrameCount];auto &im=images[frame.character];
    if(im.rgba.empty())return 0;
    auto &decoded=pixels[index];
    if(decoded.empty()) {
        decoded.assign(128*128,0);
        for(unsigned y=0;y<frame.h;++y)for(unsigned x=0;x<frame.w;++x) {
            const uint8_t *p=&im.rgba[((frame.y+y)*im.width+frame.x+x)*4];
            if(!p[3] || (frame.character==1 && p[0]==27 && p[1]==89 && p[2]==153))continue;
            uint16_t color=uint16_t((p[0]>>3)|((p[1]>>3)<<5)|((p[2]>>3)<<10));
            decoded[y*128+x]=(color?color:1)|(ghost?0x8000u:0u);
        }
    }
    if(!psx_mod_define_texture_bank(id,128,128,decoded.data()))return 0;
    defined[index]=true;return 1;
}
extern "C" int mmx4_x1_render(CPUState *cpu,uint32_t actor,unsigned character) {
    (void)cpu;
    if(character>1 || !mmx4_x1_enabled(character) || !arena ||
       (!bodyActor(actor) && !shotActor(actor) && !glowActor(actor)))return 0;
    if(!psx_mod_texture_banks_supported())return 0;
    /* Those actors are the native charge indicators, not projectiles. The
     * supplied sheet has no charge aura: its green bursts are shot impacts.
     * Indicate charging with a body pulse below instead of pasting an impact
     * animation onto either hero. Exact SNES palette timing remains separate. */
    if(glowActor(actor))return 1;
    if(!psx_mod_read_byte(actor) || !psx_mod_read_byte(actor+3))return 1;
    drawing=1;unsigned index=pose(actor,character);const auto &frame=X1Frames[index];
    bool ghost=trailActor(actor);unsigned bankIndex=index+(ghost?FrameCount:0);
    uint16_t bank=FirstBank+uint16_t(bankIndex);
    if(!defined[bankIndex] && !mmx4_x1_resolve_texture(bank)) {drawing=0;return 0;}
    unsigned buffer=psx_mod_read_word(Scratch)&1u;
    bool local=psx_mod_local_view_scope()!=0;
    auto &cursor=(local?localCursors:cursors)[buffer];
    uint32_t tick=psx_mod_read_word(0x80141BD8u);
    if(cursor.frame!=tick) {cursor.frame=tick;cursor.used=0;}
    if(cursor.used>=ArenaBytes/80) {drawing=0;return 1;}
    uint32_t at=arena+(buffer+(local?2u:0u))*ArenaBytes+cursor.used++*80;
    unsigned priority=psx_mod_read_byte(actor+0x16);
    uint32_t tail=0x8013BC40u+buffer*128+(priority>>4)*32+(priority&15u)*4;
    uint32_t previous=psx_mod_read_word(tail);
    if((previous&0xFFFFFFu)==0xFFFFFFu || !previous) {drawing=0;return 1;}
    uint32_t next=psx_mod_read_word(previous)&0xFFFFFFu;
    int x=int16_t(psx_mod_read_half(actor+10)),y=int16_t(psx_mod_read_half(actor+14));
    unsigned layer=psx_mod_read_byte(actor+0x14);
    if(layer<3) {
        x-=int16_t(psx_mod_read_half(0x801419B0u+layer*0x54u+10));
        y-=int16_t(psx_mod_read_half(0x801419B0u+layer*0x54u+14));
    }
    bool body=bodyActor(actor);x-=int(frame.w)/2;
    bool flipY=(psx_mod_read_byte(actor+0x15)&0x20u)!=0;
    y-=body?(flipY?(character?22:21):int(frame.h)-(character?22:21)):int(frame.h)/2;
    int margin=psx_mod_widescreen_x_margin();
    if(x+int(frame.w)<-margin-128 || x>320+margin+128 || y+int(frame.h)<-128 || y>368) {drawing=0;return 1;}
    bool mirror=(psx_mod_read_byte(actor+0x15)&0x40u)==0;
    uint32_t tint=0x00808080u;
    unsigned charge=psx_mod_read_byte(Player+0x94);
    if(body && !ghost && charge && (tick&4u)) {
        tint=charge>=18?0x00A0F0F0u:0x00F0D0A0u;
        psx_mod_counter_add("mmx4.x1.charge-body-pulses",1);
    }
    triangle(at,at+40,x,y,frame.w,frame.h,0,1,2,mirror,flipY,bank,ghost,tint);
    triangle(at+40,next,x,y,frame.w,frame.h,2,1,3,mirror,flipY,bank,ghost,tint);
    psx_mod_write_word(previous,(psx_mod_read_word(previous)&0xFF000000u)|(at&0xFFFFFFu));
    psx_mod_write_word(tail,at+40);
    psx_mod_tag_world_primitive(at,layer<3);psx_mod_tag_world_primitive(at+40,layer<3);
    drawing=0;psx_mod_counter_add("mmx4.x1.replacement-draws",1);
    return 1;
}

PSX_MOD_CONSTRUCTOR(mmx4_register_x1_assets) {
    const PSXModSnapshotProvider provider={1,snapshotBytes,snapshotWrite,snapshotValidate,snapshotRead,snapshotReady};
    const char *plugins[]={"mmx4.x1_x","mmx4.x1_zero"};
    const char *packages[]={"mmx4.character.x1-x","mmx4.character.x1-zero"};
    for(unsigned i=0;i<2;++i) {
        psx_mod_register_activation_plugin(plugins[i],i?activateZero:activateX);
        psx_mod_register_session_reset_plugin(plugins[i],reset);
        psx_mod_register_savestate_plugin(plugins[i],restore);
        psx_mod_register_function_filter_plugin(plugins[i],0x80024334u,autoRender);
        psx_mod_register_snapshot_provider(packages[i],&provider);
    }
}
