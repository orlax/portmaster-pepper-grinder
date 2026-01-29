/*
 * diagnose_textures.c - Diagnostic hook for Pepper Grinder
 * 
 * Purpose: Identify what texture functions Chowdren calls and when
 * 
 * Build:
 *   gcc -shared -fPIC -o libdiagnose.so diagnose_textures.c -ldl -lpthread
 * 
 * Usage:
 *   LD_PRELOAD=./libdiagnose.so ./Chowdren_pepper 2>&1 | tee texture_log.txt
 */

#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <pthread.h>
#include <sys/time.h>

// ============================================================================
// Logging utilities
// ============================================================================

static FILE* log_file = NULL;
static pthread_mutex_t log_mutex = PTHREAD_MUTEX_INITIALIZER;
static struct timeval start_time;
static size_t total_texture_bytes = 0;
static int texture_count = 0;

__attribute__((constructor))
static void init_hook() {
    gettimeofday(&start_time, NULL);
    log_file = fopen("/tmp/pepper_texture_log.txt", "w");
    if (!log_file) log_file = stderr;
    
    fprintf(log_file, "=== Pepper Grinder Texture Diagnostic ===\n");
    fprintf(log_file, "Timestamp (ms), Function, Width, Height, Format, Size (bytes)\n");
    fflush(log_file);
    
    fprintf(stderr, "[PepperDiag] Hook loaded. Logging to /tmp/pepper_texture_log.txt\n");
}

__attribute__((destructor))
static void cleanup_hook() {
    pthread_mutex_lock(&log_mutex);
    fprintf(log_file, "\n=== SUMMARY ===\n");
    fprintf(log_file, "Total textures: %d\n", texture_count);
    fprintf(log_file, "Total bytes: %zu (%.2f MB)\n", total_texture_bytes, 
            total_texture_bytes / 1024.0 / 1024.0);
    if (log_file != stderr) fclose(log_file);
    pthread_mutex_unlock(&log_mutex);
    
    fprintf(stderr, "[PepperDiag] Total: %d textures, %.2f MB\n", 
            texture_count, total_texture_bytes / 1024.0 / 1024.0);
}

static double get_elapsed_ms() {
    struct timeval now;
    gettimeofday(&now, NULL);
    return (now.tv_sec - start_time.tv_sec) * 1000.0 + 
           (now.tv_usec - start_time.tv_usec) / 1000.0;
}

static void log_texture(const char* func, int width, int height, 
                        unsigned int format, size_t size) {
    pthread_mutex_lock(&log_mutex);
    texture_count++;
    total_texture_bytes += size;
    fprintf(log_file, "%.2f, %s, %d, %d, 0x%X, %zu\n", 
            get_elapsed_ms(), func, width, height, format, size);
    
    // Print progress every 500 textures
    if (texture_count % 500 == 0) {
        fprintf(stderr, "[PepperDiag] Loaded %d textures (%.2f MB so far)\n",
                texture_count, total_texture_bytes / 1024.0 / 1024.0);
        fflush(log_file);
    }
    pthread_mutex_unlock(&log_mutex);
}

// ============================================================================
// OpenGL Hooks
// ============================================================================

// GL constants we care about
#define GL_RGBA 0x1908
#define GL_UNSIGNED_BYTE 0x1401
#define GL_TEXTURE_2D 0x0DE1

typedef unsigned int GLenum;
typedef int GLint;
typedef int GLsizei;

// glTexImage2D hook
static void (*real_glTexImage2D)(GLenum target, GLint level, GLint internalformat,
                                  GLsizei width, GLsizei height, GLint border,
                                  GLenum format, GLenum type, const void *data) = NULL;

void glTexImage2D(GLenum target, GLint level, GLint internalformat,
                  GLsizei width, GLsizei height, GLint border,
                  GLenum format, GLenum type, const void *data) {
    if (!real_glTexImage2D) {
        real_glTexImage2D = dlsym(RTLD_NEXT, "glTexImage2D");
    }
    
    size_t bytes_per_pixel = 4; // Assume RGBA
    if (format == 0x1907) bytes_per_pixel = 3; // GL_RGB
    size_t size = width * height * bytes_per_pixel;
    
    log_texture("glTexImage2D", width, height, format, size);
    
    real_glTexImage2D(target, level, internalformat, width, height, 
                      border, format, type, data);
}

// glTexSubImage2D hook (for texture updates)
static void (*real_glTexSubImage2D)(GLenum target, GLint level,
                                     GLint xoffset, GLint yoffset,
                                     GLsizei width, GLsizei height,
                                     GLenum format, GLenum type, const void *data) = NULL;

