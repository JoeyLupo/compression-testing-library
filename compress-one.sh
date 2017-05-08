#! /bin/bash 

args=($@)
file=${args[0]}
params=("${args[@]:1}")
pipe="/tmp/pipe"
for arg in "${params[@]}"
do
	pipe+="-$arg"
done

mkfifo "$pipe"
unxz < "$file" > "$pipe" &
args[0]="$pipe"
python3 cluster_tester.py "${args[@]}" 

rm "$pipe"