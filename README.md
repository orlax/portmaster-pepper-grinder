# Pepper Grinder (Chowdren 64-bit) on Knulli - Current Status

This repo documents my attempt to run a 64-bit Chowdren game ("Pepper Grinder")

[Pepper Grinder](https://www.gog.com/en/game/pepper_grinder)

the game was built using construct 2 and exported with Chowdren, very much like Iconoclasts 
this port is based on the existing [iconoclast port](https://portmaster.games/detail.html?name=iconoclasts)


on Knulli (RG40XX-V). I am sharing the current state so others can help.

## how to use whats already here? 

put this repo on your device and copy the game files to the "gamedata" folder 
gamefiles should be extracted from the GOG version of the game as that one is DRM-free (no steam stuff) 
then you can attempt to run either pepper.sh or westonwrap.sh 

both are failing at the moment. 



## What works

- Game data is found and preloaded (Startup data size: ~58 MB)
- Audio preload happens (sounds enumerated)
- gl4es loads and reports GLES 2.0 backend

## Initial failure (native SDL2 KMSDRM)

When launching 64-bit Chowdren via box64 with gl4es + system EGL (via the pepper.sh script) we arrive at:

```
Could not open window: eglQueryDevicesEXT is missing
```

The Mali EGL stack on Knulli does not provide EGL_EXT_device_enumeration,
so SDL2 KMSDRM fails at startup. <- I was told by an LLM, I am pretty out of my dev with this low level of programming.

## Westonpack attempt

Tried to use Westonpack (westonwrap.sh) to provide X11/Wayland and avoid
the KMSDRM EGL path. Approaches used:

- westonwrap backend: `headless noop kiosk`
- crusty frontend: `crusty_glx`
- gl4es for GL (libGL.so.1)
- box64 as the loader

### Current blockers with Westonpack

1) Xwayland fails because `libgbm.so.1` is missing:

```
bin/Xwayland: error while loading shared libraries: libgbm.so.1
```

2) `libcrusty.so` fails to preload under box64, so SDL falls back to the
native EGL path and the same `eglQueryDevicesEXT` error occurs.

### Verified dependencies

`ldd` for `libcrusty.so` resolves once gl4es is in the path:

```
libGL.so.1 => /media/SHARE/roms/ports/pepper/gl4es/libGL.so.1
```

But in the current runs, box64 still prints:

```
Warning, cannot pre-load /tmp/weston/lib_aarch64/graphics/crusty_glx//libcrusty.so
```

## Help wanted

If you have experience with Westonpack, box64, or Knulli graphics stacks,
I would appreciate help on:
- is it feasible to run box64 with Westonpack?
- is there a way to sort out the eglQueryDevicesEXT error? Iconoclasts is 32 bit and it seems that is why they could sort it out.
- or is this just not possible? how could I tell? 



## Device / OS

- Device: RG40XX-V (h700, aarch64, 1 GB RAM)
- OS: Knulli (gladiator-ii)
- PortMaster runtime
- No X11 available on the base system

- Getting Xwayland to see a working `libgbm.so.1` (crusty_gbm_fix?)
- Forcing `libcrusty.so` to preload under box64 reliably
- A recommended Westonpack mode for SDL2 + gl4es + Chowdren 64-bit

I can provide full logs if needed.
