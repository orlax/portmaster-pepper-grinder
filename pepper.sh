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

  source $controlfolder/control.txt
  #export PORT_32BIT="Y"

  [ -f "${controlfolder}/mod_${CFW_NAME}.txt" ] && source "${controlfolder}/mod_${CFW_NAME}.txt"

  get_controls

  GAMEDIR="/media/SHARE/roms/ports/pepper"
  > "$GAMEDIR/log.txt" && exec > >(tee "$GAMEDIR/log.txt") 2>&1

  # gl4es
  if [ -f "${controlfolder}/libgl_${CFW_NAME}.txt" ]; then
    source "${controlfolder}/libgl_${CFW_NAME}.txt"
  else
    source "${controlfolder}/libgl_default.txt"
  fi

  cd $GAMEDIR/gamedata

  export CHOWDREN_FPS=30
  # this scale controls texture size the lower the less memory used but more pixelated
  export LIBGL_FB_TEX_SCALE=0.25
  export LIBGL_SKIPTEXCOPIES=1

  export BOX64_LOG=1
  export BOX64_ALLOWMISSINGLIBS=1
  export BOX64_DLSYM_ERROR=1
  #export SDL_DYNAMIC_API="libSDL2-2.0.so.0"

  # Make sure gl4es libs are on the loader path first
  export LD_LIBRARY_PATH="$GAMEDIR/gl4es:$LD_LIBRARY_PATH:$GAMEDIR/box64/native:/usr/lib/arm-linux-gnueabihf:/usr/lib64:/usr/config/emuelec/lib64"

  # Force native EGL/Mali for SDL KMSDRM (use soname, not absolute path)
  export BOX64_NATIVELIBS="libEGL.so.1:libmali.so.0"
  export BOX64_LD_LIBRARY_PATH="/usr/lib64:$GAMEDIR/box64/native:$GAMEDIR/gamedata/bin64"

  export BOX64_LIBGL="$GAMEDIR/gl4es/libGL.so.1"
  export SDL_VIDEO_GL_DRIVER="$GAMEDIR/gl4es/libGL.so.1"
  export SDL_VIDEO_EGL_DRIVER="libEGL.so.1"
  export BOX64_FORCE_ES=31

  export BOX64_DYNAREC=1
  export SDL_GAMECONTROLLERCONFIG="$sdl_controllerconfig"

  # an llm told me this could work???
  export SENTRY_DSN=""
  export SENTRY_DISABLE=1

  $ESUDO chmod 666 /dev/tty0
  $ESUDO chmod 666 /dev/tty1
  printf "\033c" > /dev/tty0

  # Set executable permissions for sdcards using ext2 or similar.
  chmod +x "$GAMEDIR/box64/box64"
  chmod +x "$GAMEDIR/gamedata/bin64/Chowdren"

  $GPTOKEYB "Chowdren" -c "$GAMEDIR/pepper.gptk" &
  pm_message "Loading, please wait... (might take a while!)"
  $GAMEDIR/box64/box64 bin64/Chowdren

  pm_finish
