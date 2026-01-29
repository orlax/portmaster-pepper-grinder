/*
 * pepper_optimizer.c - Runtime texture optimization for Pepper Grinder
 * 
 * Strategy: Intercept glTexImage2D and downscale large textures by 50%
 * This reduces GPU memory AND system RAM (driver cache)
 * 
 * Build (basic):
 *   gcc -shared -fPIC -O3 -o libpepperopt.so pepper_optimizer.c -ldl -lpthread -lm
 * 
 * Build (with stb_image_resize for better quality):
 *   gcc -shared -fPIC -O3 -DUSE_STB_RESIZE -o libpepperopt.so pepper_optimizer.c -ldl -lpthread -lm
 * 
 * Usage:
 *   LD_PRELOAD=./libpepperopt.so ./Chowdren_pepper
 * 
 * Environment variables:
 *   PEPPER_SCALE=0.5      - Scale factor (default 0.5 = 50%)
 *   PEPPER_MIN_SIZE=64    - Minimum texture size to downscale (default 64)
 *   PEPPER_VERBOSE=1      - Enable verbose logging
 *   PEPPER_DISABLE=1      - Disable optimization (passthrough)
 */

#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <pthread.h>
#include <math.h>

// ============================================================================
// Configuration
// ============================================================================

static float g_scale_factor = 0.5f;      // 50% scale by default
static int g_min_size = 64;              // Don't scale textures smaller than this
static int g_verbose = 0;                // Verbose logging
static int g_disabled = 0;               // Disable all optimization

static size_t g_original_bytes = 0;
static size_t g_optimized_bytes = 0;
static int g_texture_count = 0;
static int g_scaled_count = 0;

static pthread_mutex_t g_mutex = PTHREAD_MUTEX_INITIALIZER;

// ============================================================================
// OpenGL types and constants
// ============================================================================

typedef unsigned int GLenum;
typedef int GLint;
typedef int GLsizei;
typedef unsigned char GLubyte;

#define GL_RGBA 0x1908
#define GL_RGB 0x1907
#define GL_UNSIGNED_BYTE 0x1401
#define GL_TEXTURE_2D 0x0DE1

// ============================================================================
// Simple box filter downscaler (fast, reasonable quality)
// ============================================================================

static void downscale_rgba_box(const uint8_t* src, int src_w, int src_h,
                                uint8_t* dst, int dst_w, int dst_h) {
    // Box filter: average 2x2 blocks
    float scale_x = (float)src_w / dst_w;
    float scale_y = (float)src_h / dst_h;
    
    for (int y = 0; y < dst_h; y++) {
        for (int x = 0; x < dst_w; x++) {
            int src_x = (int)(x * scale_x);
            int src_y = (int)(y * scale_y);
            
            // Sample 2x2 block and average
            int r = 0, g = 0, b = 0, a = 0;
            int samples = 0;
            
            for (int dy = 0; dy < 2 && (src_y + dy) < src_h; dy++) {
                for (int dx = 0; dx < 2 && (src_x + dx) < src_w; dx++) {
                    int idx = ((src_y + dy) * src_w + (src_x + dx)) * 4;
                    r += src[idx + 0];
                    g += src[idx + 1];
                    b += src[idx + 2];
                    a += src[idx + 3];
                    samples++;
                }
            }
            
            int dst_idx = (y * dst_w + x) * 4;
            dst[dst_idx + 0] = r / samples;
            dst[dst_idx + 1] = g / samples;
            dst[dst_idx + 2] = b / samples;
            dst[dst_idx + 3] = a / samples;
        }
    }
}

// Bilinear filter (better quality, slightly slower)
static void downscale_rgba_bilinear(const uint8_t* src, int src_w, int src_h,
                                     uint8_t* dst, int dst_w, int dst_h) {
    float x_ratio = (float)(src_w - 1) / dst_w;
    float y_ratio = (float)(src_h - 1) / dst_h;
    
    for (int y = 0; y < dst_h; y++) {
        for (int x = 0; x < dst_w; x++) {
            float gx = x * x_ratio;
            float gy = y * y_ratio;
            int gxi = (int)gx;
            int gyi = (int)gy;
            float fx = gx - gxi;
            float fy = gy - gyi;
            
            // Clamp
            int gxi1 = (gxi + 1 < src_w) ? gxi + 1 : gxi;
            int gyi1 = (gyi + 1 < src_h) ? gyi + 1 : gyi;
            
            // Get 4 neighboring pixels
            const uint8_t* p00 = &src[(gyi * src_w + gxi) * 4];
            const uint8_t* p10 = &src[(gyi * src_w + gxi1) * 4];
            const uint8_t* p01 = &src[(gyi1 * src_w + gxi) * 4];
            const uint8_t* p11 = &src[(gyi1 * src_w + gxi1) * 4];
            
            // Bilinear interpolation for each channel
            uint8_t* out = &dst[(y * dst_w + x) * 4];
            for (int c = 0; c < 4; c++) {
                float v = p00[c] * (1-fx) * (1-fy) +
                          p10[c] * fx * (1-fy) +
                          p01[c] * (1-fx) * fy +
                          p11[c] * fx * fy;
                out[c] = (uint8_t)(v + 0.5f);
            }
        }
    }
}

