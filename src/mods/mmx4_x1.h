#ifndef MMX4_X1_H
#define MMX4_X1_H
#include <stdint.h>
#include "cpu_state.h"
#ifdef __cplusplus
extern "C" {
#endif
int mmx4_x1_enabled(unsigned character);
int mmx4_x1_buster_context(void);
int mmx4_x1_render(CPUState *cpu,uint32_t actor,unsigned character);
int mmx4_x1_resolve_texture(uint16_t id);
int mmx4_x1_x_resources(uint32_t out[4]);
int mmx4_coop_x1_resources(uint32_t out[4]);
void mmx4_x1_enforce_current(void);
int mmx4_x1_native_ready(void);
void mmx4_x1_native_reset(void);
#ifdef __cplusplus
}
#endif
#endif
