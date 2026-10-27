/* Real-GL equivalence to the former independent16px sprite banks. */
#define main render_thread_reference_main
#define gr_wide_set_target atlas_wide_target
#include "test_gl_render_thread.c"
#undef gr_wide_set_target
#undef main
void gr_wide_set_target(int base);
static unsigned atlas_frame;
static int atlas_latch_background;
void atlas_wide_target(int base) {
    /* A batch-tier comparison needs the renderer's full-composite policy
     * installed before drawing (wide_fast_center_valid's caller contract).
     * The shared worker fixture deliberately changes it halfway through a
     * frame to stress state recording. Keep that original stream separately
     * for the within-tier worker comparison in test_mmx4_gl_tiers.py. */
    if(atlas_latch_background)g_bg_full=(int)(atlas_frame++&1u);
    gr_wide_set_target(base);
}
#define u16 mmx4_atlas_u16
#define u32 mmx4_atlas_u32
#include "../src/mods/mmx4_coop_assets.c"
#undef u16
#undef u32
int g_psx_render_pass_active;

static uint16_t source_pixels[256*256],atlas_pixels[240*240],part_pixels[256];
static uint16_t native_ref[320*240],native_out[320*240];
static unsigned atlas_w[9],atlas_h[9];

static void draw_cells(unsigned tiles,unsigned flip,int packed) {
    check(gl_renderer_select_texture_bank(0),"clear selected bank");
    gr_set_draw_area(0,0,319,239);gr_set_draw_offset(0,0);
    mask_bits(0,0);gr_set_semi_transparency(0,0);
    gr_fill_rect(0,0,320,240,0x4210);
    for(unsigned i=0;i<256;++i) {
        uint16_t tile=(uint16_t)((i%16)*16|((i/16)*16<<8)|flip),group,uv;
        check(mmx4_coop_sprite_atlas_tile(tiles,tile,&group,&uv),"atlas cell");
        check(gl_renderer_select_texture_bank((uint16_t)(packed?2000+group:1000+i)),"select sprite pixels");
        int x=(int)(i%20)*16,y=(int)(i/20)*16,u=packed?(uv&255):0,v=packed?(uv>>8):0;
        if(i>=224) {x=64+(int)(i%8)*4;y=80+(int)((i-224)/8)*4;}
        mask_bits(i%17==0,i%19==0);
        int mode=(int)(i%5)-1;
        gr_set_semi_transparency(mode>=0,mode>=0?mode:0);
        uint16_t page=(uint16_t)(0x100|((mode>=0?mode:0)<<5));
        gr_draw_shaded_textured_triangle(x,y,u,v,0x808080,x+16,y,u+16,v,0x808080,
            x,y+16,u,v+16,0x808080,0,0,page,1);
        gr_draw_shaded_textured_triangle(x,y+16,u,v+16,0x808080,x+16,y,u+16,v,0x808080,
            x+16,y+16,u+16,v+16,0x808080,0,0,page,1);
    }
    check(gl_renderer_select_texture_bank(0),"release selected bank");
    gl_renderer_render_thread_frame_boundary();
}

