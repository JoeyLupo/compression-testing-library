import os
import sys
import subprocess

trace = sys.argv[1]
script = "compress-one.sh"
base_dir = os.getcwd()
results_base_dir = os.path.join(base_dir, "results")

cmd_file = "compress.cmd"
f = open(cmd_file, 'w+')
f.write("universe = vanilla\n")
f.write("notification = never\n")
f.write("getenv = true\n")
f.write("initialdir = " + base_dir + "\n")
f.write("priority = 5\n")
f.write("executable = " + script + "\n")
f.write("\n")

for word_size_bits in [32,64]:
    for dict_size in [2**n for n in range(1,11)]:
        for low_bits in range(4,17):
            for algorithm in ["wk", "wk-huffman"]:
                results_dir = os.path.join(results_base_dir, algorithm, str(word_size_bits), str(dict_size), str(low_bits))
                if not os.path.exists(results_dir):
                    os.makedirs(results_dir, mode = 755)
                
                f.write("log = " + os.path.join(results_dir, "log.txt\n"))
                f.write("output = " + os.path.join(results_dir, "out.txt\n"))
                f.write("error = " + os.path.join(results_dir, "err.txt\n"))
                f.write("arguments = " + trace + " " + algorithm + " " + str(word_size_bits//8) + " " + str(dict_size) + " " + str(low_bits) +"\n")
                f.write("queue\n\n")  
                
results_lzma = os.path.join(results_base_dir, "lzma")
if not os.path.exists(results_lzma):
    os.makedirs(results_lzma, mode = 755)
f.write("log = " + os.path.join(results_lzma, "log.txt\n"))
f.write("output = " + os.path.join(results_lzma, "out.txt\n"))
f.write("error = " + os.path.join(results_lzma, "err.txt\n"))
f.write("arguments = " + trace + " lzma\n")
f.write("queue\n\n") 

results_bzip = os.path.join(results_base_dir, "bzip")
if not os.path.exists(results_bzip):
    os.makedirs(results_bzip, mode = 755)
f.write("log = " + os.path.join(results_bzip, "log.txt\n"))
f.write("output = " + os.path.join(results_bzip, "out.txt\n"))
f.write("error = " + os.path.join(results_bzip, "err.txt\n"))
f.write("arguments = " + trace + " bzip\n")
f.write("queue\n\n") 

f.close()

subprocess.run(["chmod","755", "results", "-R"])
subprocess.run(["condor_submit",os.path.join(base_dir, cmd_file)])
                