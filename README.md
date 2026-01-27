# Pepper Grinder (Chowdren 64-bit) on Knulli — Current Status not working

This repo documents my attempt to run **Pepper Grinder** on a retro handheld using PortMaster and the Chowdren (64-bit) build (GOG version, DRM-free).

Buy the game here: [Pepper Grinder](https://www.gog.com/en/game/pepper_grinder)

the game was built using construct 2 and exported with Chowdren, very much like Iconoclasts 
this port is based on the existing [iconoclast port](https://portmaster.games/detail.html?name=iconoclasts)

## Target device / firmware

Device: Anbernic RG40XX-V (H700, 1GB RAM)
CFW: Knulli (gladiator-ii)
Architecture: aarch64
Renderer stack: Westonwrap/Westonpack + XWayland + GL4ES + Box64

Note: Knulli does not expose a working native Wayland video driver for this binary (forcing SDL_VIDEODRIVER=wayland fails).

## how to use whats already here? 

Copy this repo into your device ports folder:

roms/ports/pepper/

Extract your GOG Pepper Grinder game files and copy them into:

roms/ports/pepper/gamedata/ <- you have to create the gamedata folder
(GOG is recommended because it is DRM-free.)

Run: ./weston.sh 

## ✅ What works

The graphical pipeline does launch:

- Weston starts
- XWayland starts
- GL4ES initializes
- SDL creates a window

The game begins loading content successfully:

- reads Assets.dat
- loads ~58MB startup data
- preloads ~240 audio assets (“Sound bank” step)

## ❌ What fails

The game is consistently killed by the Linux OOM-killer (Out-of-Memory), after heavy asset/audio preload.

This is not an application-level crash. The OS forcibly kills the process once memory pressure peaks.

**Symptoms**

Exit code often appears as 137 (SIGKILL) or the process ends abruptly
Kernel logs show: Out of memory: Kill process (Chowdren)
```
===== POST-MORTEM lun 26 ene 2026 18:39:31 -05 =====
Exit code: 0
--- swapon --show ---
NAME       TYPE        SIZE   USED PRIO
/dev/zram0 partition 486,6M 103,4M 1000
--- /proc/swaps ---
Filename				Type		Size	Used	Priority
/dev/zram0                              partition	498312	105832	1000
--- free -m ---
               total       usado       libre  compartido   búf/caché  disponible
Mem:             973         203         626           1         153         770
Inter:           486         103         383
--- OOM (dmesg tail) ---
[ 3721.078494] udevd invoked oom-killer: gfp_mask=0x27080c0(GFP_KERNEL_ACCOUNT|__GFP_ZERO|__GFP_NOTRACK), nodemask=0, order=2, oom_score_adj=-1000
[ 3721.078577] [<ffffff8008161224>] oom_kill_process+0x90/0x408
[ 3721.078790] [ pid ]   uid  tgid total_vm      rss nr_ptes nr_pmds swapents oom_score_adj name
[ 3721.079621] Out of memory: Kill process 26596 (Chowdren) score 578 or sacrifice child
[ 3721.079704] Killed process 26596 (Chowdren) total-vm:1609972kB, anon-rss:267232kB, file-rss:243700kB, shmem-rss:8kB
--- zram stats ---
107487232 30915948 33853440        0 350806016     2398     5401     1248
   24602        0   196816      340  1288165        0 10305320    46090        0    19710    46460
===== END POST-MORTEM =====
```
Last visible lines before kill (runtime log excerpt)
```
...
LIBGL: Extension GL_OES_rgb8_rgba8  detected and used
LIBGL: Extension GL_EXT_texture_format_BGRA8888  detected and used
LIBGL: Extension GL_OES_depth_texture  detected and used
LIBGL: Extension GL_OES_texture_stencil8  detected and used
LIBGL: Extension GL_EXT_texture_rg  detected and used
LIBGL: Extension GL_EXT_color_buffer_float  detected and used
LIBGL: Extension GL_EXT_color_buffer_half_float  detected and used
LIBGL: high precision float in fragment shader available and used
LIBGL: Max vertex attrib: 16
LIBGL: Extension GL_OES_standard_derivatives  detected and used
LIBGL: Extension GL_ARM_shader_framebuffer_fetch detected and used
LIBGL: Extension GL_OES_get_program_binary  detected and used
LIBGL: Number of supported Program Binary Format: 1
LIBGL: Max texture size: 8192
LIBGL: Max Varying Vector: 15
LIBGL: Texture Units: 16/16 (hardware: 16), Max lights: 8, Max planes: 6
LIBGL: Max Color Attachments: 1 / Draw buffers: 1
LIBGL: Hardware vendor is ARM
LIBGL: Targeting OpenGL 2.1
LIBGL: Not trying to batch small subsequent glDrawXXXX
LIBGL: Trying to use VBO
LIBGL: glXMakeCurrent FBO workaround enabled
LIBGL: FBO workaround for using binded texture enabled
LIBGL: Force texture for Attachment color0 on FBO
LIBGL: Hack to trigger a SwapBuffers when a Full Framebuffer Blit on default FBO is done
LIBGL: Current folder is:/userdata/roms/ports/pepper/gamedata
LIBGL: Texture Copies will be skipped
LIBGL: Framebuffer Textures will be scaled by 0.25
Crusty's SDL2 backend is running with these attributes: 
Red Size: 8
Green Size: 8
Blue Size: 8
Alpha Size: 8
Buffer Size: 32
Double Buffer: 1
Depth Size: 24
Stencil Size: 8
Accum Red Size: 0
Accum Green Size: 0
Accum Blue Size: 0
Accum Alpha Size: 0
Multisample Buffers: 0
Multisample Samples: 0
Context Major Version: 3
Context Minor Version: 2
Context Profile Mask: 4
Renderer: GL4ES wrapper - ptitSeb - 
LIBGL: unshrinking shrinked texture for FBO
Image read took 0.6831741259999973
/tmp/weston/westonwrap.sh: línea 48: 26596 Killed                  XDG_CONFIG_HOME=/userdata/roms/ports/pepper/conf/config XDG_DATA_HOME=/userdata/roms/ports/pepper/conf/local /userdata/roms/ports/pepper/box64/box64 ./bin64/Chowdren
---------------------------------------------------------------------------------------------------
Your command has exited with exit code 137.
```

## The current status 
So I think i got to a place where the actual game tries to open but the way this particular game operates is pre-loading too many asssets for this low-powered device to handle. 
also I think there is a lot of overhead with the current graphics stack, in the case of Iconoclasts it was a 32 bit executable wich I think was able to run with less overhead. 
for this game as it is 64 bits the only way I found it was able to actually create a window was using westonpack just trying to run box64 failed 

## Next Steps: 
- Try to get this game to "open" with Box64 "only" but my attempts to use "export SDL_DYNAMIC_API="libSDL2-2.0.so.0" all failed.
- Do something to reduce the actual size of the Data.assets sounds? would require to patch this and I dont think I have the ability
- Get help from the actual developers of the game.

I am leaving this at this point, if someone more experienced in this stuff than me wants to keep going, fork this repo! 


