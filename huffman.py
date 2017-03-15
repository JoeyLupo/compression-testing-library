'''
Created on Mar 2, 2017

Implementation of Huffman Coding algorithm for data compression

@author:  Joey Lupo
'''
from heapq import heappush, heappop, heapify
from collections import defaultdict, namedtuple
from bitarray import bitarray
from operator import attrgetter
import functools

# A tuple containing a symbol and the length of its code in a canonical Huffman tree
# Used in compression and decompression 
CodeLength = namedtuple("CodeLength", 'symbol, length')

def _create_codebook(src):
    """Return a canonical huffman encoding of the src in a dict mapping symbols to codes"""
    
    symb2freq = defaultdict(int)        
    for byte in src:
        symb2freq[byte] += 1
        
    #a named tuple with a weight as the first element, a count element to break ties in 
    #comparisons (used in heapify method) and a dictionary of symbols for a compound node to hold all the 
    #symbols and codes of that node's descendants
    HuffmanNode = namedtuple('HuffmanNode', 'weight, count, symbols')
         
    heap = [HuffmanNode(symb_freq_tuple[1] , count, {symb_freq_tuple[0]:bitarray()}) for count, symb_freq_tuple in enumerate(symb2freq.items())]
    heapify(heap)
    while len(heap) > 1:
        low = heappop(heap)
        high = heappop(heap)
        for symbol, code in low.symbols.items():
            low.symbols[symbol] = bitarray('0') + code
        for symbol, code in high.symbols.items():
            high.symbols[symbol] = bitarray('1') + code
            
        #merging of the symbols dictionary contained in each child node
        low.symbols.update(high.symbols)
        parent_node = HuffmanNode(weight = low.weight+high.weight, count = low.count, symbols = low.symbols)
        heappush(heap, parent_node)           
        
    codebook = heap[0].symbols
    code_lengths = list()
    #create a list of tuples that will be sorted by code word length and then alphabetically
    for symb, code in codebook.items():
        code_lengths.append(CodeLength(symb, len(code)))
    codebook = _to_canonical(code_lengths)
    return codebook

def _to_canonical(code_lengths):
    """Given a list of tuples of (symb, len(code)), return a canonical huffman encoding"""
    
    canonical = dict()
    #sort first by length and then numerically
    code_lengths = sorted(code_lengths, key = attrgetter('length', 'symbol'))

    current_length = code_lengths[0].length
    current_code_num = 0
    current_code_str = '0' * current_length
    #storing the first symbol as all zeroes 
    canonical[code_lengths[0].symbol] = bitarray(current_code_str)
    for code in code_lengths[1:]:
        if code.length > current_length:
            current_code_num = (current_code_num + 1) << (code.length - current_length)
            current_length += (code.length - current_length)
        else:
            current_code_num += 1
        #index out '0b' in resulting string
        bin_num = bin(current_code_num)[2:]
        #prepend 0's to reach needed length in case of shorter bin representation
        current_code_str = '0' * (code.length - len(bin_num)) + bin_num
        canonical[code.symbol] = bitarray(current_code_str)
        
    return canonical

def _encode_dict(codebook):
    """Compress a codebook into lengths representations for compact header"""
    
    compact = bytearray()
    #code lengths stored as 4 bits, so 2 packed per byte
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
        
def compress(src):
    """Public interface for returning huffman encoded source"""
      
    codebook = _create_codebook(src)
    encoded_dict = _encode_dict(codebook)   
    compressed_src = bitarray()
    compressed_src.encode(codebook, src)
    num_bits_encoded = len(compressed_src).to_bytes(2,byteorder = "big")
    compressed_src = compressed_src.tobytes()
    
    compressed = bytearray()
    compressed += num_bits_encoded + encoded_dict + compressed_src
    return compressed

def decompress(compressed):
    """Public interface for decoding huffman encoded source file"""
    
    #unpacking the header into 3 distinct sections
    num_bits_encoded = int.from_bytes(compressed[:2], byteorder = "big")
    code_lengths = _decode_dict(compressed[2:130])
    coded_src = bitarray()
    coded_src.frombytes(bytes(compressed[130:]))
    coded_src = coded_src[:num_bits_encoded]
    
    codebook = _to_canonical(code_lengths)
    uncompressed_list = coded_src.decode(codebook)
    uncompressed = functools.reduce(lambda x,y: x+y, [b.to_bytes(1, byteorder = "big") for b in uncompressed_list])
    return uncompressed
    