// ============================================================================
// Initialization
// ============================================================================

__attribute__((constructor))
static void init_optimizer() {
    // Read configuration from environment
    const char* env_scale = getenv("PEPPER_SCALE");
    const char* env_min = getenv("PEPPER_MIN_SIZE");
    const char* env_verbose = getenv("PEPPER_VERBOSE");
    const char* env_disable = getenv("PEPPER_DISABLE");
    
    if (env_scale) g_scale_factor = atof(env_scale);
    if (env_min) g_min_size = atoi(env_min);
    if (env_verbose) g_verbose = atoi(env_verbose);
    if (env_disable) g_disabled = atoi(env_disable);
    
    // Sanity checks
    if (g_scale_factor <= 0 || g_scale_factor > 1.0f) g_scale_factor = 0.5f;
    if (g_min_size < 8) g_min_size = 8;
    
    fprintf(stderr, "[PepperOpt] ========================================\n");
    fprintf(stderr, "[PepperOpt] Texture Optimizer Loaded\n");
    fprintf(stderr, "[PepperOpt] Scale: %.0f%%, Min size: %d\n", 
            g_scale_factor * 100, g_min_size);
    if (g_disabled) {
        fprintf(stderr, "[PepperOpt] DISABLED (passthrough mode)\n");
    }
    fprintf(stderr, "[PepperOpt] ========================================\n");
}

__attribute__((destructor))
static void cleanup_optimizer() {
    pthread_mutex_lock(&g_mutex);
    
    float saved_mb = (g_original_bytes - g_optimized_bytes) / 1024.0f / 1024.0f;
    float reduction = g_original_bytes > 0 ? 
        (1.0f - (float)g_optimized_bytes / g_original_bytes) * 100 : 0;
    
    fprintf(stderr, "[PepperOpt] ========================================\n");
    fprintf(stderr, "[PepperOpt] Session Summary:\n");
    fprintf(stderr, "[PepperOpt]   Total textures: %d\n", g_texture_count);
    fprintf(stderr, "[PepperOpt]   Scaled textures: %d\n", g_scaled_count);
    fprintf(stderr, "[PepperOpt]   Original size: %.2f MB\n", 
            g_original_bytes / 1024.0f / 1024.0f);
    fprintf(stderr, "[PepperOpt]   Optimized size: %.2f MB\n", 
            g_optimized_bytes / 1024.0f / 1024.0f);
    fprintf(stderr, "[PepperOpt]   Saved: %.2f MB (%.1f%%)\n", saved_mb, reduction);
    fprintf(stderr, "[PepperOpt] ========================================\n");
    
    pthread_mutex_unlock(&g_mutex);
}

// ============================================================================
// OpenGL Hook: glTexImage2D
// ============================================================================

static void (*real_glTexImage2D)(GLenum target, GLint level, GLint internalformat,
                                  GLsizei width, GLsizei height, GLint border,
                                  GLenum format, GLenum type, const void *data) = NULL;

