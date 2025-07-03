### Spider-Man Web of Shadows

Some info and tools for reversing WoS.

`imhex`:
ImHex patterns for various WoS formats.  
`python`:
Scripts for reading `PCPACK` and `pcapk` files.  

`resource/filename_hashes.json`:
Filename hashes (~90% complete) 
 
`notes/WoSFileStatistics.txt`:
 counts of files from all PCPACK archives
`notes/game_shared.ini`:
 original development options found in the binary. Nearly all disabled in release build.  
`notes/ghidra_slf.txt`:
 offsets of (slf) Script Library Functions in the binary. NOPed functions at end.

### Using unpack scripts

You will need `https://github.com/jd-boyd/python-lzo` to decompress PCPACK files.

Resources are stored in PCPACK files. Assets like meshes, animations, skeletons, textures are stored in PCAPK files inside the PCPACK.
To iterate over files in a PCPACK:
```Python
import pathlib
import pcpack

filename = "path/to/GAME.PCPACK"
buffer = pathlib.Path(filename).read_bytes()
archive = pcpack.PCPACKArchive(buffer)
for f in archive.files:    
    print(f.filename, f.dataSize, f.data[:100])
``` 


Files in a PCAPK can be made up of one or two components.
`createStandaloneFile` merges them together and applies (some) of the patches in the patch table at the end of PCAPK.
```Python
import pathlib
import pcapk

PCAPK_FILE = "path/to/asset.pcapk"
apkf_path = pathlib.Path(PCAPK_FILE)
buffer = apkf_path.read_bytes()
apkf = pcapk.APKFArchive(buffer)
    
for f in apkf.files():
    dirname = apkf_path.parent.stem
    outpath = pathlib.Path('./out', dirname, f"{f.filename}.{f.fileType.lower()}")
    outpath.parent.mkdir(parents=True, exist_ok=True)
            
    outBytes = pcapk.createStandaloneFile(f)

    with outpath.open('wb') as out:
        out.write(outBytes)
``` 




### Repacking

Not yet implemented. More work needs to be done on figuring the file structures of PCAPK, PCPACK and amalga.toc.


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

