/*
 * pepper_optimizer_v2.c - Aggressive memory optimization for Pepper Grinder
 * 
 * Strategy: 
 * 1. Hook malloc to track large allocations (likely texture buffers)
 * 2. Hook glTexImage2D to downscale textures
 * 3. After uploading to GPU, FREE the original buffer to reclaim RAM
 * 
 * Build:
 *   gcc -shared -fPIC -O3 -o libpepperopt2.so pepper_optimizer_v2.c -ldl -lpthread -lm
 * 
 * Usage:
 *   LD_PRELOAD=/path/to/libpepperopt2.so ./Chowdren
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

static float g_scale_factor = 0.5f;
static int g_min_size = 64;
static int g_verbose = 0;
static int g_disabled = 0;
static int g_aggressive_free = 1;  // NEW: Free buffers after GPU upload

// Stats
static size_t g_original_bytes = 0;
static size_t g_optimized_bytes = 0;
static size_t g_freed_bytes = 0;
static int g_texture_count = 0;
static int g_scaled_count = 0;
static int g_freed_count = 0;

static pthread_mutex_t g_mutex = PTHREAD_MUTEX_INITIALIZER;

// ============================================================================
// Buffer tracking for aggressive freeing
// ============================================================================

#define MAX_TRACKED_BUFFERS 20000

typedef struct {
    void* ptr;
    size_t size;
    int freed;
} TrackedBuffer;

static TrackedBuffer g_buffers[MAX_TRACKED_BUFFERS];
static int g_buffer_count = 0;
static pthread_mutex_t g_buffer_mutex = PTHREAD_MUTEX_INITIALIZER;

// Track a large allocation
static void track_buffer(void* ptr, size_t size) {
    if (!ptr || size < 4096) return;  // Only track allocations >= 4KB
    
    pthread_mutex_lock(&g_buffer_mutex);
    if (g_buffer_count < MAX_TRACKED_BUFFERS) {
        g_buffers[g_buffer_count].ptr = ptr;
        g_buffers[g_buffer_count].size = size;
        g_buffers[g_buffer_count].freed = 0;
        g_buffer_count++;
    }
    pthread_mutex_unlock(&g_buffer_mutex);
}

// Find and mark a buffer for freeing (returns size if found)
static size_t find_buffer(const void* ptr) {
    pthread_mutex_lock(&g_buffer_mutex);
    for (int i = g_buffer_count - 1; i >= 0; i--) {  // Search backwards (most recent first)
        if (g_buffers[i].ptr == ptr && !g_buffers[i].freed) {
            size_t size = g_buffers[i].size;
            pthread_mutex_unlock(&g_buffer_mutex);
            return size;
        }
    }
    pthread_mutex_unlock(&g_buffer_mutex);
    return 0;
}

// Mark buffer as freed
static void mark_freed(const void* ptr) {
    pthread_mutex_lock(&g_buffer_mutex);
    for (int i = g_buffer_count - 1; i >= 0; i--) {
        if (g_buffers[i].ptr == ptr && !g_buffers[i].freed) {
            g_buffers[i].freed = 1;
            break;
        }
    }
    pthread_mutex_unlock(&g_buffer_mutex);
}

// ============================================================================
// OpenGL types
// ============================================================================

typedef unsigned int GLenum;
typedef int GLint;
typedef int GLsizei;

#define GL_RGBA 0x1908
#define GL_RGB 0x1907
#define GL_UNSIGNED_BYTE 0x1401
#define GL_TEXTURE_2D 0x0DE1

// ============================================================================
// Real function pointers
// ============================================================================

static void* (*real_malloc)(size_t size) = NULL;
static void (*real_free)(void* ptr) = NULL;
static void* (*real_realloc)(void* ptr, size_t size) = NULL;
static void* (*real_calloc)(size_t nmemb, size_t size) = NULL;

static void (*real_glTexImage2D)(GLenum target, GLint level, GLint internalformat,
                                  GLsizei width, GLsizei height, GLint border,
                                  GLenum format, GLenum type, const void *data) = NULL;

// Flag to prevent recursion in malloc hook
static __thread int in_malloc = 0;

// ============================================================================
// Downscaler
// ============================================================================

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
            
            int gxi1 = (gxi + 1 < src_w) ? gxi + 1 : gxi;
            int gyi1 = (gyi + 1 < src_h) ? gyi + 1 : gyi;
            
            const uint8_t* p00 = &src[(gyi * src_w + gxi) * 4];
            const uint8_t* p10 = &src[(gyi * src_w + gxi1) * 4];
            const uint8_t* p01 = &src[(gyi1 * src_w + gxi) * 4];
            const uint8_t* p11 = &src[(gyi1 * src_w + gxi1) * 4];
            
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
    const char* env_scale = getenv("PEPPER_SCALE");
    const char* env_min = getenv("PEPPER_MIN_SIZE");
    const char* env_verbose = getenv("PEPPER_VERBOSE");
    const char* env_disable = getenv("PEPPER_DISABLE");
    const char* env_aggressive = getenv("PEPPER_AGGRESSIVE_FREE");
    
    if (env_scale) g_scale_factor = atof(env_scale);
    if (env_min) g_min_size = atoi(env_min);
    if (env_verbose) g_verbose = atoi(env_verbose);
    if (env_disable) g_disabled = atoi(env_disable);
    if (env_aggressive) g_aggressive_free = atoi(env_aggressive);
    
    if (g_scale_factor <= 0 || g_scale_factor > 1.0f) g_scale_factor = 0.5f;
    if (g_min_size < 8) g_min_size = 8;
    
    // Initialize real function pointers early
    real_malloc = dlsym(RTLD_NEXT, "malloc");
    real_free = dlsym(RTLD_NEXT, "free");
    real_realloc = dlsym(RTLD_NEXT, "realloc");
    real_calloc = dlsym(RTLD_NEXT, "calloc");
    
    fprintf(stderr, "[PepperOpt2] ========================================\n");
    fprintf(stderr, "[PepperOpt2] Aggressive Memory Optimizer Loaded\n");
    fprintf(stderr, "[PepperOpt2] Scale: %.0f%%, Min size: %d\n", 
            g_scale_factor * 100, g_min_size);
    fprintf(stderr, "[PepperOpt2] Aggressive free: %s\n", 
            g_aggressive_free ? "ENABLED" : "disabled");
    if (g_disabled) {
        fprintf(stderr, "[PepperOpt2] DISABLED (passthrough mode)\n");
    }
    fprintf(stderr, "[PepperOpt2] ========================================\n");
}

__attribute__((destructor))
static void cleanup_optimizer() {
    pthread_mutex_lock(&g_mutex);
    
    float saved_mb = (g_original_bytes - g_optimized_bytes) / 1024.0f / 1024.0f;
    float freed_mb = g_freed_bytes / 1024.0f / 1024.0f;
    
    fprintf(stderr, "[PepperOpt2] ========================================\n");
    fprintf(stderr, "[PepperOpt2] Session Summary:\n");
    fprintf(stderr, "[PepperOpt2]   Total textures: %d\n", g_texture_count);
    fprintf(stderr, "[PepperOpt2]   Scaled textures: %d\n", g_scaled_count);
    fprintf(stderr, "[PepperOpt2]   Original size: %.2f MB\n", 
            g_original_bytes / 1024.0f / 1024.0f);
    fprintf(stderr, "[PepperOpt2]   Optimized size: %.2f MB\n", 
            g_optimized_bytes / 1024.0f / 1024.0f);
    fprintf(stderr, "[PepperOpt2]   GPU memory saved: %.2f MB\n", saved_mb);
    fprintf(stderr, "[PepperOpt2]   Buffers freed: %d (%.2f MB)\n", g_freed_count, freed_mb);
    fprintf(stderr, "[PepperOpt2] ========================================\n");
    
    pthread_mutex_unlock(&g_mutex);
}

// ============================================================================
// malloc hook - track large allocations
// ============================================================================

void* malloc(size_t size) {
    if (!real_malloc) {
        real_malloc = dlsym(RTLD_NEXT, "malloc");
    }
    
    void* ptr = real_malloc(size);
    
    // Track large allocations (likely texture buffers)
    // Texture buffers are typically width*height*4 bytes
    // Minimum interesting size: 64*64*4 = 16KB
    if (!in_malloc && ptr && size >= 16384 && g_aggressive_free && !g_disabled) {
        in_malloc = 1;
        track_buffer(ptr, size);
        in_malloc = 0;
    }
    
    return ptr;
}

void* calloc(size_t nmemb, size_t size) {
    if (!real_calloc) {
        real_calloc = dlsym(RTLD_NEXT, "calloc");
    }
    
    void* ptr = real_calloc(nmemb, size);
    
    size_t total = nmemb * size;
    if (!in_malloc && ptr && total >= 16384 && g_aggressive_free && !g_disabled) {
        in_malloc = 1;
        track_buffer(ptr, total);
        in_malloc = 0;
    }
    
    return ptr;
}

void* realloc(void* old_ptr, size_t size) {
    if (!real_realloc) {
        real_realloc = dlsym(RTLD_NEXT, "realloc");
    }
    
    void* ptr = real_realloc(old_ptr, size);
    
    if (!in_malloc && ptr && size >= 16384 && g_aggressive_free && !g_disabled) {
        in_malloc = 1;
        if (old_ptr) mark_freed(old_ptr);
        track_buffer(ptr, size);
        in_malloc = 0;
    }
    
    return ptr;
}

void free(void* ptr) {
    if (!real_free) {
        real_free = dlsym(RTLD_NEXT, "free");
    }
    
    if (ptr && !in_malloc) {
        in_malloc = 1;
        mark_freed(ptr);
        in_malloc = 0;
    }
    
    real_free(ptr);
}

// ============================================================================
// glTexImage2D hook
// ============================================================================

void glTexImage2D(GLenum target, GLint level, GLint internalformat,
                  GLsizei width, GLsizei height, GLint border,
                  GLenum format, GLenum type, const void *data) {
    
    if (!real_glTexImage2D) {
        real_glTexImage2D = dlsym(RTLD_NEXT, "glTexImage2D");
        if (!real_glTexImage2D) {
            fprintf(stderr, "[PepperOpt2] ERROR: Could not find glTexImage2D!\n");
            return;
        }
    }
    
    if (g_disabled || !data) {
        real_glTexImage2D(target, level, internalformat, width, height, 
                          border, format, type, data);
        return;
    }
    
    size_t original_size = width * height * 4;
    
    // Check if we should scale this texture
    int should_scale = (target == GL_TEXTURE_2D &&
                        level == 0 &&
                        format == GL_RGBA &&
                        type == GL_UNSIGNED_BYTE &&
                        width >= g_min_size &&
                        height >= g_min_size);
    
    pthread_mutex_lock(&g_mutex);
    g_texture_count++;
    g_original_bytes += original_size;
    pthread_mutex_unlock(&g_mutex);
    
    // Find the source buffer for potential freeing
    size_t buffer_size = find_buffer(data);
    
    if (should_scale) {
        int new_width = (int)(width * g_scale_factor);
        int new_height = (int)(height * g_scale_factor);
        
        if (new_width < 8) new_width = 8;
        if (new_height < 8) new_height = 8;
        
        if (new_width < width && new_height < height) {
            size_t new_size = new_width * new_height * 4;
            
            in_malloc = 1;  // Prevent tracking our own allocation
            uint8_t* scaled_data = real_malloc(new_size);
            in_malloc = 0;
            
            if (scaled_data) {
                downscale_rgba_bilinear((const uint8_t*)data, width, height,
                                        scaled_data, new_width, new_height);
                
                real_glTexImage2D(target, level, internalformat, new_width, new_height,
                                  border, format, type, scaled_data);
                
                real_free(scaled_data);
                
                pthread_mutex_lock(&g_mutex);
                g_scaled_count++;
                g_optimized_bytes += new_size;
                
                if (g_verbose || g_scaled_count <= 5) {
                    fprintf(stderr, "[PepperOpt2] Scaled %dx%d -> %dx%d (saved %.1f KB)\n",
                            width, height, new_width, new_height,
                            (original_size - new_size) / 1024.0f);
                } else if (g_scaled_count % 500 == 0) {
                    fprintf(stderr, "[PepperOpt2] Progress: %d textures scaled...\n", g_scaled_count);
                }
                pthread_mutex_unlock(&g_mutex);
                
                // AGGRESSIVE FREE: Now free the original buffer!
                if (g_aggressive_free && buffer_size > 0) {
                    // Mark as freed in our tracking
                    mark_freed(data);
                    
                    // Actually free the buffer
                    real_free((void*)data);
                    
                    pthread_mutex_lock(&g_mutex);
                    g_freed_count++;
                    g_freed_bytes += buffer_size;
                    pthread_mutex_unlock(&g_mutex);
                    
                    if (g_verbose) {
                        fprintf(stderr, "[PepperOpt2] Freed source buffer: %.1f KB\n",
                                buffer_size / 1024.0f);
                    }
                }
                
                return;
            }
        }
    }
    
    // Passthrough
    pthread_mutex_lock(&g_mutex);
    g_optimized_bytes += original_size;
    pthread_mutex_unlock(&g_mutex);
    
    real_glTexImage2D(target, level, internalformat, width, height,
                      border, format, type, data);
    
    // Even for non-scaled textures, try to free the buffer
    if (g_aggressive_free && buffer_size > 0) {
        mark_freed(data);
        real_free((void*)data);
        
        pthread_mutex_lock(&g_mutex);
        g_freed_count++;
        g_freed_bytes += buffer_size;
        pthread_mutex_unlock(&g_mutex);
    }
}