int main(int argc,char **argv) {
    /* Reuse the shared upload/readback/mask/render-to-texture stream for
     * cross-tier checks as well as the title's immutable-bank stream. */
    if(argc>1) {
        atlas_latch_background=argc>5 && !strcmp(argv[5],"latched");
        return render_thread_reference_main(argc,argv);
    }
    if(SDL_Init(SDL_INIT_VIDEO)!=0)return 77;
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_MAJOR_VERSION,3);
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_MINOR_VERSION,3);
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_PROFILE_MASK,SDL_GL_CONTEXT_PROFILE_CORE);
#if defined(__APPLE__)
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_FLAGS,SDL_GL_CONTEXT_FORWARD_COMPATIBLE_FLAG);
#endif
    SDL_Window *win=SDL_CreateWindow("Sprite atlas hidden test",0,0,320,240,SDL_WINDOW_OPENGL|SDL_WINDOW_HIDDEN);
    if(!win)return 77;
    /* Four times native fits the GL3.3 minimum4096px texture limit. The
     * runtime clamps larger requested presets on hosts with that limit. */
    gr_set_backend(GR_BACKEND_OPENGL);gr_init(vram);gr_set_scale(4);
    gl_renderer_set_dynamic_resolution(1);gl_renderer_set_swap_interval(0);
    if(!gl_renderer_init_context(win))return 77;
    const int capacity=320*240*16;
    uint32_t *hires_ref=malloc((size_t)capacity*4),*hires_out=malloc((size_t)capacity*4);
    if(!hires_ref || !hires_out)return 2;
    const unsigned counts[]={1,16,225,226,256};const int scales[]={1,4};
    uint64_t digest=0xcbf29ce484222325ull;
    for(int batching=0;batching<2;++batching) {
      psx_mod_set_texture_bank_batching(batching);
      for(int threaded=0;threaded<2;++threaded) {
        if(threaded)check(gl_renderer_render_thread_start(2)==1,"render worker starts");
        for(unsigned si=0;si<2;++si) {
            int scale=scales[si];check(gl_renderer_step_internal_scale_now(scale),"internal scale changes");
            for(unsigned ci=0;ci<sizeof counts/sizeof counts[0];++ci) {
                unsigned tiles=counts[ci];memset(source_pixels,0,sizeof source_pixels);
                for(unsigned i=0;i<tiles;++i)for(unsigned y=0;y<16;++y)for(unsigned x=0;x<16;++x)
                    source_pixels[((i/16)*16+y)*256+(i%16)*16+x]=
                        (uint16_t)((i*257+x+y*17)^((x+y)&1?0x8000:0));
                psx_mod_forget_texture_bank_range(2000,9);
                for(unsigned group=0;group<9;++group)if(group==8 || group/4*225<tiles) {
                    check(mmx4_coop_sprite_atlas_pixels(source_pixels,tiles,group,atlas_pixels,&atlas_w[group],&atlas_h[group]),"pack atlas");
                    check(psx_mod_define_texture_bank((uint16_t)(2000+group),atlas_w[group],atlas_h[group],atlas_pixels),"define atlas");
                }
                for(unsigned flip=0;flip<4;++flip) {
                    psx_mod_forget_texture_bank_range(1000,256);
                    for(unsigned i=0;i<256;++i) {
                        uint16_t tile=(uint16_t)((i%16)*16|((i/16)*16<<8)|flip);
                        mmx4_coop_sprite_tile_pixels(source_pixels,tile,part_pixels);
                        check(psx_mod_define_texture_bank((uint16_t)(1000+i),16,16,part_pixels),"define original tile");
                    }
                    draw_cells(tiles,flip,0);
                    gr_vram_transfer_out(0,0,320,240,native_ref);
                    int rw=0,rh=0,ow=0,oh=0;
                    int rn=gl_renderer_read_display_hires(0,0,320,240,hires_ref,capacity,&rw,&rh);
                    draw_cells(tiles,flip,1);
                    gr_vram_transfer_out(0,0,320,240,native_out);
                    int on=gl_renderer_read_display_hires(0,0,320,240,hires_out,capacity,&ow,&oh);
                    if(memcmp(native_ref,native_out,sizeof native_ref) || rn!=on ||
                       (rn>0 && memcmp(hires_ref,hires_out,(size_t)rn*4)))
                        fprintf(stderr,"atlas mismatch worker=%d scale=%d tiles=%u flip=%u\n",threaded,scale,tiles,flip);
                    check(!memcmp(native_ref,native_out,sizeof native_ref),"native pixels equal original tile banks");
                    check(rn==320*240*scale*scale && on==rn && rw==ow && rh==oh,"hires dimensions");
                    check(rn>0 && !memcmp(hires_ref,hires_out,(size_t)rn*4),"hires pixels equal original tile banks");
                    digest=fnv(native_out,sizeof native_out,digest);
                    if(on>0)digest=fnv(hires_out,(size_t)on*4,digest);
                }
            }
            printf("atlas exact batching=%d worker=%d scale=%d\n",batching,threaded,scale);
        }
        if(threaded)gl_renderer_render_thread_stop();
      }
    }
    check(glGetError()==GL_NO_ERROR,"no GL error");
    printf("atlas=%016llx\n",(unsigned long long)digest);
    printf("checks=%d failures=%d\n",checks,failures);
    free(hires_ref);free(hires_out);gl_renderer_shutdown();SDL_DestroyWindow(win);SDL_Quit();
    return failures?1:0;
}
