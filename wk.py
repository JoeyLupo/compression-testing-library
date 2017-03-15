'''
Created on Mar 2, 2017

Provides class WKCompressor as implementation of WK algorithm

@author:  Joey Lupo
'''
import functools
import math  

class WKCompressor():
    """Simple implementation of WK compression algorithm"""
        
    ZERO = 0
    PARTIAL = 1
    MISS = 2
    HIT = 3
    BITS_PER_BYTE = 8
    PAGE_SIZE_BYTES = 4096
    TAGS_PER_PACKED_BYTE = 4
    HEADER_SIZE_BYTES = 16
        
    def __init__(self, word_size_bytes = 8, packing_word_bytes = 8, dict_size = 16, num_low_bits = 10, debug = False):
        self.DEBUG = debug
        self.WORD_SIZE_IN_BYTES = word_size_bytes
        self.PACKING_WORD_IN_BYTES = packing_word_bytes
        self.DICT_SIZE = dict_size
        num_dict_index_bits = math.log(self.DICT_SIZE, 2)
        if num_dict_index_bits.is_integer(): 
            self.NUM_DICT_INDEX_BITS = int(num_dict_index_bits) 
        else: 
            raise Exception("Dictionary size must be power of 2")
        
        self.NUM_LOW_BITS = num_low_bits
        self.LOW_BIT_MASK = (1 << self.NUM_LOW_BITS) - 1
        self.HIGH_BIT_MASK = ~(self.LOW_BIT_MASK)
     
    def pack(self, unpacked, data_size):
        reps = (self.PACKING_WORD_IN_BYTES * WKCompressor.BITS_PER_BYTE) // data_size   
        packed = list()
        for n in range(0, len(unpacked), reps):
            tmp = unpacked[n] << self.PACKING_WORD_IN_BYTES * WKCompressor.BITS_PER_BYTE - data_size
            for r in range(1, reps): 
                try:
                    tmp |=  unpacked[n + r] << self.PACKING_WORD_IN_BYTES * WKCompressor.BITS_PER_BYTE -(data_size * (r+1)) 
                except IndexError:
                    break
            packed.append(tmp)
        if len(packed) == 0:
            return bytearray()
        packed = functools.reduce(lambda x,y: x+y, [x.to_bytes(self.PACKING_WORD_IN_BYTES, byteorder = "big") for x in packed])

        return packed    

    def unpack(self, packed_tags, data_size):
        unused_bits = (self.PACKING_WORD_IN_BYTES * WKCompressor.BITS_PER_BYTE) % data_size
        reps = (self.PACKING_WORD_IN_BYTES * WKCompressor.BITS_PER_BYTE) // data_size   
        unpacked = list()
        for n in range(0, len(packed_tags), self.PACKING_WORD_IN_BYTES):
            tmp = int.from_bytes(packed_tags[n:n+self.PACKING_WORD_IN_BYTES], byteorder = "big")
            for i in reversed(range(reps)):               
                unpacked.append((tmp >> (data_size*i + unused_bits)) & (-1 + 2**data_size))
            
        return unpacked
        
             
    def compress(self, src_bytes):  
        #convert bytearray to array of words of length determined by parameter to compressor  
        src_words = [int.from_bytes(src_bytes[n:n+self.WORD_SIZE_IN_BYTES], byteorder = "big") for n in range(0, len(src_bytes), self.WORD_SIZE_IN_BYTES)] 

        #our recency dictionary
        lru_queue = list([0])
                
        tags = list()        
        full_words = bytearray()  
        dict_indices = list()
        low_bits = list()
             
        for word in src_words:
            if word == 0:
                tags.append(WKCompressor.ZERO)
                
            elif word in lru_queue:
                tags.append(WKCompressor.HIT)
                hit_index = lru_queue.index(word)
                dict_indices.append(hit_index)
                
                if hit_index != 0:
                    lru_queue.insert(0, lru_queue.pop(hit_index))
                                       
            elif word >> self.NUM_LOW_BITS in [entry >> self.NUM_LOW_BITS for entry in lru_queue]:
                tags.append(WKCompressor.PARTIAL)
                low_bits.append(word & self.LOW_BIT_MASK)
                high_bits = [entry >> self.NUM_LOW_BITS for entry in lru_queue]
                hit_index = high_bits.index(word >> self.NUM_LOW_BITS)
                dict_indices.append(hit_index)
            
                if hit_index != 0:
                    lru_queue.pop(hit_index)
                    lru_queue.insert(0,word)
            else:
                tags.append(WKCompressor.MISS)
                full_words += word.to_bytes(self.WORD_SIZE_IN_BYTES, byteorder = "big")
                if len(lru_queue) != self.DICT_SIZE:
                    lru_queue.insert(0,word)
                else: 
                    lru_queue.pop()
                    lru_queue.insert(0,word)
                
        packed_tags = self.pack(tags, 2)
        packed_dict_indices = self.pack(dict_indices, self.NUM_DICT_INDEX_BITS)
        packed_low_bits = self.pack(low_bits, self.NUM_LOW_BITS)
        
        num_words = len(src_words)   
        dict_indices_offset = 16 + len(packed_tags) + len(full_words)
        low_bits_offset = dict_indices_offset + len(packed_dict_indices)
        end_of_compressed_offset = low_bits_offset + len(packed_low_bits)
        
        header = functools.reduce(lambda x,y: x+y, [x.to_bytes(4, byteorder = "big") for x in [num_words,dict_indices_offset,low_bits_offset,end_of_compressed_offset]])
        
        compressed_page = bytearray()
        compressed_page += header + packed_tags + full_words + packed_dict_indices + packed_low_bits
        
        if self.DEBUG: 
            print("HEADER CONTENTS:\tWord 1: ",hex(int.from_bytes(header[:4], byteorder = "big")),"\t\tWord 2: ", hex(int.from_bytes(header[4:8], byteorder = "big")), 
                  "\t\tWord 3: ", hex(int.from_bytes(header[8:12], byteorder = "big")), "\t\tWord 4: ", hex(int.from_bytes(header[12:16], byteorder = "big")))
            print("LRU QUEUE CONTENTS:")
            for index, value in enumerate(lru_queue):
                print("Index = ", index, "\tValue = ", hex(value), "\tBinary = ", bin(value), "\tLow bits = ", bin(value & 0x3ff))
            
            low_count = 0
            index_count = 0
            for num, t in enumerate(tags[:10]): 
                print("Word number ", num, "=", hex(src_words[num]), "\t\tTag = ", t, end = "\t")
                if t == 0:
                    print("ZERO")
                elif t == 1:
                    print("PARTIAL","\tDict Index = ", dict_indices[index_count], "\tLow Bits = ", hex(low_bits[low_count]))
                    low_count += 1
                    index_count += 1
                elif t == 2:
                    print("MISS")
                else: 
                    print("FULL MATCH", "\tDict Index = ", dict_indices[index_count])
                    index_count += 1
            
            print("\n\n=================IN BYTES=================")
            print("Starting length:\t\t\t", len(src_bytes))
            print("End compressed length:\t\t\t", len(compressed_page))
            print("Achieved ratio:\t\t\t\t", "{0:.2f}".format(len(compressed_page) / len(src_bytes)))
            print("Length of Header:\t\t\t", len(header))
            print("Length of Tags Area:\t\t\t" , len(packed_tags))
            print("Length of Full Words Area:\t\t", len(full_words))
            print("Length of Dictionary Indices Area:\t", len(packed_dict_indices))
            print("Length of Low Bits Area:\t\t", len(packed_low_bits))
            #END DEBUG 
              
        return compressed_page
    
    def decompress(self, compressed_page):
        num_words = int.from_bytes(compressed_page[:4], byteorder = "big")
        dict_indices_offset = int.from_bytes(compressed_page[4:8], byteorder = "big")
        low_bits_offset = int.from_bytes(compressed_page[8:12], byteorder = "big")
        end_of_compressed_offset = int.from_bytes(compressed_page[12:16], byteorder = "big")      
        tags_area_size = (WKCompressor.PAGE_SIZE_BYTES // self.WORD_SIZE_IN_BYTES) // WKCompressor.TAGS_PER_PACKED_BYTE
        
        packed_tags = compressed_page[WKCompressor.HEADER_SIZE_BYTES : WKCompressor.HEADER_SIZE_BYTES + tags_area_size]
        full_words = compressed_page[WKCompressor.HEADER_SIZE_BYTES + tags_area_size: dict_indices_offset]
        packed_dict_indices = compressed_page[dict_indices_offset:low_bits_offset]
        packed_low_bits = compressed_page[low_bits_offset:end_of_compressed_offset]

        tags = self.unpack(packed_tags, 2)
        dict_indices = self.unpack(packed_dict_indices, self.NUM_DICT_INDEX_BITS)
        low_bits = self.unpack(packed_low_bits, self.NUM_LOW_BITS)
        
        uncompressed_page = bytearray()
  
        lru_queue = list([0])
        full_words_count = 0
        dict_count = 0
        low_bits_count = 0
        
        for tag in tags:
            if tag == WKCompressor.ZERO:
                uncompressed_page += bytearray(self.WORD_SIZE_IN_BYTES)
                
            elif tag == WKCompressor.PARTIAL:
                hit_index = dict_indices[dict_count]
                dict_word = lru_queue[hit_index]
                dict_count += 1
                word_low_bits = low_bits[low_bits_count]
                low_bits_count += 1
                
                word_high_bits = dict_word & self.HIGH_BIT_MASK
                word = word_high_bits | word_low_bits
                word_bytes = word.to_bytes(self.WORD_SIZE_IN_BYTES,byteorder = "big")
                
                if hit_index != 0:
                    lru_queue.pop(hit_index)
                    lru_queue.insert(0,word)
                    
                uncompressed_page += word_bytes

            elif tag == WKCompressor.MISS:
                word_bytes = full_words[full_words_count:full_words_count+self.WORD_SIZE_IN_BYTES]
                word = int.from_bytes(word_bytes, byteorder ="big")
                full_words_count += self.WORD_SIZE_IN_BYTES
                if len(lru_queue) != self.DICT_SIZE:
                    lru_queue.insert(0,word)
                else: 
                    lru_queue.pop()
                    lru_queue.insert(0,word)
                uncompressed_page += word_bytes
                    
            elif tag == WKCompressor.HIT: 
                hit_index = dict_indices[dict_count]
                dict_count += 1
                dict_word = lru_queue[hit_index]
                dict_word_bytes = dict_word.to_bytes(self.WORD_SIZE_IN_BYTES, byteorder = "big")  
                if hit_index != 0:
                    lru_queue.insert(0, lru_queue.pop(hit_index))                    
                uncompressed_page += dict_word_bytes           
        
        if self.DEBUG:
            print("\n\n================In decompress()==================")
            print("Num words = ", num_words)
            print("Dict Indices offset = ", dict_indices_offset)
            print("Low Bits offset = ", low_bits_offset)
            print("End of page offset = ", end_of_compressed_offset)

        return uncompressed_page
    
    @staticmethod
    def get_lru_queue_histogram(compressor, compressed_page):
        dict_indices_offset = int.from_bytes(compressed_page[4:8], byteorder = "big")
        low_bits_offset = int.from_bytes(compressed_page[8:12], byteorder = "big")
        packed_dict_indices = compressed_page[dict_indices_offset:low_bits_offset]
        dict_indices = compressor.unpack(packed_dict_indices, compressor.NUM_DICT_INDEX_BITS)
        
        histogram = [0] * compressor.DICT_SIZE
        for index in dict_indices:
            histogram[index] += 1
        
        return histogram
    
    @staticmethod
    def get_dict(compressor, compressed_page):
        dict_indices_offset = int.from_bytes(compressed_page[4:8], byteorder = "big")
        low_bits_offset = int.from_bytes(compressed_page[8:12], byteorder = "big")
        packed_dict_indices = compressed_page[dict_indices_offset:low_bits_offset]
        return packed_dict_indices