/* Native-call adaptation must never leak the temporary X identity or erase
 * saved upgrade progress. The guest stub verifies the boundary in both seats;
 * actual movement/projectile behavior is qualified against the original disc. */
#include "mmx4_x1.h"
#include "mod_plugins.h"
#include "mod_runtime.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define P 0x801418C8u
#define V 0x801721C0u
#define CHECK(x) do { if(!(x)){fprintf(stderr,"line %d: %s\n",__LINE__,#x);abort();} } while(0)
static uint8_t ram[2*1024*1024],scratch[1024];
static int enabled[2],local_scope,resource_ready=1,expect_zero;
static unsigned calls;
static PSXModFunctionFilterCallback movement,shot,aerial;
static PSXModFunctionEntryCallback iris;
static uint8_t *at(uint32_t a){if(a>=0x1F800000u&&a<0x1F800400u)return scratch+a-0x1F800000u;CHECK((a&0x1FFFFFFFu)<sizeof ram);return ram+(a&0x1FFFFFFFu);}
uint8_t psx_mod_read_byte(uint32_t a){return *at(a);}
void psx_mod_write_byte(uint32_t a,uint8_t v){*at(a)=v;}
uint16_t psx_mod_read_half(uint32_t a){return psx_mod_read_byte(a)|(uint16_t)psx_mod_read_byte(a+1)<<8;}
void psx_mod_write_half(uint32_t a,uint16_t v){psx_mod_write_byte(a,v);psx_mod_write_byte(a+1,v>>8);}
uint32_t psx_mod_read_word(uint32_t a){return psx_mod_read_half(a)|(uint32_t)psx_mod_read_half(a+2)<<16;}
void psx_mod_write_word(uint32_t a,uint32_t v){psx_mod_write_half(a,v);psx_mod_write_half(a+2,v>>16);}
int mod_runtime_snapshot_package_active(const char *id){return enabled[strstr(id,"zero")!=NULL];}
int psx_mod_local_view_scope(void){return local_scope;}
void psx_mod_counter_add(const char *name,uint32_t n){(void)name;(void)n;}
int mmx4_x1_x_resources(uint32_t out[4]){for(unsigned i=0;i<4;++i)out[i]=0x9F001000u+i*0x1000u;return resource_ready;}
int psx_mod_register_function_filter_plugin(const char *id,uint32_t a,PSXModFunctionFilterCallback cb){(void)id;if(a==0x800312B4u)movement=cb;if(a==0x800922D8u)shot=cb;if(a==0x8003484Cu)aerial=cb;return 1;}
int psx_mod_register_function_entry_plugin(const char *id,uint32_t a,PSXModFunctionEntryCallback cb){(void)id;(void)a;(void)cb;return 1;}
int psx_mod_register_instruction_plugin(const char *id,uint32_t a,uint32_t word,PSXModFunctionEntryCallback cb){(void)id;CHECK(a==0x8002DE84u&&word==0xA0820063u);iris=cb;return 1;}
uint32_t psx_mod_call_guest(CPUState *cpu,uint32_t a,uint32_t ret,uint32_t a0,uint32_t a1,uint32_t a2,uint32_t a3){
    (void)ret;(void)a0;(void)a1;(void)a2;(void)a3;++calls;
    CHECK(!mmx4_x1_native_ready());CHECK(mmx4_x1_buster_context()==expect_zero);
    CHECK(!psx_mod_read_byte(P+2));CHECK(!psx_mod_read_byte(V+0x47));CHECK(!psx_mod_read_byte(V+0x48));CHECK(!psx_mod_read_byte(V+0x37));
    CHECK(!psx_mod_read_byte(P+0xA7));CHECK(!psx_mod_read_byte(P+0xB8));
    CHECK(!movement(cpu,0x800312B4u));
    if(expect_zero){CHECK(!psx_mod_read_byte(V+0x43));CHECK(!psx_mod_read_byte(V+0x60));CHECK(psx_mod_read_word(P+0x30)==0x80119DF0u);CHECK(psx_mod_read_word(0x1F800014u)==0x9F001000u);}
    else CHECK(psx_mod_read_byte(V+0x60)==4);
    if(a==0x800312B4u)psx_mod_write_word(P+12,psx_mod_read_word(P+12)+0x30000u);
    psx_mod_write_byte(P+0x91,77);return 123;
}
static void init(unsigned character,unsigned action){
    memset(ram,0,sizeof ram);memset(scratch,0,sizeof scratch);calls=0;expect_zero=character;enabled[0]=enabled[1]=1;local_scope=0;resource_ready=1;
    psx_mod_write_byte(P+2,character);psx_mod_write_byte(P+5,action);psx_mod_write_word(P+12,0x1000000u);psx_mod_write_word(P+28,0x2200000u);psx_mod_write_word(P+0x30,0x12345678u);
    psx_mod_write_byte(V+0x43,1);psx_mod_write_byte(V+0x60,4);psx_mod_write_byte(V+0x47,15);psx_mod_write_byte(V+0x48,2);psx_mod_write_byte(V+0x37,3);
    psx_mod_write_byte(P+0xA7,15);psx_mod_write_byte(P+0xB8,2);psx_mod_write_word(0x1F800014u,0x11223344u);mmx4_x1_native_reset();
}
int main(void){
    CPUState cpu;memset(&cpu,0,sizeof cpu);cpu.gpr[4]=P;
    CHECK(movement&&shot&&aerial);
    for(unsigned character=0;character<2;++character)for(unsigned action=2;action<=15;++action){
        init(character,action);CHECK(movement(&cpu,0x800312B4u));CHECK(calls==1&&cpu.gpr[2]==123);CHECK(psx_mod_read_byte(P+2)==character);
        CHECK(psx_mod_read_byte(V+0x43)==1&&psx_mod_read_byte(V+0x60)==4);CHECK(psx_mod_read_byte(V+0x47)==15&&psx_mod_read_byte(V+0x48)==2&&psx_mod_read_byte(V+0x37)==3);
        CHECK(psx_mod_read_word(P+12)==0x1030000u&&psx_mod_read_word(P+28)==0x2200000u);CHECK(psx_mod_read_word(P+0x30)==0x12345678u);CHECK(psx_mod_read_word(0x1F800014u)==0x11223344u);
        CHECK(psx_mod_read_byte(P+0x91)==77);CHECK(mmx4_x1_native_ready()&&!mmx4_x1_buster_context());CHECK(aerial(&cpu,0x8003484Cu)&&!cpu.gpr[2]);
    }
    for(unsigned action=0;action<35;++action)if(action<2||action>15){init(1,action);CHECK(!movement(&cpu,0x800312B4u)&&!calls);}
    init(1,2);local_scope=1;CHECK(!movement(&cpu,0x800312B4u)&&!calls);
    init(1,2);enabled[1]=0;CHECK(!movement(&cpu,0x800312B4u)&&!calls);CHECK(!aerial(&cpu,0x8003484Cu));
    init(1,2);resource_ready=0;CHECK(movement(&cpu,0x800312B4u)&&!calls&&!cpu.gpr[2]&&mmx4_x1_native_ready());
    init(1,2);psx_mod_write_byte(P+0xC5,255);CHECK(!movement(&cpu,0x800312B4u)&&!calls);
    init(1,2);cpu.gpr[4]=0x801406F8u;CHECK(shot(&cpu,0x800922D8u)&&calls==1&&psx_mod_read_byte(P+2)==1);
    init(1,2);CHECK(iris);psx_mod_write_byte(V,6);psx_mod_write_byte(V+12,11);
    psx_mod_write_byte(0x8013BED0u,1);psx_mod_write_byte(0x8013BED1u,66);
    for(unsigned core=0;core<2;++core)for(unsigned kind=0;kind<3;++kind){
        unsigned types[3]={0,9,18},type=types[kind],entry=kind?24:32;
        uint32_t table=core?0x80107E84u:0x80107DFCu;
        psx_mod_write_byte(0x8013BED2u,core);psx_mod_write_byte(table+entry*2,7);
        cpu.gpr[4]=0x8013BED0u;cpu.gpr[6]=type;cpu.gpr[7]=table;cpu.gpr[2]=255;
        iris(&cpu,0x8002DE84u);CHECK(cpu.gpr[2]==7&&cpu.gpr[6]==type&&cpu.gpr[7]+type*2==table+entry*2);
    }
    cpu.gpr[7]=0x80107E84u;cpu.gpr[6]=24;cpu.gpr[2]=255;iris(&cpu,0x8002DE84u);CHECK(cpu.gpr[2]==255);
    cpu.gpr[6]=0;cpu.gpr[7]=0x80107F0Cu;iris(&cpu,0x8002DE84u);CHECK(cpu.gpr[2]==255);
    cpu.gpr[7]=0x80107E84u;enabled[1]=0;iris(&cpu,0x8002DE84u);CHECK(cpu.gpr[2]==255);
    puts("X1 scoped capability contract passed");return 0;
}
