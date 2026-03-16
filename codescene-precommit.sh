#! /bin/bash -e

if [ -n "$CS_ACCESS_TOKEN" ]; then 
    cs delta --git-hook --staged
else    
    run-codescene.sh delta --git-hook --staged
fi    
