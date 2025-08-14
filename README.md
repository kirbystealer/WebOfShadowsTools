### Spider-Man Web of Shadows

Some info and tools for reversing WoS.

Resources are stored in PCPACK files. Assets like meshes, animations, skeletons, textures are stored in PCAPK files inside the PCPACK.

`imhex`:
ImHex patterns for various WoS formats.  
`python`:
Python tools for reading `PCPACK` and `pcapk` files.  

`python/resource/filename_hashes.json`:
Filename hashes (~95% complete) 
 
`notes/WoSFileStatistics.txt`:
 counts of files from all PCPACK archives
`notes/game_shared.ini`:
 original development options found in the binary. Nearly all disabled in release build.  
`notes/ghidra_slf.txt`:
 offsets of (slf) Script Library Functions in the binary. NOPed functions at end.


#### Misc

Spider-Man Web of Shadows uses Treyarch NGL as a game engine.


| Treyarch NGL  |            | Year | Platforms        |
|----------|------------|------|------------------|
| v3.1.0-pre  |    Spider-Man Web of Shadows          | 2008 | PS3, XBOX360, PC (Windows)         |
| v2.5.1-7971   |      Ultimate Spider-Man     <br>    | 2005 | GameCube, PlayStation 2, Xbox, PC (Windows) |
| v1.7.5x   |      Kelly Slater's Pro Surfer        | 2002 | GameCube, PlayStation 2, Xbox |

#### See Also

##### Ultimate Spider-Man (v2.5.1)
- Open Engine recreation at: https://gitlab.com/MrMartinIden/openusm
- Debug Menu addon: https://github.com/krystalgamer/usm-debug-menu

##### Kelly Slater's Pro Surfer (v1.7.5)
- Source available at: https://github.com/historicalsource/kelly-slaters-pro-surfer

