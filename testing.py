'''
Created on Mar 5, 2017

@author: Joey Lupo
'''
from wk import WKCompressor
import huffman
import random
import lzma, zlib, bz2
from pip.commands.search import print_results

def main():    
    patterns = [0x61083282abedbf10, 0xcccccccc55555555, 0x1234abcdf5ba03e7, 0x1234abcdf5ba0132, 0]
    random.seed(7)
    src = bytearray()
    src32 = bytearray()
    src3 = bytearray()
    for _ in range(512):
        src += random.choice(patterns).to_bytes(8, byteorder = "big")
      
    for i in range(1024):
        #num = (-1 - i) + 2**32
        num = 2*i
        src32 += num.to_bytes(4, byteorder = "big")
     
    for _ in range(1024):
        src3 += random.randint(0,1024).to_bytes(4, byteorder = "big")
    
    src64 = bytearray()
    for i in range(512):
        #num =  (- 1 - i) + 2**64
        num = random.randint(1,10000000)
        src64 += num.to_bytes(8, byteorder = "big")
     
    src = src64         
    compressor = WKCompressor(word_size_bytes= 4, dict_size=256, num_low_bits= 10, debug = False)
    
    wk_compressed = compressor.compress(src)    
    wk_uncompressed = compressor.decompress(wk_compressed)
    
    wk_huffman_encoded = huffman.compress(wk_compressed)
    wk_huffman_decoded  = huffman.decompress(wk_huffman_encoded)
    wk_huffman_uncompressed = compressor.decompress(wk_huffman_decoded)
    
    lz_compressed = lzma.compress(src)
    lz_uncompressed = lzma.decompress(lz_compressed)
    
    zlib_compressed = zlib.compress(src, 9)
    zlib_uncompressed = zlib.decompress(zlib_compressed)
    
    bz_compressed = bz2.compress(src)
    bz_uncompressed = bz2.decompress(bz_compressed)
    
    print("LRU Histogram: ", WKCompressor.get_lru_queue_histogram(compressor, wk_compressed))
    indices = WKCompressor.get_dict(compressor, wk_compressed)
    print(len(indices))
    
    print_results("WK", src, wk_compressed, wk_uncompressed)
    print_results("WK Huffman", src, wk_huffman_encoded, wk_huffman_uncompressed)
    print_results("lzma", src, lz_compressed, lz_uncompressed)
    print_results("zlib", src, zlib_compressed, zlib_uncompressed)
    print_results("bzip2", src, bz_compressed, bz_uncompressed)

def print_results(algorithm, src, compressed, uncompressed):
    print("======================",algorithm,"Algorithm ================================")
    print("Source page equals compressed/decompressed page? ", uncompressed == src)
    print("Original Length: ", len(src), "bytes")
    print("Compressed Length of", algorithm,":", len(compressed), "bytes")
    print("Achieved wk ratio by", algorithm, ":", "{0:.2f}".format(len(compressed) / len(src)))
    print()   
    
if __name__ == "__main__":
    main()