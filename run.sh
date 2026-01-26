#!/bin/bash

XDG_DATA_HOME=${XDG_DATA_HOME:-$HOME/.local/share}

if [ -d "/opt/system/Tools/PortMaster/" ]; then
  controlfolder="/opt/system/Tools/PortMaster"
elif [ -d "/opt/tools/PortMaster/" ]; then
  controlfolder="/opt/tools/PortMaster"
elif [ -d "$XDG_DATA_HOME/PortMaster/" ]; then
  controlfolder="$XDG_DATA_HOME/PortMaster"
else
  controlfolder="/roms/ports/PortMaster"
fi

source "$controlfolder/control.txt"
export PORT_64BIT="Y"
unset PORT_32BIT

[ -f "${controlfolder}/mod_${CFW_NAME}.txt" ] && source "${controlfolder}/mod_${CFW_NAME}.txt"

get_controls

GAMEDIR="/$directory/ports/pepper"

# ensure /tmp exists for PortMaster control scripts that write there
mkdir -p /tmp
touch /tmp/gamecontrollerdb.txt 2>/dev/null || true

# logging disabled for now
#> "$GAMEDIR/log.txt" && exec > >(tee "$GAMEDIR/log.txt") 2>&1

# gl4es (kept, but we force drivers below explicitly)
if [ -f "${controlfolder}/libgl_${CFW_NAME}.txt" ]; then 
  source "${controlfolder}/libgl_${CFW_NAME}.txt"
else
  source "${controlfolder}/libgl_default.txt"
fi

cd "$GAMEDIR/gamedata"

# ---- controller mapping ----
export SDL_GAMECONTROLLERCONFIG="$sdl_controllerconfig"

# ---- load user settings first (so our overrides win) ----
[ -f "$GAMEDIR/settings.txt" ] && source "$GAMEDIR/settings.txt"

# ---- libraries / box64 paths ----
# Host/native libs used by wrapped/native components
export LD_LIBRARY_PATH="$LD_LIBRARY_PATH:$GAMEDIR/box64/native"

# Force SDL DynAPI to load SDL2 by soname (lets us override via BOX64_LD_LIBRARY_PATH)
export SDL_DYNAMIC_API="libSDL2-2.0.so.0"
#this line loads the libSDL2 that I got from the hollow knight port. (does not work at the moment)
#export SDL_DYNAMIC_API="$GAMEDIR/gamedata/lib/libSDL2-2.0.so.0"

# x86_64 libs search path (put gamedata/lib FIRST so your shipped SDL2 wins)
#export BOX64_LD_LIBRARY_PATH="$GAMEDIR/gamedata/lib:$GAMEDIR/box64/native:$GAMEDIR/gamedata:$GAMEDIR/gamedata/bin64"
export BOX64_LD_LIBRARY_PATH="$GAMEDIR/lib:$GAMEDIR/gamedata/sentry:$GAMEDIR/box64/native:$GAMEDIR/gamedata:$GAMEDIR/gamedata/bin64"

# ---- GL/EGL forcing (via gl4es bundle) ----
export SDL_VIDEO_GL_DRIVER="$GAMEDIR/gl4es/libGL.so.1"
export SDL_VIDEO_EGL_DRIVER="$GAMEDIR/gl4es/libEGL.so.1"
export BOX64_LIBGL="$GAMEDIR/gl4es/libGL.so.1"
export BOX64_LIBEGL="$GAMEDIR/gl4es/libEGL.so.1"

# If you still want to force GLES version, keep this (name is historical; harmless)
export BOX86_FORCE_ES=31

#trying to get Sentry to work
#export SENTRY_CRASHPAD_HANDLER="$GAMEDIR/gamedata/sentry/crashpad_handler"
export SENTRY_OPTIONS="{\"database_path\":\"$SENTRY_DB\",\"handler_path\":\"$GAMEDIR/gamedata/sentry/crashpad_handler\"}"
export PATH="$GAMEDIR/gamedata/sentry:$PATH"

# ---- SDL video backend ----
# fbcon attempt; if it fails, comment these out to let SDL choose
#export SDL_VIDEODRIVER=fbcon
#export SDL_FBDEV=/dev/fb0

# ---- Chowdren knobs ----
export CHOWDREN_FPS=60

# ---- box64 config ----
export BOX64_LOG=2
export BOX64_ALLOWMISSINGLIBS=1
export BOX64_DYNAREC=1
export BOX64_NOGTK=1
export BOX64_NOSDL=1

# permissions (sdcards/ext2/etc.)
chmod +x "$GAMEDIR/box64/box64"
chmod +x "$GAMEDIR/gamedata/bin64/Chowdren"

$GPTOKEYB "Chowdren" -c "$GAMEDIR/pepper.gptk" &
pm_message "Loading, please wait..."


"$GAMEDIR/box64/box64" "bin64/Chowdren"

pm_finish
