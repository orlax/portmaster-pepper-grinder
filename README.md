# Pepper Grinder (Chowdren 64-bit) on Knulli — Current Status not working

This repo documents my attempt to run **Pepper Grinder** on a retro handheld using PortMaster and the Chowdren (64-bit) build (GOG version, DRM-free).

Buy the game here: [Pepper Grinder](https://www.gog.com/en/game/pepper_grinder)

the game was built using construct 2 and exported with Chowdren, very much like Iconoclasts 
this port is based on the existing [iconoclast port](https://portmaster.games/detail.html?name=iconoclasts)

---------

Last Updated Was: Tuesday Jan 27 

I got a launch script that was able to start the game using westonpack and box64, however the process is always kill because of an Out Of Memory Error. 

looking at what the Chowdren executable does I can see it preloads all sounds (and maybe all assets) at the start of the game. 

so I looked into running the game on my SteamDeck with regular x86 linux and start tweaking the game to get RAM usage down, maybe disable audio preloading and other things. 

BUT upon testing how much ram the game takes when running on steam deck I found out that standing on the first level it uses 700-800mb of ram as reported via terminal 
```
watch -n 0.5 "ps -o pid,rss,vsz,cmd -C Chowdren"

#output: 
PID   RSS    VSZ     CMD 
11056 780324 2181380 ./bin64/Chowdren
```
as a comparison I tested the Iconoclast game and that one uses only 300mb during gameplay. 

So my conclussion is that Pepper Grinder uses too much ram to be ran on a 1gb total RAM device, reducing the amount of ram it uses might be possible but that is not something I know how to do. 

so now I know for sure, the game is too heavy as it exists. would need major refinement.
