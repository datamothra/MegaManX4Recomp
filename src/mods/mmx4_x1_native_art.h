#ifndef MMX4_X1_NATIVE_ART_H
#define MMX4_X1_NATIVE_ART_H
#include "mmx4_coop_assets.h"
typedef struct {
    int left,top;
    unsigned width,height;
} Mmx4X1NativeFrame;
/* Original ARC pixels/assembly only, no guest calls or movement changes.
 * Output has a fixed128px stride; the signed origin retains native feet. */
int mmx4_x1_native_frame(const Mmx4Asset *body,const Mmx4Asset *assembly,
    const Mmx4Asset *palette,unsigned frame,uint16_t out[128*128],
    Mmx4X1NativeFrame *layout);
#endif
