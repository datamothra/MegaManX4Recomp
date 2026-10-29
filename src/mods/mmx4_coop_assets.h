#ifndef MMX4_COOP_ASSETS_H
#define MMX4_COOP_ASSETS_H
#include <stddef.h>
#include <stdint.h>
typedef struct { const uint8_t *data; size_t size; uint32_t type; } Mmx4Asset;
/* Character CLUT -> byte offset in the packed 256-wide native palette.
 * Other CLUTs retain the shared GPU palette (including animated effects). */
int mmx4_coop_character_palette_offset(uint16_t clut);
/* Native8002A484's clamped RGB additions/subtractions. Amounts retain their
 * packed channel positions; bits0..2 select subtraction for R/G/B. */
uint16_t mmx4_coop_palette_lighting(uint16_t color,const uint16_t amounts[3],unsigned subtract);
/* Original SLUS-00561 ARC descriptor/sector format, loader 80013E68. */
int mmx4_coop_arc_asset(const uint8_t *data, size_t size, unsigned member, Mmx4Asset *out);
/* Original word LZ format at 80016FF4, also used by X6 at 80018BE0. */
int mmx4_coop_decode_sprite(const uint8_t *src, size_t size, uint8_t *dst,
                            size_t capacity, size_t *written);
/* Native 16px assembly tile -> private, forward-sampled tile. Low key bits
 * 0/1 encode X/Y reflection; source origins remain aligned to 16 pixels. */
uint16_t mmx4_coop_sprite_quad_tile(uint32_t quad[10]);
void mmx4_coop_sprite_tile_pixels(const uint16_t pixels[256*256],uint16_t tile,
                                  uint16_t out[16*16]);
/* Forward-sampled immutable sprite atlases. Fifteen 16px cells per row keep
 * every exclusive UV edge <=240, representable in native eight-bit packets.
 * Keys0..7 select a225-tile page and its per-cell reflection;8 is transparent.
 * The bank renderer point-samples these pixels even with world filtering. */
int mmx4_coop_sprite_atlas_tile(unsigned tiles,uint16_t tile,
                               uint16_t *key,uint16_t *uv);
int mmx4_coop_sprite_atlas_pixels(const uint16_t pixels[256*256],unsigned tiles,
                                 unsigned key,uint16_t out[240*240],
                                 unsigned *width,unsigned *height);
#endif
