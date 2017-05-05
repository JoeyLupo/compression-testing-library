'''
Created on Mar 2, 2017

Provides class WKCompressor as implementation of WK algorithm

@author:  Joey Lupo
'''

import functools
import math  

ZERO = 0
PARTIAL = 1
MISS = 2
HIT = 3
BITS_PER_BYTE = 8
PAGE_SIZE_BYTES = 4096
TAGS_PER_PACKED_BYTE = 4
HEADER_SIZE_BYTES = 16


class WKCompressor():
    """Simple implementation of WK compression algorithm"""        
    
    def __init__(self, word_size_bytes = 8, packing_word_bytes = 8, 
                 dict_size = 16, num_low_bits = 10, debug = False):
        self.DEBUG = debug
        self._word_size_in_bytes = word_size_bytes
        self._packing_word_in_bytes = packing_word_bytes
        self._dict_size = dict_size
        num_dict_index_bits = math.log(self._dict_size, 2)
        if num_dict_index_bits.is_integer(): 
            self._num_dict_index_bits = int(num_dict_index_bits) 
        else: 
            raise ValueError("Dictionary size must be a power of 2")
        
        self._num_low_bits = num_low_bits
        self._low_bit_mask = (1 << self._num_low_bits) - 1
        self._high_bit_mask = ~(self._low_bit_mask)
     
    def _pack(self, unpacked, data_size):
        """Pack data from a list into bytes"""
        reps = (self._packing_word_in_bytes * BITS_PER_BYTE) // data_size   
        packed = list()      
        for n in range(0, len(unpacked), reps):
            shift = self._packing_word_in_bytes * BITS_PER_BYTE - data_size
            tmp = unpacked[n] << shift
            for r in range(1, reps): 
                try:
                    tmp |=  unpacked[n + r] <<  (shift - (data_size * r))
                except IndexError:
                    break
            packed.append(tmp)
        if len(packed) == 0:
            return bytearray()
        
        # Convert each element of the packed list into bytes and then use 
        # the reduce function to add the elements into a single bytes object
        packed_bytes_list = [x.to_bytes(self._packing_word_in_bytes, byteorder = "big") for x in packed]
        packed = functools.reduce(lambda x,y: x+y, packed_bytes_list)
        return packed    

    def _unpack(self, packed_tags, data_size):
        """Extract and return a list of data packed into bytes"""
        unused_bits = (self._packing_word_in_bytes * BITS_PER_BYTE) % data_size
        reps = (self._packing_word_in_bytes * BITS_PER_BYTE) // data_size   
        unpacked = list()
        for n in range(0, len(packed_tags), self._packing_word_in_bytes):
            tmp = int.from_bytes(packed_tags[n:n+self._packing_word_in_bytes], byteorder = "big")
            for i in reversed(range(reps)):               
                unpacked.append((tmp >> (data_size*i + unused_bits)) & (-1 + 2**data_size))
            
        return unpacked
        
             
    def compress(self, src_bytes):  
        """Compress a bytes-like object using the WK algorithm"""
        # Convert given bytes-like object to an array of words
        src_words = [int.from_bytes(src_bytes[n : n+self._word_size_in_bytes], byteorder = "big") 
                     for n in range(0, len(src_bytes), self._word_size_in_bytes)] 

        # Instantiate data structures to hold the elements for compression.
        # Full words are written directly to the compressed page so are 
        # stored in a bytearray. Others are added to lists where they 
        # are sent to the _pack() function to be packed into bytes.
        lru_queue = list([0])        
        tags = list()        
        full_words = bytearray()  
        dict_indices = list()
        low_bits = list()
        
        # Start the loop through the uncompressed page recording tags, 
        # dict indices, full words, or low bits for each word    
        for word in src_words:
            if word == 0:
                tags.append(ZERO)
                
            elif word in lru_queue:
                tags.append(HIT)
                hit_index = lru_queue.index(word)
                dict_indices.append(hit_index)
                
                if hit_index != 0:
                    lru_queue.insert(0, lru_queue.pop(hit_index))
                                       
            elif word >> self._num_low_bits in [entry >> self._num_low_bits for entry in lru_queue]:
                tags.append(PARTIAL)
                low_bits.append(word & self._low_bit_mask)
                # Create a temporary list that matches the LRU queue but only 
                # contains the high bits of each number for easy comparison
                high_bits = [entry >> self._num_low_bits for entry in lru_queue]
                hit_index = high_bits.index(word >> self._num_low_bits)
                dict_indices.append(hit_index)
                
                # Move the dictionary entry to the front of the queue and replace with new low bits
                if hit_index != 0:
                    lru_queue.pop(hit_index)
                    lru_queue.insert(0,word)
            else:
                tags.append(MISS)
                full_words += word.to_bytes(self._word_size_in_bytes, byteorder = "big")
                if len(lru_queue) != self._dict_size:
                    lru_queue.insert(0,word)
                else: 
                    lru_queue.pop()
                    lru_queue.insert(0,word)
         
        # Pack the compression data compactly into bytes       
        packed_tags = self._pack(tags, 2)
        packed_dict_indices = self._pack(dict_indices, self._num_dict_index_bits)
        packed_low_bits = self._pack(low_bits, self._num_low_bits)
        
        # Create the header section
        num_words = len(src_words)   
        dict_indices_offset = HEADER_SIZE_BYTES + len(packed_tags) + len(full_words)
        low_bits_offset = dict_indices_offset + len(packed_dict_indices)
        end_of_compressed_offset = low_bits_offset + len(packed_low_bits)
        header_list = [num_words, dict_indices_offset, low_bits_offset, end_of_compressed_offset]
        header = functools.reduce(lambda x,y: x+y, [x.to_bytes(4, byteorder = "big") for x in header_list])
        
        # Construct the final compressed output 
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
        """Decompress a bytes-like object compressed by the WK algorithm"""
        # Read in the from the header to determine metadata about the compressed page
        num_words = int.from_bytes(compressed_page[:4], byteorder = "big")
        dict_indices_offset = int.from_bytes(compressed_page[4:8], byteorder = "big")
        low_bits_offset = int.from_bytes(compressed_page[8:12], byteorder = "big")
        end_of_compressed_offset = int.from_bytes(compressed_page[12:16], byteorder = "big")      
        tags_area_size = math.ceil(num_words / (TAGS_PER_PACKED_BYTE * self._packing_word_in_bytes)) * self._packing_word_in_bytes
        
        # Break down the compressed page into its distinct sections
        packed_tags = compressed_page[HEADER_SIZE_BYTES : HEADER_SIZE_BYTES+tags_area_size]
        full_words = compressed_page[HEADER_SIZE_BYTES+tags_area_size : dict_indices_offset]
        packed_dict_indices = compressed_page[dict_indices_offset : low_bits_offset]
        packed_low_bits = compressed_page[low_bits_offset : end_of_compressed_offset]

        # Unpack data back into list form 
        tags = self._unpack(packed_tags, 2)
        dict_indices = self._unpack(packed_dict_indices, self._num_dict_index_bits)
        low_bits = self._unpack(packed_low_bits, self._num_low_bits)
             
        # Create the recency queue and counters that will be used as indices
        # into the relevant lists.
        lru_queue = list([0])
        full_words_count = 0
        dict_count = 0
        low_bits_count = 0
        
        uncompressed_page = bytearray()    
        for n in range(num_words):
            tag = tags[n]
            if tag == ZERO:
                uncompressed_page += bytearray(self._word_size_in_bytes)
                
            elif tag == PARTIAL:
                hit_index = dict_indices[dict_count]
                dict_word = lru_queue[hit_index]
                dict_count += 1
                word_low_bits = low_bits[low_bits_count]
                low_bits_count += 1
                
                word_high_bits = dict_word & self._high_bit_mask
                word = word_high_bits | word_low_bits
                word_bytes = word.to_bytes(self._word_size_in_bytes,byteorder = "big")
                
                if hit_index != 0:
                    lru_queue.pop(hit_index)
                    lru_queue.insert(0,word)
                    
                uncompressed_page += word_bytes

            elif tag == MISS:
                word_bytes = full_words[full_words_count : full_words_count+self._word_size_in_bytes]
                word = int.from_bytes(word_bytes, byteorder ="big")
                full_words_count += self._word_size_in_bytes
                if len(lru_queue) != self._dict_size:
                    lru_queue.insert(0,word)
                else: 
                    lru_queue.pop()
                    lru_queue.insert(0,word)
                uncompressed_page += word_bytes
                    
            elif tag == HIT: 
                hit_index = dict_indices[dict_count]
                dict_count += 1
                dict_word = lru_queue[hit_index]
                dict_word_bytes = dict_word.to_bytes(self._word_size_in_bytes, byteorder = "big")  
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
    def create_lru_queue_histogram(compressor, compressed_page):
        """Create a histogram of dictionary index hits"""
        dict_indices_offset = int.from_bytes(compressed_page[4:8], byteorder = "big")
        low_bits_offset = int.from_bytes(compressed_page[8:12], byteorder = "big")
        packed_dict_indices = compressed_page[dict_indices_offset : low_bits_offset]
        dict_indices = compressor._unpack(packed_dict_indices, compressor._num_dict_index_bits)
        
        histogram = [0] * compressor._dict_size
        for index in dict_indices:
            histogram[index] += 1
        
        return histogram
    
    @staticmethod
    def get_lru_queue(compressor, compressed_page):
        dict_indices_offset = int.from_bytes(compressed_page[4:8], byteorder = "big")
        low_bits_offset = int.from_bytes(compressed_page[8:12], byteorder = "big")
        packed_dict_indices = compressed_page[dict_indices_offset : low_bits_offset]
        return packed_dict_indices

if __name__ == "__main__":
    pass