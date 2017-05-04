#! /bin/bash 

args=($@)
file=${args[0]}
mkfifo pipe
args[0]="pipe"
unxz < $file > pipe &

python3 cluster_tester.py ${args[@]} 

rm pipe