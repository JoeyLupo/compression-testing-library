import sys
import queue
import threading
import struct
from wk import WKCompressor
import huffman
import lzma
import bz2

def page_reader(trace):
    with open(trace, 'rb') as f:
        count = 0
        while count < 10:   
            try:
                page = f.read(4104)
                page = page[8:]
                q.put(page)
                count += 1
            except:
                q.put(None)  
                break
        q.put(None)
    return

def compressor(algorithm, wk_compressor = None):
    while True:
        if not q.empty():
            page = q.get()
            if page is None:
                break
            
            if algorithm == "wk":
                compressed = wk_compressor.compress(page)
            elif algorithm == "wk-huffman":
                wk_compressed = wk_compressor.compress(page)
                compressed = huffman.compress(wk_compressed)
            elif algorithm == "lzma":
                compressed = lzma.compress(page)
            elif algorithm == "bzip":
                compressed = bz2.compress(page)
            else:
                print("Please enter one of 'wk', 'wk-huffman', 'lzma', or 'bzip'")
                exit()
            compressed_size = len(compressed)
            #compressed_size_bytes = struct.pack(">I", compressed_size)
            out.write(str(compressed_size) + " ")

if __name__ == '__main__':
    q = queue.Queue()
    #outfile = "compression-ratio.txt"
    #out = open(outfile, "w+")
    out = sys.stdout
    
    trace = sys.argv[1]
    producer = threading.Thread(target= page_reader, args = (trace,))
    
    algorithm = sys.argv[2]
    if "wk" in algorithm:
        wk = WKCompressor(word_size_bytes=int(sys.argv[3]), dict_size= int(sys.argv[4]), num_low_bits=int(sys.argv[5]))
    else:
        wk = None           
    consumer = threading.Thread(target= compressor, args = (algorithm,), kwargs = {'wk_compressor': wk})
    
    producer.start()
    consumer.start()
   
    producer.join()
    consumer.join()
    #out.close()
