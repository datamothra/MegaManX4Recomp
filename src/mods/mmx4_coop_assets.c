#include "mmx4_coop_assets.h"
#include <string.h>
static uint16_t u16(const uint8_t *p) { return (uint16_t)(p[0]|p[1]<<8); }
static uint32_t u32(const uint8_t *p) { return (uint32_t)u16(p)|(uint32_t)u16(p+2)<<16; }
uint16_t mmx4_coop_palette_lighting(uint16_t color,const uint16_t amounts[3],unsigned subtract) {
    if(!color)return 0; /* Native leaves transparent palette entries alone. */
    uint16_t result=color&0x8000u;
    for(unsigned channel=0;channel<3;++channel) {
        unsigned mask=31u<<(channel*5u),value=color&mask,amount=amounts[channel];
        if(subtract&(1u<<channel))value=amount>value?0:value-amount;
        else {value+=amount;if(value>mask)value=mask;}
        result|=(uint16_t)value;
    }
    return result;
}
int mmx4_coop_character_palette_offset(uint16_t clut) {
    /* Native upload rectangle 800F1658 is (0,480,256,8), whereas encoded
     * PSX CLUT rows have a 1024-pixel stride. Only its first two rows are
     * character-owned. Armor 7843/7844 lives at 260/280, not 860/880. */
    unsigned x=(clut&63u)*16u,y=clut>>6;
    if(x>=256u || y<480u || y>=482u)return -1;
    return (int)(((y-480u)*256u+x)*2u);
}
uint16_t mmx4_coop_sprite_quad_tile(uint32_t q[10]) {
    /* 80024754/800247A8 shorten an edge when a flipped native tile would
     * need a UV of -1 (or a forward tile would need 256). At private origin
     * zero that drops a pixel from every vertically flipped first-row tile.
     * Restore the full assembly square and reflect its pixels instead: all
     * four edges then use representable, exclusive UVs 0..16. */
    unsigned u=q[3]&255u,v=(q[3]>>8)&255u;
    unsigned flip_x=u>(q[5]&255u),flip_y=v>((q[7]>>8)&255u);
    int x=(int16_t)q[2],y=(int16_t)(q[2]>>16);
    uint16_t tile=(uint16_t)((u&0xF0u)|((v&0xF0u)<<8)|flip_x|(flip_y<<1));
    for(unsigned i=0;i<4;++i) {
        q[2+i*2]=(uint16_t)(x+(i&1)*16)|((uint32_t)(uint16_t)(y+(i>>1)*16)<<16);
        q[3+i*2]=(q[3+i*2]&0xFFFF0000u)|(i&1)*16|((i>>1)*16<<8);
    }
    return tile;
}
void mmx4_coop_sprite_tile_pixels(const uint16_t pixels[256*256],uint16_t tile,
                                  uint16_t out[16*16]) {
    for(unsigned y=0;y<16;++y)for(unsigned x=0;x<16;++x) {
        unsigned sx=(tile&0xF0u)+((tile&1u)?15-x:x);
        unsigned sy=((tile>>8)&0xF0u)+((tile&2u)?15-y:y);
        out[y*16+x]=pixels[sy*256+sx];
    }
}
int mmx4_coop_sprite_atlas_tile(unsigned tiles,uint16_t tile,
                               uint16_t *key,uint16_t *uv) {
    if(!tiles || tiles>256 || !key || !uv)return 0;
    unsigned index=((tile>>12)&15u)*16u+((tile>>4)&15u);
    if(index>=tiles) {*key=8;*uv=0;return 1;}
    unsigned local=index%225u;
    *key=(uint16_t)((index/225u)*4u+(tile&3u));
    *uv=(uint16_t)((local%15u)*16u|((local/15u)*16u<<8));
    return 1;
}
int mmx4_coop_sprite_atlas_pixels(const uint16_t pixels[256*256],unsigned tiles,
                                 unsigned key,uint16_t out[240*240],
                                 unsigned *width,unsigned *height) {
    if(!pixels || !out || !width || !height || !tiles || tiles>256 || key>8)return 0;
    if(key==8) {memset(out,0,256*sizeof *out);*width=*height=16;return 1;}
    unsigned first=(key/4u)*225u,flip=key&3u;
    if(first>=tiles)return 0;
    unsigned count=tiles-first;if(count>225)count=225;
    unsigned w=(count<15?count:15)*16u,h=((count+14u)/15u)*16u;
    memset(out,0,(size_t)w*h*sizeof *out);
    for(unsigned i=0;i<count;++i) {
        unsigned source=first+i,sx=(source%16u)*16u,sy=(source/16u)*16u;
        unsigned dx=(i%15u)*16u,dy=(i/15u)*16u;
        for(unsigned y=0;y<16;++y)for(unsigned x=0;x<16;++x)
            out[(dy+y)*w+dx+x]=pixels[(sy+((flip&2u)?15u-y:y))*256u+sx+((flip&1u)?15u-x:x)];
    }
    *width=w;*height=h;return 1;
}
int mmx4_coop_arc_asset(const uint8_t *data,size_t size,unsigned member,Mmx4Asset *out) {
    if (!data || !out || size<2048 || u32(data+4)!=size) return 0;
    unsigned count=u32(data); size_t cursor=2048;
    if (count>255 || member>=count) return 0;
    Mmx4Asset found={0};
    for(unsigned i=0;i<count;++i) {
        size_t bytes=u32(data+12+i*8);
        if (cursor>size || bytes>size-cursor) return 0;
        if(i==member) found=(Mmx4Asset){data+cursor,bytes,u32(data+8+i*8)};
        cursor+=(bytes+2047)&~(size_t)2047;
    }
    if(cursor!=size) return 0;
    *out=found; return 1;
}
int mmx4_coop_decode_sprite(const uint8_t *src,size_t size,uint8_t *dst,
                            size_t capacity,size_t *written) {
    size_t in=0,out=0;
    if(written)*written=0;
    if(!src || !dst || !written)return 0;
    while(size-in>=2) {
        unsigned flags=u16(src+in); in+=2;
        for(unsigned bit=0x8000;bit;bit>>=1) {
            if(size-in<2)return 0;
            unsigned code=u16(src+in);in+=2;
            if(!(flags&bit)) {
                if(capacity-out<2)return 0;
                dst[out++]=(uint8_t)code;dst[out++]=(uint8_t)(code>>8);continue;
            }
            unsigned count=code>>11,distance=code&0x7ff;
            if(!count) { if(size-in<2)return 0;count=u16(src+in);in+=2; }
            if(!count&&!distance) { *written=out;return 1; }
            if((size_t)count*2>capacity-out || (size_t)distance*2>out)return 0;
            while(count--) {
                uint8_t lo=distance?dst[out-distance*2]:0;
                uint8_t hi=distance?dst[out-distance*2+1]:0;
                dst[out++]=lo;dst[out++]=hi;
            }
        }
    }
    return 0;
}
