'''
Created on Mar 2, 2017

Implementation of Huffman Coding algorithm for data compression

@author:  Joey Lupo
'''

from heapq import heappush, heappop, heapify
from collections import defaultdict, namedtuple
from operator import attrgetter
import functools
from bitarray import bitarray

# A tuple containing a symbol and the length of its code in a canonical Huffman tree
# Used in compression and decompression 
CodeLength = namedtuple("CodeLength", 'symbol, length')

        
def compress(src):
    """Public interface for returning huffman encoded source"""  
    codebook = _create_codebook(src)
    encoded_dict = _encode_dict(codebook)   
    compressed_src = bitarray()
    compressed_src.encode(codebook, src)
    num_bits_encoded = len(compressed_src).to_bytes(4,byteorder = "big")
    compressed_src = compressed_src.tobytes()
    
    compressed = bytearray()
    compressed += num_bits_encoded + encoded_dict + compressed_src
    return compressed


def decompress(compressed):
    """Public interface for decoding huffman encoded source file"""   
    #unpacking the header into 3 distinct sections
    num_bits_encoded = int.from_bytes(compressed[:4], byteorder = "big")
    code_lengths = _decode_dict(compressed[4:132])
    coded_src = bitarray()
    coded_src.frombytes(bytes(compressed[132:]))
    coded_src = coded_src[:num_bits_encoded]
    
    codebook = _to_canonical(code_lengths)
    uncompressed_list = coded_src.decode(codebook)
    uncompressed = functools.reduce(lambda x,y: x+y, [b.to_bytes(1, byteorder = "big") for b in uncompressed_list])
    return uncompressed

    
def _create_codebook(src):
    """Return a canonical huffman encoding of the src in a dict mapping symbols to codes""" 
    symb2freq = defaultdict(int)        
    for byte in src:
        symb2freq[byte] += 1
        
    # A named tuple with a weight as the first element, a count element to break ties in 
    # comparisons (needed as workaround for heapq.heapify), and a dictionary of symbols to codes.
    HuffmanNode = namedtuple('HuffmanNode', 'weight, count, symbols')
    # Create a heap out of HuffmanNodes for efficient removal of the smallest elements,
    # i.e. a priority queue
    heap = [HuffmanNode(symb_freq_tuple[1] , count, {symb_freq_tuple[0] : bitarray()}) 
            for count, symb_freq_tuple in enumerate(symb2freq.items())]
    heapify(heap)
    
    # As the loop iterates, the smallest two nodes are removed from the heap and 
    # combined into a parent HuffmanNode that has their combined weight and contains a 
    # dictionary with each of their symbols and corresponding codes. A '0' is prepended
    # to the all the codes contained in the dictionary of the smaller of the two, while
    # a '1' is prepended to all the codes in the dictionary of the other. The loop exits
    # when there is only one HuffmanNode remaining with all of the symbols mapped to codes 
    while len(heap) > 1:
        smallest = heappop(heap)
        next_smallest = heappop(heap)
        for symbol, code in smallest.symbols.items():
            smallest.symbols[symbol] = bitarray('0') + code
        for symbol, code in next_smallest.symbols.items():
            next_smallest.symbols[symbol] = bitarray('1') + code
            
        # Merge the symbols dictionaries of each child node
        smallest.symbols.update(next_smallest.symbols)
        parent_node = HuffmanNode(weight = smallest.weight+next_smallest.weight, count = smallest.count, symbols = smallest.symbols)
        heappush(heap, parent_node)           
        
    codebook = heap[0].symbols
    # Create a list of tuples so that of codes and lengths so that a 
    # canonical Huffman tree can be constructed
    code_lengths = list()
    for symb, code in codebook.items():
        code_lengths.append(CodeLength(symb, len(code)))
    codebook = _to_canonical(code_lengths)
    return codebook


def _to_canonical(code_lengths):
    """Given a list of tuples of CodeLength(symbol, length), return a canonical Huffman encoding"""
    canonical = dict()
    # Sort first by length and then by symbol
    code_lengths = sorted(code_lengths, key = attrgetter('length', 'symbol'))

    current_length = code_lengths[0].length
    current_code_num = 0
    current_code_str = '0' * current_length
    # Store the first symbol as all zeroes 
    canonical[code_lengths[0].symbol] = bitarray(current_code_str)
    
    for code in code_lengths[1:]:
        diff = (code.length - current_length)
        current_length += diff
        current_code_num = (current_code_num + 1) << (diff)      
        # Index out '0b' in resulting string
        bin_num = bin(current_code_num)[2:]
        # Prepend 0's to reach needed length in case of shorter bin representation
        current_code_str = '0' * (code.length - len(bin_num)) + bin_num
        canonical[code.symbol] = bitarray(current_code_str)
        
    return canonical


def _encode_dict(codebook):
    """Compress a codebook into lengths representations for compact header"""  
    compact = bytearray()
    # Code lengths stored as 4 bits, so 2 packed per byte
    for n in range(0, 256, 2):
        try:
            left_code = len(codebook[n])
        except KeyError:
            left_code = 0    
        try:
            right_code = len(codebook[n+1])
        except KeyError:
            right_code = 0         
        compact.append((left_code << 4) | right_code)    
    return compact 


def _decode_dict(encoded_dict):
    """Decode 128 bytes from header into 256 code lengths"""    
    right_length_mask = 0b00001111
    code_lengths = list()
    for n in range(len(encoded_dict)):
        left_symb = n*2 
        left_length = encoded_dict[n] >> 4
        if left_length != 0:
            code_lengths.append(CodeLength(left_symb, left_length))
        
        right_symb = n*2 + 1
        right_length = encoded_dict[n] & right_length_mask
        if right_length != 0:
            code_lengths.append(CodeLength(right_symb, right_length))
        
    return code_lengths    