void glTexImage2D(GLenum target, GLint level, GLint internalformat,
                  GLsizei width, GLsizei height, GLint border,
                  GLenum format, GLenum type, const void *data) {
    
    if (!real_glTexImage2D) {
        real_glTexImage2D = dlsym(RTLD_NEXT, "glTexImage2D");
        if (!real_glTexImage2D) {
            fprintf(stderr, "[PepperOpt] ERROR: Could not find real glTexImage2D!\n");
            return;
        }
    }
    
    // Passthrough if disabled or no data
    if (g_disabled || !data) {
        real_glTexImage2D(target, level, internalformat, width, height, 
                          border, format, type, data);
        return;
    }
    
    // Only optimize RGBA textures with unsigned byte data
    // and only for level 0 (base mipmap)
    int should_scale = (target == GL_TEXTURE_2D &&
                        level == 0 &&
                        format == GL_RGBA &&
                        type == GL_UNSIGNED_BYTE &&
                        width >= g_min_size &&
                        height >= g_min_size);
    
    pthread_mutex_lock(&g_mutex);
    g_texture_count++;
    size_t original_size = width * height * 4;
    g_original_bytes += original_size;
    pthread_mutex_unlock(&g_mutex);
    
    if (should_scale) {
        int new_width = (int)(width * g_scale_factor);
        int new_height = (int)(height * g_scale_factor);
        
        // Ensure minimum size
        if (new_width < 8) new_width = 8;
        if (new_height < 8) new_height = 8;
        
        // Ensure dimensions don't increase
        if (new_width >= width || new_height >= height) {
            // No point in scaling, passthrough
            pthread_mutex_lock(&g_mutex);
            g_optimized_bytes += original_size;
            pthread_mutex_unlock(&g_mutex);
            
            real_glTexImage2D(target, level, internalformat, width, height,
                              border, format, type, data);
            return;
        }
        
        // Allocate buffer for scaled texture
        size_t new_size = new_width * new_height * 4;
        uint8_t* scaled_data = malloc(new_size);
        
        if (scaled_data) {
            // Downscale the texture
            downscale_rgba_bilinear((const uint8_t*)data, width, height,
                                    scaled_data, new_width, new_height);
            
            // Upload scaled texture
            real_glTexImage2D(target, level, internalformat, new_width, new_height,
                              border, format, type, scaled_data);
            
            free(scaled_data);
            
            pthread_mutex_lock(&g_mutex);
            g_scaled_count++;
            g_optimized_bytes += new_size;
            
            if (g_verbose || g_scaled_count <= 5) {
                fprintf(stderr, "[PepperOpt] Scaled %dx%d -> %dx%d (saved %.1f KB)\n",
                        width, height, new_width, new_height,
                        (original_size - new_size) / 1024.0f);
            } else if (g_scaled_count % 500 == 0) {
                fprintf(stderr, "[PepperOpt] Progress: %d textures scaled...\n", g_scaled_count);
            }
            pthread_mutex_unlock(&g_mutex);
            
            return;
        }
        // If malloc failed, fall through to passthrough
    }
    
    // Passthrough for non-scaled textures
    pthread_mutex_lock(&g_mutex);
    g_optimized_bytes += original_size;
    pthread_mutex_unlock(&g_mutex);
    
    real_glTexImage2D(target, level, internalformat, width, height,
                      border, format, type, data);
}

// ============================================================================
// OpenGL Hook: glTexSubImage2D (for texture updates)
// ============================================================================

static void (*real_glTexSubImage2D)(GLenum target, GLint level,
                                     GLint xoffset, GLint yoffset,
                                     GLsizei width, GLsizei height,
                                     GLenum format, GLenum type, 
                                     const void *data) = NULL;

void glTexSubImage2D(GLenum target, GLint level,
                     GLint xoffset, GLint yoffset,
                     GLsizei width, GLsizei height,
                     GLenum format, GLenum type, const void *data) {
    
    if (!real_glTexSubImage2D) {
        real_glTexSubImage2D = dlsym(RTLD_NEXT, "glTexSubImage2D");
    }
    
    // For SubImage, we need to scale offsets and dimensions consistently
    // This is tricky because we don't know the original texture size
    // For now, just passthrough - SubImage is typically used for small updates
    
    if (g_disabled || !real_glTexSubImage2D) {
        if (real_glTexSubImage2D) {
            real_glTexSubImage2D(target, level, xoffset, yoffset,
                                 width, height, format, type, data);
        }
        return;
    }
    
    // Scale offsets and dimensions
    int new_xoffset = (int)(xoffset * g_scale_factor);
    int new_yoffset = (int)(yoffset * g_scale_factor);
    int new_width = (int)(width * g_scale_factor);
    int new_height = (int)(height * g_scale_factor);
    
    if (new_width < 1) new_width = 1;
    if (new_height < 1) new_height = 1;
    
    // If it's RGBA data, scale it
    if (format == GL_RGBA && type == GL_UNSIGNED_BYTE && data &&
        width >= g_min_size && height >= g_min_size) {
        
        size_t new_size = new_width * new_height * 4;
        uint8_t* scaled_data = malloc(new_size);
        
        if (scaled_data) {
            downscale_rgba_bilinear((const uint8_t*)data, width, height,
                                    scaled_data, new_width, new_height);
            
            real_glTexSubImage2D(target, level, new_xoffset, new_yoffset,
                                 new_width, new_height, format, type, scaled_data);
            
            free(scaled_data);
            return;
        }
    }
    
    // Passthrough
    real_glTexSubImage2D(target, level, xoffset, yoffset,
                         width, height, format, type, data);
}
