# Pepper Grinder (Chowdren 64-bit) on Knulli - Current Status

This repo documents my attempt to run the game Pepper Grinder with PortMasters on a retro handheld.

[Pepper Grinder](https://www.gog.com/en/game/pepper_grinder)

the game was built using construct 2 and exported with Chowdren, very much like Iconoclasts 
this port is based on the existing [iconoclast port](https://portmaster.games/detail.html?name=iconoclasts)


on Knulli (RG40XX-V). I am sharing the current state so others can help.

## how to use whats already here? 

put this repo on your device and copy the game files to the "gamedata" folder 
gamefiles should be extracted from the GOG version of the game as that one is DRM-free (no steam stuff) 
then you can attempt to execute run.shs


## The current status 
with the current configuration of the run.sh file and a stub library for "libsentry" I created the game 
seems to have a "correct initialization" however it hangs/kills the processs very early. you can find a 
full log in the full_logs.txt file. 

the last few lines of the logs are 
```
20514|0x2cb3689: Calling strlen("sentry_init: ") => return 0xD
20514|0x2cb364f: Calling fwrite(0x7F8046D1A1, 0xD, 0x1, ...) =>sentry_init:  return 0x1
20514|0x2cb3657: Calling fflush(0x7F806C25F0, 0xD, 0x1, ...) => return 0x0
20514|0x2cb3c2e: Calling fwrite(0x7F8046D1A1, 0x1, 0x1, ...) =>0 return 0x1
20514|0x2cb3c36: Calling fflush(0x7F806C25F0, 0x1, 0x1, ...) => return 0x0
20514|0x2cb3b32: Calling fputc(0xA, 0x7F806C25F0, 0x1, ...) =>
 return 0xA
20514|0x2cae9b9: Calling fflush(0x7F806C25F0, 0x7F806C25F0, 0x1, ...) => return 0x0
20514|0x2cae9da: Calling free(0x56661B80, 0x7F806C25F0, 0x1, ...) => return 0x0
20514|0x2caecf7: Calling strlen("CHOWDREN_BACKEND_PICKER=GOG") => return 0x1B
20514|0x2caef16: Calling strncmp(0x7F8046D239, 0x1024F41, 0x3, ...) => return 0xFFFFFF9F
20514|0x2caef71: Calling strncmp(0x7F8046D239, 0x102FA4E, 0x3, ...) => return 0x2
20514|0x2cb3689: Calling strlen("clearing dyntimers: ") => return 0x14
20514|0x2cb364f: Calling fwrite(0x7F8046D251, 0x14, 0x1, ...) =>clearing dyntimers:  return 0x1
20514|0x2cb3657: Calling fflush(0x7F806C25F0, 0x14, 0x1, ...) => return 0x0
20514|0x2cb3ece: Calling fwrite(0x7F8046D251, 0x1, 0x1, ...) =>0 return 0x1
20514|0x2cb3ed6: Calling fflush(0x7F806C25F0, 0x1, 0x1, ...) => return 0x0
20514|0x2cb3b32: Calling fputc(0xA, 0x7F806C25F0, 0x1, ...) =>
 return 0xA
20514|0x2cfbc46: Calling fflush(0x7F806C25F0, 0x7F806C25F0, 0x1, ...) => return 0x0
20514|0x2cb3689: Calling strlen("reset
") => return 0x6
20514|0x2cb364f: Calling fwrite(0x7F8046D251, 0x6, 0x1, ...) =>reset
 return 0x1
20514|0x2cb3657: Calling fflush(0x7F806C25F0, 0x6, 0x1, ...) => return 0x0
20514|0x2cb3689: Calling strlen("locale lang: ") => return 0xD
20514|0x2cb364f: Calling fwrite(0x7F8046D271, 0xD, 0x1, ...) =>locale lang:  return 0x1
20514|0x2cb3657: Calling fflush(0x7F806C25F0, 0xD, 0x1, ...) => return 0x0
20514|0x4919b2c: Calling pthread_mutex_lock(0x6350408, 0xD, 0x1, ...) => return 0x0
20514|0x4919b9f: Calling syscall(186, 0xd, 0x1....) =>[BOX64] 20514| 0x300508b3: Calling libc syscall 0xBA (186) 0xd 0x1 (nil) 0x7f8046d279 0x1050152
 return 0x5022
20514|0x4919bb6: Calling pthread_mutex_unlock(0x6350408, 0xD, 0x1, ...) => return 0x0
20514|0x2ca4319: Calling strlen("English") => return 0x7
20514|0x2c9f44f: Calling __cxa_atexit(0x2CA41D0, 0x4C4AF80, 0x1000000, ...) => return 0x0
20514|0x4919c5b: Calling pthread_mutex_lock(0x6350408, 0x4C4AF80, 0x1000000, ...) => return 0x0
20514|0x4919c73: Calling pthread_mutex_unlock(0x6350408, 0x4C4AF80, 0x1000000, ...) => return 0x0
20514|0x2c9f27d: Calling getenv("LANG") => return 0x7FFE9D1902(es_ES.UTF-8)
20514|0x2ca41f9: Calling strlen("Spanish") => return 0x7
20514|0x2cb35e4: Calling fwrite(0x4C4AF81, 0x7, 0x1, ...) =>Spanish return 0x1
20514|0x2c9f2a7: Calling fflush(0x7F806C25F0, 0x7, 0x1, ...) => return 0x0
20514|0x2cb3b32: Calling fputc(0xA, 0x7F806C25F0, 0x1, ...) =>
 return 0xA
20514|0x2c9f2b3: Calling fflush(0x7F806C25F0, 0x7F806C25F0, 0x1, ...) => return 0x0
20514|0x2c9f2c9: Calling SDL_SetHint(0x1030F95, 0x1021640, 0x1, ...) => return 0x1
20514|0x2c9f2da: Calling setenv("SDL_VIDEO_X11_WMCLASS", "PepperGrinder", 0) => return 0x0
20514|0x2c9f2eb: Calling setenv("SDL_VIDEO_WAYLAND_WMCLASS", "PepperGrinder", 0) => return 0x0
20514|0x2c9f301: Calling SDL_SetHint(0x102F88E, 0x10355A5, 0x0, ...) => return 0x1
20514|0x2c9f317: Calling SDL_SetHint(0x10310BD, 0x1035078, 0x0, ...) => return 0x1
20514|0x2c9f326: Calling SDL_SetHint(0x103109E, 0x1035078, 0x0, ...) => return 0x1
20514|0x2c9f335: Calling SDL_SetHint(0x102FB11, 0x10355A5, 0x0, ...) => return 0x1
20514|0x2c9f344: Calling SDL_SetHint(0x102F8A5, 0x1035078, 0x0, ...) => return 0x1
20514|0x2c9f353: Calling SDL_SetHint(0x1030892, 0x10355A5, 0x0, ...) => return 0x1
20514|0x2c9f35d: Calling SDL_Init(0x100020, 0x10355A5, 0x0, ...) => return 0x0
20514|0x2c9f366: Calling SDL_IsTextInputActive(0x100020, 0x10355A5, 0x0, ...) => return 0x1
20514|0x2c9f36f: Calling SDL_StopTextInput(0x100020, 0x10355A5, 0x0, ...) => return 0x1
20514|0x2c9f37b: Calling SDL_EventState(0x400, 0x0, 0x0, ...) => return 0x1
20514|0x2c9f380: Calling SDL_GetPerformanceCounter(0x400, 0x0, 0x0, ...) => return 0xD6867DCEF8
20514|0x2ca1d46: Calling SDL_GetHint(0x102FCD2, 0x4C4AA10, 0x0, ...) => return 0x0
20514|0x2ca1d46: Calling SDL_GetHint(0x102F627, 0x4C4AA28, 0x0, ...) => return 0x0
20514|0x2c9f4a8: Calling SDL_SetHintWithPriority(0x102F627, 0x1051899, 0x2, ...) => return 0x1
20514|0x2c9f4b8: Calling SDL_SetHintWithPriority(0x102FCD2, 0x1051899, 0x2, ...) => return 0x1
20514|0x2c9f4ce: Calling SDL_RWFromFile(0x101C55B, 0x102E6C7, 0x2, ...) => return 0x5666EE00
20514|0x2c9f4db: Calling SDL_GameControllerAddMappingsFromRW(0x5666EE00, 0x1, 0x2, ...) => return 0x255
20514|0x2c9f4e5: Calling SDL_InitSubSystem(0x2000, 0x1, 0x2, ...) => return 0x0
20514|0x2c9f4f4: Calling SDL_RWFromFile(0x101C47A, 0x102E6C7, 0x2, ...) => return 0x0
20514|0x2c9f501: Calling SDL_GameControllerAddMappingsFromRW(0x0, 0x1, 0x2, ...) => return 0xFFFFFFFF
20514|0x2c9f506: Calling SDL_NumJoysticks(0x0, 0x1, 0x2, ...) => return 0x1
20514|0x2c9fc03: Calling SDL_IsGameController(0x0, 0x1, 0x2, ...) => return 0x1
20514|0x2c9fc0e: Calling SDL_GameControllerOpen(0x0, 0x1, 0x2, ...) => return 0x566CE620
20514|0x2c9fc1e: Calling SDL_GameControllerGetJoystick(0x566CE620, 0x1, 0x2, ...) => return 0x566CE920
20514|0x2c9fcae: Calling SDL_JoystickInstanceID(0x566CE920, 0x1, 0x2, ...) => return 0x0
20514|0x4931278: Calling malloc(0x100, 0x1, 0x2, ...) => return 0x566D1270
20514|0x2ca4496: Calling SDL_JoystickName(0x566CE920, 0x566CE620, 0x566CE920, ...) => return 0x56690C10
20514|0x2ca41f9: Calling strlen("Anbernic RG40XX-H Controller") => return 0x1C
20514|0x2ca44a8: Calling SDL_JoystickGetDeviceGUID(0x0, 0x56690C10, 0x72, ...) => return 0x100000019

```

## my current suspicions are: 
- the game is failing to connect to a video backend correctly and it just so happens to be right before the controllers are initialized.
- there really is a problem with the controllers.


## some other notes:
- If I execute run.sh with with the dynamic sdl line commented the game actually runs the pre-load of assets but then we get a message that says:

```
Could not open window: eglQueryDevicesEXT is missing
```
my current understandment is that we NEED to use the dynamic SDL library so that this error does not happen. 
- If I put lines to force an specific video driver kmsdrm/fbcon/wayland I get error messages saying they are not available.

## My next Ideas?
- look at creating a script that will run this using Westonpack stuff.
- look at how other ports that use box64 are configured and see if there is something there I can learn from. 

## Do I think this should be possible? 
Yes I think the game should be able to run. 
