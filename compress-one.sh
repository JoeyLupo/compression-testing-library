#! /bin/bash 

args=($@)
file=${args[0]}
params=("${args[@]:1}")
pipe="pipe"
for arg in "${params[@]}"
do
	pipe+="-$arg"
done

mkfifo "$pipe"
args[0]="$pipe"
unxz < "$file" > "$pipe" &

python3 cluster_tester.py ${args[@]} 

rm "$pipe"