"""
Author: Rony Kelner


This module implements the decompression of a LG/Qualcomm compression algorithm.


This compression protocol was discovered as part of the LG Qualcomm dload mode
research. Specifically LG VS840 phones with EMMC flash. More specifically, the
commands for reading EMMC flash returns the data in the compressed form.


For information about how to decompress please start from reading the
decompress_data() doc string.


"""


import traceback


DEBUG = False
def dbg(*args):
    if DEBUG:
        print ' '.join(str(s) for s in args)






class DecompressLGQC(object):
    MARKER_0x8000 = 0x16
    MARKER_END_OF_COMPRESSED_DATA = 0x6
    MAX_WINDOW_SIZE = 0x10000
    OPTIMAL_RESULT_BUFFER = int(MAX_WINDOW_SIZE * 1.3)
    
    def __init__(self):
        self.result = ""
        self.data_in_loc = 0
        self.data_in = ""
        self.prev_offset = None        
        
    def get_next_byte(self):        
        byte = self.data_in[self.data_in_loc]
        self.data_in_loc += 1
        return ord(byte)        
    
    def calc_size(self, next_byte,  flag):
        if next_byte == flag:
            size = ord(self.data_in[self.data_in_loc]) + 0x10
            self.data_in_loc += 1
        else:
            size = next_byte & 0xF
                 
        return size


    def handle_uncompressed(self, next_byte):
        """
        uncompressed header comes in two flavors based on the length of the uncompressed data:
        1 byte - if the uncompressed data length is < 0x10
          [0xE0 + uncompressed length:4 bits]
            length is encoded in the low nibble of the byte
        2 bytes - if the length is >= 0x10
          [0xE0][uncompressed length - 0x10]
            the first byte contains constant 0xE0
            the second byte contains the (length - 0x10)
        """                    
        size = self.calc_size(next_byte, 0xE0)        
        self.result += self.data_in[self.data_in_loc:self.data_in_loc+size]        
        self.data_in_loc += size 
    




    def read_all_copy_bytes(self):
        """
        "Number of bytes to copy" is represented as a sum of values. Those values
        are encoded as 1 or 2 byte chunks, each chunk encodes one value.
    
        1 byte chunk - if the value is less than 0x10
          [0xF0 + copy_bytes:4 bits]
            encoded as the lower nibble of the byte
        2 bytes - if the value is greater or equal to 0x10
          [0xF0][value - 0x10]
            the first byte is 0xF0
            (number - 0x10) is encoded in the next byte
        """
        copy_bytes = 0
    
        while True:
            prev_pos = self.data_in_loc
            if (self.data_in_loc >= len(self.data_in)):
                break
            
            next_byte = ord(self.data_in[self.data_in_loc])
            self.data_in_loc += 1
                
            if next_byte == self.MARKER_0x8000: # skip the 0x8000 boundary marker
                continue
            if next_byte >> 4 != 0xF:
                # it's not ours, put it back!
                self.data_in_loc = prev_pos                 
                break
    
            copy_bytes += self.calc_size(next_byte, 0xF0)                
        return copy_bytes
    


    def copy_compressed(self, offset, copy_bytes):
        """ copy <copy_bytes> from <offset> to data_out """    
        dbg("copy compressed: offset:%d copy_bytes:%d buf_len:%d" % (offset, copy_bytes, len(self.result)))
        if copy_bytes >= offset :
            buf = self.result[-offset:]
            s = copy_bytes / offset
            m = copy_bytes % offset
            self.result += (s * buf) + buf[:m]
        else :
            self.result += self.result[-offset:-offset+copy_bytes]
        return 
