#! /bin/bash

ECHO=

if [[ "$1" == "--dry-run" ]]; then
    ECHO=echo
fi
for dotDir in $(cd dotfiles && ls) ; do 
    echo "$dotDir"
    actualDir="dotDir/$dotDir"
    targetDir="$HOME/.${dotDir}"
    echo "$actualDir -> $targetDir"

    find "$targetDir" -type l | while read -r link; do
        target="$(readlink "$link")"
        # Resolve relative symlinks
        if [[ "$target" != /* ]]; then
            target="$(dirname "$link")/$target"
        fi
        if [ ! -e "$target" ]; then
            echo "Removing broken symlink: $link"
            $ECHO rm "$link"
        fi
    done

    find "dotfiles/$dotDir" -type f | while read -r file; do
        relPath="${file#dotfiles/$dotDir/}"
        targetFile="$targetDir/$relPath"
        targetFileDir="$(dirname "$targetFile")"
        if [ ! -d "$targetFileDir" ]; then
            $ECHO mkdir -p "$targetFileDir" 
        fi
        if [ -e "$targetFile" ]; then
            if [ -L "$targetFile" ] && [ "$(readlink "$targetFile")" = "$(pwd)/$file" ]; then
            # Already linked correctly, do nothing
            continue
            else
            echo "Error: $targetFile exists and is not a symlink to $(pwd)/$file"
            exit 1
            fi
        fi
        $ECHO ln -s "$(pwd)/$file" "$targetFile"
    done
done