void glTexSubImage2D(GLenum target, GLint level,
                     GLint xoffset, GLint yoffset,
                     GLsizei width, GLsizei height,
                     GLenum format, GLenum type, const void *data) {
    if (!real_glTexSubImage2D) {
        real_glTexSubImage2D = dlsym(RTLD_NEXT, "glTexSubImage2D");
    }
    
    size_t bytes_per_pixel = 4;
    if (format == 0x1907) bytes_per_pixel = 3;
    size_t size = width * height * bytes_per_pixel;
    
    log_texture("glTexSubImage2D", width, height, format, size);
    
    real_glTexSubImage2D(target, level, xoffset, yoffset, width, height,
                         format, type, data);
}

// ============================================================================
// SDL2 Hooks (in case Chowdren uses SDL for textures)
// ============================================================================

typedef void SDL_Renderer;
typedef void SDL_Surface;
typedef void SDL_Texture;

// SDL_CreateTextureFromSurface hook
static SDL_Texture* (*real_SDL_CreateTextureFromSurface)(SDL_Renderer* renderer,
                                                          SDL_Surface* surface) = NULL;

SDL_Texture* SDL_CreateTextureFromSurface(SDL_Renderer* renderer, SDL_Surface* surface) {
    if (!real_SDL_CreateTextureFromSurface) {
        real_SDL_CreateTextureFromSurface = dlsym(RTLD_NEXT, "SDL_CreateTextureFromSurface");
    }
    
    // Try to get surface dimensions (SDL_Surface struct layout)
    // This is a rough guess - actual struct may differ
    int* surface_ptr = (int*)surface;
    int width = surface_ptr[1];  // offset may vary
    int height = surface_ptr[2]; // offset may vary
    
    // Sanity check dimensions
    if (width > 0 && width < 10000 && height > 0 && height < 10000) {
        log_texture("SDL_CreateTextureFromSurface", width, height, 0, width * height * 4);
    } else {
        log_texture("SDL_CreateTextureFromSurface", -1, -1, 0, 0);
    }
    
    return real_SDL_CreateTextureFromSurface(renderer, surface);
}

// SDL_CreateTexture hook
static SDL_Texture* (*real_SDL_CreateTexture)(SDL_Renderer* renderer,
                                               uint32_t format,
                                               int access,
                                               int w, int h) = NULL;

SDL_Texture* SDL_CreateTexture(SDL_Renderer* renderer, uint32_t format,
                                int access, int w, int h) {
    if (!real_SDL_CreateTexture) {
        real_SDL_CreateTexture = dlsym(RTLD_NEXT, "SDL_CreateTexture");
    }
    
    log_texture("SDL_CreateTexture", w, h, format, w * h * 4);
    
    return real_SDL_CreateTexture(renderer, format, access, w, h);
}

// SDL_UpdateTexture hook
static int (*real_SDL_UpdateTexture)(SDL_Texture* texture,
                                      const void* rect,
                                      const void* pixels,
                                      int pitch) = NULL;

int SDL_UpdateTexture(SDL_Texture* texture, const void* rect,
                      const void* pixels, int pitch) {
    if (!real_SDL_UpdateTexture) {
        real_SDL_UpdateTexture = dlsym(RTLD_NEXT, "SDL_UpdateTexture");
    }
    
    // Can't easily get dimensions here, just log that it happened
    log_texture("SDL_UpdateTexture", -1, -1, 0, 0);
    
    return real_SDL_UpdateTexture(texture, rect, pixels, pitch);
}

// ============================================================================
// Memory allocation hooks (to track large allocations)
// ============================================================================

static void* (*real_malloc)(size_t size) = NULL;
static void (*real_free)(void* ptr) = NULL;

static size_t large_alloc_count = 0;
static size_t large_alloc_bytes = 0;

void* malloc(size_t size) {
    if (!real_malloc) {
        real_malloc = dlsym(RTLD_NEXT, "malloc");
    }
    
    // Track allocations > 100KB (likely texture buffers)
    if (size > 100 * 1024) {
        pthread_mutex_lock(&log_mutex);
        large_alloc_count++;
        large_alloc_bytes += size;
        
        // Log first 20 large allocations
        if (large_alloc_count <= 20) {
            fprintf(log_file, "%.2f, MALLOC, 0, 0, 0, %zu\n", get_elapsed_ms(), size);
        }
        pthread_mutex_unlock(&log_mutex);
    }
    
    return real_malloc(size);
}

// Note: We don't hook free() by default as it can cause issues
// Uncomment if needed for debugging
/*
void free(void* ptr) {
    if (!real_free) {
        real_free = dlsym(RTLD_NEXT, "free");
    }
    real_free(ptr);
}
*/
