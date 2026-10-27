#include "mmx4_x1_native_art.h"
#include <string.h>
static unsigned u16(const uint8_t *p) {return (unsigned)p[0]|(unsigned)p[1]<<8;}
static uint32_t u32(const uint8_t *p) {return u16(p)|(uint32_t)u16(p+2)<<16;}
int mmx4_x1_native_frame(const Mmx4Asset *body,const Mmx4Asset *assembly,
    const Mmx4Asset *palette,unsigned frame,uint16_t out[128*128],
    Mmx4X1NativeFrame *layout) {
    if(!body || !assembly || !palette || !out || !layout ||
       !body->data || !assembly->data || !palette->data ||
       body->size<8 || assembly->size<8 || frame>=256)return 0;
    size_t graphics=u32(body->data),table=u32(assembly->data);
    if(graphics<4 || table<4 || graphics>body->size || table>assembly->size ||
       (size_t)frame*4+4>body->size-graphics ||
       (size_t)frame*4+4>assembly->size-table)return 0;
    if((size_t)frame*4+4>(u32(body->data+graphics)&0xFFFFFu) ||
       (size_t)frame*4+4>u16(assembly->data+table+2)*4u)return 0;
    uint32_t packed=u32(body->data+graphics+frame*4);
    unsigned tiles=packed>>20;
    size_t source=graphics+(packed&0xFFFFFu);
    const uint8_t *record=assembly->data+table+frame*4;
    unsigned count=u16(record);
    size_t pieces=table+u16(record+2)*4u;
    if(!tiles || tiles>256 || source>=body->size || !count || count>256 ||
       pieces>assembly->size || count*4u>assembly->size-pieces)return 0;
    int left=128,top=128,right=-128,bottom=-128;
    for(unsigned i=0;i<count;++i) {
        const uint8_t *p=assembly->data+pieces+i*4;
        unsigned tile=p[1]+((p[0]&3u)<<8),colors=(p[0]>>2)&3u;
        if(tile>=tiles || (colors+1u)*32u>palette->size)return 0;
        int x=(int8_t)p[2],y=(int8_t)p[3];
        if(x<left)left=x;if(y<top)top=y;
        if(x+16>right)right=x+16;if(y+16>bottom)bottom=y+16;
    }
    if(right-left>128 || bottom-top>128)return 0;
    uint8_t decoded[32768];size_t written=0;
    if(!mmx4_coop_decode_sprite(body->data+source,body->size-source,
        decoded,sizeof decoded,&written) || written!=tiles*128u)return 0;
    memset(out,0,128*128*sizeof *out);
    for(unsigned i=0;i<count;++i) {
        const uint8_t *p=assembly->data+pieces+i*4;
        unsigned tile=p[1]+((p[0]&3u)<<8),row=tile/16u;
        unsigned chunk=tiles-row*16u;if(chunk>16)chunk=16;
        unsigned colors=((p[0]>>2)&3u)*32u;
        int dx=(int8_t)p[2]-left,dy=(int8_t)p[3]-top;
        for(unsigned y=0;y<16;++y)for(unsigned x=0;x<16;++x) {
            unsigned sx=(p[0]&64u)?15-x:x,sy=(p[0]&128u)?15-y:y;
            unsigned at=row*2048u+sy*chunk*8u+(tile%16u)*8u+sx/2u;
            unsigned pixel=(decoded[at]>>((sx&1u)*4u))&15u;
            uint16_t color=(uint16_t)u16(palette->data+colors+pixel*2u);
            if(color)out[(dy+(int)y)*128u+dx+x]=color;
        }
    }
    *layout=(Mmx4X1NativeFrame){left,top,(unsigned)(right-left),(unsigned)(bottom-top)};
    return 1;
}
