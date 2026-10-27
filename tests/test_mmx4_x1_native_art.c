#include "mmx4_x1_native_art.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define CHECK(c) do {if(!(c)){fprintf(stderr,"line%d: %s\n",__LINE__,#c);exit(1);}}while(0)
static void half(uint8_t *p,unsigned x){p[0]=(uint8_t)x;p[1]=(uint8_t)(x>>8);}
static void word(uint8_t *p,unsigned x){half(p,x);half(p+2,x>>16);}
int main(void) {
    uint8_t body[512]={0},assembly[16]={0},palette[128]={0},raw[256];
    uint16_t pixels[128*128];Mmx4X1NativeFrame bounds={0};
    word(body,8);word(body+8,(2u<<20)|4u);
    for(unsigned y=0;y<16;++y)for(unsigned x=0;x<32;++x) {
        unsigned color=x<16?(x<8?1u:2u):(x==16?0u:y<8?1u:2u);
        if(!(x&1u))raw[y*16+x/2]=(uint8_t)color;
        else raw[y*16+x/2]|=(uint8_t)(color<<4);
    }
    unsigned cursor=12;
    for(unsigned i=0;i<8;++i) {half(body+cursor,0);cursor+=2;memcpy(body+cursor,raw+i*32,32);cursor+=32;}
    half(body+cursor,0x8000);half(body+cursor+2,0);half(body+cursor+4,0);cursor+=6;
    word(assembly,4);half(assembly+4,2);half(assembly+6,1);
    assembly[8]=0;assembly[9]=0;assembly[10]=(uint8_t)-10;assembly[11]=(uint8_t)-20;
    assembly[12]=0xC4;assembly[13]=1;assembly[14]=2;assembly[15]=(uint8_t)-16;
    half(palette+2,0x1234);half(palette+4,0x2345);
    half(palette+32+2,0x3456);half(palette+32+4,0xC567);
    Mmx4Asset b={body,cursor,2},a={assembly,sizeof assembly,3},p={palette,sizeof palette,9};
    CHECK(mmx4_x1_native_frame(&b,&a,&p,0,pixels,&bounds));
    CHECK(bounds.left==-10 && bounds.top==-20 && bounds.width==28 && bounds.height==20);
    CHECK(pixels[0]==0x1234 && pixels[8]==0x2345);
    CHECK(pixels[4*128+12]==0xC567 && pixels[19*128+12]==0x3456);
    CHECK(pixels[4*128+27]==0 && pixels[4*128+11]==0x2345);
    CHECK(pixels[127*128+127]==0);
    CHECK(!mmx4_x1_native_frame(&b,&a,&p,1,pixels,&bounds));
    CHECK(!mmx4_x1_native_frame(&b,&a,&p,256,pixels,&bounds));
    CHECK(!mmx4_x1_native_frame(NULL,&a,&p,0,pixels,&bounds));
    CHECK(!mmx4_x1_native_frame(&b,&a,&p,0,NULL,&bounds));
    p.size=32;CHECK(!mmx4_x1_native_frame(&b,&a,&p,0,pixels,&bounds));p.size=sizeof palette;
    assembly[13]=2;CHECK(!mmx4_x1_native_frame(&b,&a,&p,0,pixels,&bounds));assembly[13]=1;
    half(assembly+6,0xFFFF);CHECK(!mmx4_x1_native_frame(&b,&a,&p,0,pixels,&bounds));half(assembly+6,1);
    b.size=cursor-2;CHECK(!mmx4_x1_native_frame(&b,&a,&p,0,pixels,&bounds));b.size=cursor;
    assembly[14]=127;CHECK(!mmx4_x1_native_frame(&b,&a,&p,0,pixels,&bounds));
    puts("Native Zero frame pixels, palette, reflections, origin and bounds passed");
    return 0;
}