#        for _ in xrange(copy_bytes) :
#            self.result += self.result[-offset]
            


    def copy_uncompressed(self, length):
        self.result += self.data_in[self.data_in_loc:self.data_in_loc+length]
        self.data_in_loc += length


    def handle_compressed_with_same_offset(self, next_byte, offset):
        """
        In this case the offset is the same as in the previous compressed block,
        hence it is not encoded in the header.
        There are two flavors of this header, with and without the uncompressed data:
    
        - with uncompressed data: [header byte 0][uncompressed...][copy_bytes...]
            header byte 0:
              [uncompressed length:2 bis|copy_bytes:3 bits|b110:3 bits]
    
        - no uncompressed data: [header byte 0][copy_bytes...]
            header byte 0:
              [0xF3 + (copy_bytes:3 bits)]
    
        * copy_bytes:3 bits in the header are encoded as value-3
    
        """
        if next_byte >> 4 == 0xF:
            dbg("no uncompressed data")
            copy_bytes = next_byte - 0xF3
        else:
            dbg("uncompressed data present")
            uncompressed_len = (next_byte >> 6) & 3
            assert uncompressed_len # no uncompressed data can't happen in this case
            self.copy_uncompressed(uncompressed_len)
            copy_bytes = (next_byte >> 3) & 7
    
        # minimum compressed bytes is 3, its encoded as -3
        copy_bytes += 3
    
        copy_bytes += self.read_all_copy_bytes()
        self.copy_compressed(offset, copy_bytes)




    def handle_compressed(self, next_byte):
        """
        3 flavors for this type of header:
    
        - offset 11 bits
          In this case the offset is less than 0x600.
    
          Header form: [header byte 0][uncompressed...][header byte 1][copy_bytes...]
            header byte 0:
              [uncompressed length:2 bits|copy_bytes:3 bits|offset hi byte:3 bits]
            header byte 1:
              [offset lo byte:8 bits]
    
          Note, that because the offset is less than 0x600 the hi byte 3 bits that
          present in the header byte 0 cannot form b110, so there is no ambiguity
          with the "compressed with same offset" case.
          
        - offset 14 bits, copy_bytes 5 bits:
          In this case the offset is relatively small and the (copy_bytes - 3) can
          be represented by 5 bits. Those 5 bits then divided into hi:3 bits and
          lo:2 bits and placed in different header bytes.
    
          Header form: [header byte 0][uncompressed...][header byte 1][header byte 2]
            header byte 0:
              [b101:3 bits|uncompressed length:2 bits|copy_bytes hi:3 bits]
            header byte 1:
              [copy_bytes lo:2 bits|offset hi byte:6 bits]
            header byte 2:
              [offset lo byte:8 bits]
    
        - offset 16 bits
          Header form: [header byte 0][uncompressed...][header byte 1][header byte 2][copy_bytes...]
            header byte 0:
              [uncompressed length:2 bits|copy_bytes:3 bits|b111:3 bits]
            header byte 1:
              [offset lo byte:8 bits]
            header byte 2:
              [offset hi byte:8 bits]
        """
    
        if next_byte >> 5 == 0b101:
            dbg("case: offset 14 bits")
            uncompressed_len = (next_byte >> 3) & 3
            copy_bytes = (next_byte & 7) << 2
        elif next_byte & 7 == 0b111:
            dbg("compressed: offset 16 bits")
            uncompressed_len = (next_byte >> 6) & 3
            copy_bytes = (next_byte >> 3) & 7
        else:
            dbg("compressed: offset 11 bits")
            uncompressed_len = (next_byte >> 6) & 3
            copy_bytes = (next_byte >> 3) & 7
            offset = (next_byte & 7) << 8
    
        self.copy_uncompressed(uncompressed_len)
        next_next_byte = self.get_next_byte()
    
        if next_byte >> 5 == 0b101: # offset 14 bits
            copy_bytes += next_next_byte >> 6
            offset = ((next_next_byte & 0x3F) << 8) + self.get_next_byte()
        elif next_byte & 7 == 0b111: # offset 16 bits
            offset = next_next_byte + (self.get_next_byte() << 8)
        else: # offset 11 bits
            offset += next_next_byte
    
        # all the cases encode copy_bytes as value - 3, so we add it back
        copy_bytes += 3
        copy_bytes += self.read_all_copy_bytes()
    
        self.copy_compressed(offset, copy_bytes)
        return offset






    def decompress_data(self, compressed_data):
        """
            For more info read at EOF
        """
        self.data_in += compressed_data
        self.data_in_loc = 0
        
        while True:
            if self.data_in_loc >= len(self.data_in):
                break
            
            if len(self.result) > self.OPTIMAL_RESULT_BUFFER :
                self.data_in = self.data_in[self.data_in_loc:]
                self.data_in_loc = 0
                res = self.result[:-self.MAX_WINDOW_SIZE]
                self.result = self.result[-self.MAX_WINDOW_SIZE:]
                return res
                              
            next_byte = self.get_next_byte()


            try:
                if next_byte == self.MARKER_0x8000:
                    dbg("marker: 0x8000 boundary")
                elif next_byte == self.MARKER_END_OF_COMPRESSED_DATA:
                    dbg("marker: done")
                    break
                elif next_byte >> 4 == 0xE:
                    dbg("uncompressed block")
                    self.handle_uncompressed(next_byte)
                elif next_byte >> 4 == 0xF or (next_byte & 0x7 == 0b110 and next_byte >> 5 != 0b101):
                    dbg("compressed block (same offset)")
                    self.handle_compressed_with_same_offset(next_byte, self.prev_offset)
                else:
                    dbg("compressed block")
                    self.prev_offset = self.handle_compressed(next_byte)
            except Exception as e:
                raise e
            
            
        # Done to process all the chunk 
        self.data_in = self.data_in[self.data_in_loc:]
        self.data_in_loc = 0
        r = self.result
        self.result = ""
        return r




    def has_more_data(self) :
        return self.data_in_loc < len(self.data_in)










    """
Compressed data stream:
================================================================================
Compressed data stream is arranged into blocks of compressed and uncompressed
data and special markers.


+--------------------------------------------------------------------------+
|CC|CC|UU|UU|UU|CC|UU|CC|0x16|CC|CC|CC|................|CC|CC|UU|CC|UU|0x06|
+--------------------------------------------------------------------------+


UU:
---
Uncompressed block (see below).


CC:
---
Compressed block (see below).


0x16 (MARKER_0x8000):
---------------------
This marker can appear in between compressed/uncompressed blocks or in between
the stream of "copy_bytes" blocks (see below).
We are not aware of any significance of this marker to the decompression
process, hence we just skip this marker.


0x06 (MARKER_END_OF_COMPRESSED_DATA):
-------------------------------------
This marker is the last byte of a compressed stream. Marks the end of our work.




Uncompressed block:
================================================================================
A header, followed by bytes of uncompressed data. The header starts with a byte
that contains 0xE in its high nibble. The header can be 1 or 2 bytes long
depending on the uncompressed data length.


                            +----------------------------+
                            | header | uncompressed data |
                            +----------------------------+
                               /  `                                        
 uncompressed data len < 0x10 /     `                                     
                             /        `                                        
+--------------------------------------+`         
|0xE0 + uncompressed data length:4 bits|  `                                    
+--------------------------------------+    `    
:             byte 0                   :      `   uncompressed data len >= 0x10             
                                                `
                              +------------------------------------------------+
                              |    0xE0      | uncompressed data length - 0x10 |
                              +------------------------------------------------+
                              :    byte 0    :                byte 1           :
    


                                                                                
Compressed block:
================================================================================
The data is compressed using the "go back X bytes and copy Y bytes" scheme.
In this code (and documentation) we call X - an "offset" and Y - a "copy_bytes".
Notice "copy_bytes" is the NUMBER of bytes to copy (the bytes themselves are
not present, this is the compression).


General form of a compressed block:
+-----------------------------------------------------------+                                                                               
| header | uncompressed bytes | header cont. |  copy bytes  |                                                                             
+-----------------------------------------------------------+
: 1 byte :     0-3 bytes      :   1-2 bytes  :  0-INF bytes :




header (spread over 1-3 bytes):
-------------------------------
Contains the following:
- number of uncompressed bytes
- offset
- copy bytes - number of bytes to copy (see below for encoding)
- magic bits for distinguish between different headers


  Types of headers:
  -----------------
  Header type is chosen based on the offset length, the copy bytes length and
  whether or not the previous compressed block had the same offset.


  Legend:
  -------
    UL - uncompressed length
    CB - copy bytes
    off - offset


  header A (offset 11 bit)
  +--------------------------+--------------------------+--------------------+------------------------+                      
  |   UL   |   CB   | off hi |         Optional         |       off lo       |        Optional        |
  +--------------------------+ ZZZZ  Uncompressed  ZZZZ +--------------------+ ZZZZ  copy bytes  ZZZZ +
  : 2 bits : 3 bits : 3 bits :           Data           :       8 bits       :         chunks         :
  :..........................:           Here           :....................:          here          :
  :          byte 0          :                          :       byte 1       :                        :


  header B (offset 14 bit)
  +--------------------------+--------------------------+---------------------+------------+
  |  101   |   UL   | CB hi  |         Optional         |   CB lo  |  off hi  |   off lo   |
  +--------------------------+ ZZZZ  Uncompressed  ZZZZ +----------+----------+------------+
  : 3 bits : 2 bits : 3 bits :           Data           :   2 bits :  6 bits  :   8 bits   :
  :..........................:           Here           :.....................: ...........:
  :          byte 0          :                          :        byte 1       :   byte 2   :


  header C (offset 16 bit)
  +--------------------------+--------------------------+--------------------+--------------------+------------------------+                     
  |   UL   |   CB   |   111  |         Optional         |       off lo       |       off hi       |        Optional        |
  +--------------------------+ ZZZZ  Uncompressed  ZZZZ +--------------------+--------------------+ ZZZZ  copy bytes  ZZZZ +
  : 2 bits : 3 bits : 3 bits :           Data           :       8 bits       :       8 bits       :        chunks          :
  :..........................:           Here           :....................:....................:         here           :
  :          byte 0          :                          :       byte 1       :       byte 2       :                        :


  header D (same offset as in the last compressed block, no uncompressed data)
  +------------------+------------------------+
  | 0xF3 + CB:3 bits |        Optional        |
  +------------------+ ZZZZ  copy bytes  ZZZZ +
  :      byte 0      :        chunks          :
                               here            


  header E (same offset as in the last compressed block, uncompressed data present)
  +--------------------------+--------------------------+------------------------+
  |   UL   |   CB   |   110  |         Optional         |        Optional        |
  +--------------------------+ ZZZZ  Uncompressed  ZZZZ + ZZZZ  copy bytes  ZZZZ +
  : 2 bits : 3 bits : 3 bits :           Data           :        chunks          :
  :..........................:           Here           :         here           :                                                
  :          byte 0          :                          :                        :




uncompressed bytes (optional):
------------------------------
0-3 uncompressed bytes to be added to the decompressed data before handling of
the compressed part of this block.


copy bytes
----------
The number of bytes to copy is encoded as a sum of numbers (values). The first
value is encoded in the header and the rest of the values are encoded as copy
bytes "chunks".
Because the minimum number of bytes to copy (compress) is 3, the first value
(the one in the header) is encoded (value - 3).
To recover "copy bytes" one needs to do the following:
    Copy Bytes = (CB_header + 3) + CB_chunk_0 + CB_chunk_1 + ... + CB_chunk_N


                       copy bytes chunk
                       ----------------
                       /             \                             
     value is < 0x10  /               \ value is >= 0x10                           
                     /                 \                               
  +-------------------+     +---------------------------------+            
  |0xF0 + value:4 bits|     |    0xF0      |   value - 0x10   |                                         
  +-------------------+     +---------------------------------+           
  :       byte 0      :     :    byte 0    :       byte 1     :                        
                                                 


    """
