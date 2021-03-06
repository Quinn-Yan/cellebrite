"""
    Qualcomm Download Mode Protocol
    Used to upload a bootloader to the phone
    
    Written by NirZ    
"""




import struct
from Mits.Utils.General import pack32B, pack16B, unpack16B, unpack32B, pack32L, pack16L, unpack16L, unpack32L


from ProtocolQualcommDownloadDecompressor import DecompressLGQC


class Config_QC_V0(object):
    """
    This configuration used LG devices with 0x50 command for read MMC         
    """
    emmc_blocks_per_read = 0x200
    connection_timeout = 0.25
    CMD_EMMC_READ               = 0x50
    
    @staticmethod
    def get_read_emmc_cmd(block_num):
        return "\x00" + pack32L(block_num)


    @staticmethod
    def parse_data(data):
        # send_command() removes one byte, so the offsets are decremented by 1
        header, comp_data = data[:0xF], data[0xF:]
        err_code, data_len, is_compressed = struct.unpack("< ? 8x I x ?", header)
#        assert len(comp_data) == data_len
        return is_compressed, comp_data
    
    @staticmethod
    def parse_internal_init(data):
        
        values_offset = 5 
        # skip 5 bytes: err_code (1 byte) and addr (4 bytes)
        values = struct.unpack("<" + "I"*3, data[values_offset:values_offset+4*3])
        (max_block_cnt_info, max_block_size_info, max_page_size_info) = values
        max_page_cnt = None
        header_len = len(data)
        if (header_len > 19):
            max_page_cnt = ord(data[values_offset+4*3:values_offset+4*3+1])
        return (max_block_cnt_info, max_block_size_info, max_page_size_info, max_page_cnt)




class Config_QC_V1(object):
    emmc_blocks_per_read = 0x200
    CMD_EMMC_READ               = 0x50
    connection_timeout = 0.25
    
    @staticmethod
    def get_read_emmc_cmd(block_num):
        blocks_per_read = 0x200
        return "\x00"*7 + pack32L(block_num)+ pack32L(blocks_per_read)+pack32L(0)
    
    @staticmethod
    def parse_data(data):
        header, comp_data = data[:0x17], data[0x17:]
        data_len = unpack32L(header[15:15+4])
        flag = unpack32L(header[:4])
        return flag == 0x100, comp_data
    
    @staticmethod
    def parse_internal_init(data):
        
        values_offset = 7
        # skip 5 bytes: err_code (1 byte) and addr (4 bytes)
        values = struct.unpack("<" + "I"*3, data[values_offset:values_offset+4*3])
        (max_block_cnt_info, max_block_size_info, max_page_size_info) = values
        return (max_block_cnt_info, max_page_size_info, max_block_size_info, None)




class Config_QC_V2(Config_QC_V0):
    emmc_blocks_per_read = 0x6
    connection_timeout = 0.02
    CMD_EMMC_READ     = 0x99
    @classmethod
    def get_read_emmc_cmd(cls, block_num):        
        return "\x00" + pack32L(block_num) + pack32L(cls.emmc_blocks_per_read) 
    




class ProtocolQualcommDownload(object):
    name = "Download"


    HIGH_PERM_CODE = 'd|f|++-+'
    class Commands:        
        CMD_WRITE                   = 0x01   #Write a block of data to memory (received)        
        CMD_ACK                     = 0x02   #Acknowledge receiving a packet  (transmitted)        
        CMD_NAK                     = 0x03   #Acknowledge a bad packet        (transmitted)
        CMD_ERASE                   = 0x04   #Erase a block of memory         (received)
        CMD_GO                      = 0x05   #Begin execution at an address   (received)
        CMD_NOP                     = 0x06   #No operation, for debug         (received)
        CMD_PREQ                    = 0x07   #Request implementation info     (received)
        CMD_PARAMS                  = 0x08   #Provide implementation info     (transmitted)
        CMD_DUMP                    = 0x09   #Debug: dump a block of memory   (received)
        CMD_RESET                   = 0x0A   #Reset the phone                 (received)
        CMD_UNLOCK                  = 0x0B   #Unlock access to secured ops    (received)
        CMD_VERREQ                  = 0x0C   #Request software version info   (received)
        CMD_VERRSP                  = 0x0D   #Provide software version info   (transmitted)
        CMD_PWROFF                  = 0x0E   #Turn phone power off            (received)
        CMD_WRITE_32BIT             = 0x0F   #Write a block of data to 32-bit memory address (received)
        CMD_MEM_DEBUG_QUERY         = 0x10   #Memory debug query       (received)
        CMD_MEM_DEBUG_INFO          = 0x11   #Memory debug info        (transmitted)
        CMD_MEM_READ_REQ            = 0x12   #Memory read request      (received)
        CMD_MEM_READ_RESP           = 0x13   #Memory read response     (transmitted) 
        CMD_DLOAD_SWITCH            = 0x3A
        CMD_NAND_IMAGE_INIT         = 0x30 
        CMD_NAND_IMAGE_READ_PAGE    = 0x31
        CMD_PRE_FIRMWARE_UPGRADE    = 0x48
        CMD_UPLOAD_PARTITION        = 0x40
        CMD_FIRMWARE_STUFF          = 0x50
        CMD_EMMC_READ               = None
        
        CMD_QCSBL_CFGDATA           = 0x42
        CMD_QCSBL                   = 0x43
        CMD_OEMSBL_HD               = 0x44


        CMD_SELECT_OFFSET           = 0x21
        CMD_FINISH_SECTION          = 0x22


        
        responses = {1  : "NAK_INVALID_FCS",
                     2  : "NAK_INVALID_DEST",
                     3  : "NAK_INVALID_LEN",
                     4  : "NAK_EARLY_END",
                     5  : "NAK_TOO_LARGE",
                     6  : "NAK_INVALID_CMD",
                     7  : "NAK_FAILED",
                     8  : "NAK_WRONG_IID",
                     9  : "NAK_BAD_VPP",
                     10 : "NAK_VERIFY_FAILED",
                     11 : "NAK_NO_SEC_CODE",
                     12 : "NAK_BAD_SEC_CODE",
                     14 : "NAK_OP_NOT_PERMITTED",
                     15 : "NAK_INVALID_ADDR",
                     16 : "NAK_ADDR_MISMATCH",
                     17 : "NAK_FAIL_NAND_PRG",
                     }
    class Cmds0x50:
        CMD_FIRST                   = 0x07
        CMD_OEMSBL_HEADER           = 0x0f
        CMD_SECOND                  = 0x12


    def __init__(self, framer):
        self.framer = framer
        self.decomp = DecompressLGQC()
        self._has_additional_internal_info = False




    def __recv_replay(self, response):
        received_response = self.framer.recv()
            
        if received_response == "":
            raise Exception("ProtocolQualcommDownload: no response")


        code = ord(received_response[0])


        if ((code <> self.Commands.CMD_NAK) and (code <> response)):
            raise Exception("ProtocolQualcommDownload: received invalid response: "+repr(received_response))
                
        if (code == response):
            if (self.Commands.CMD_ACK == response):
                return "ACK"
            return received_response[1:]
        else:
            if (len(received_response) < 3):
                raise Exception("ProtocolQualcommDownload: received invalid length: "+repr(received_response))


            reason = struct.unpack(">H", received_response[1:3])[0]
            if (self.Commands.responses.has_key(reason)):
                reason = self.Commands.responses[reason]
                
            raise Exception("ProtocolQualcommDownload: received NAK: " + repr(reason))                 


       
    def send_command(self, cmd, response=Commands.CMD_ACK, tx='', empty_header=False):
        """ send a command and recv a reply"""
        self.framer.send(chr(cmd) + tx, empty_header)
        return self.__recv_replay(response)


    def send_firmware_stuff_cmd(self, cmd, ret = 1, tx=''):
        data = self.send_command(self.Commands.CMD_FIRMWARE_STUFF, self.Commands.CMD_FIRMWARE_STUFF, (chr(cmd) + tx))
        ret_cmd = ord(data[0])
        data = data[1:]
        if ret_cmd != cmd:
            raise Exception("Unexpected ret code: 0x%x, to command 0x%x" % (ret_cmd, cmd))
        dword = struct.unpack("<L", data)[0]
##        if ret != dword:
##            raise Exception("Unexpected response: 0x%x, expected 0x%x" % (dword, ret))






    def has_additional_internal_info(self) :
        return self._has_additional_internal_info




    def identify_configuration(self):    
        model       = self.get_model()
        data = self.send_init_cmd()
        print "Device model %s" % model
        if '_LGE430_' in model or '_LGE435_' in model :
            print "Setting config V2"
            self.set_config(Config_QC_V2())
            return data    
        if len(data) > 0x200 :
            # different header format
            print "Setting config V1"            
            self.set_config(Config_QC_V1())
            return data
        self.set_config(Config_QC_V0())
        print "Setting config V0"
        return data        


    def set_config(self, config):
        self.protocol_config = config
        self.framer.set_timeout(config.connection_timeout)
        self.Commands.CMD_EMMC_READ = config.CMD_EMMC_READ          
    
    def internal_emmc_read(self, block_num):
        """
        Request is a CMD_EMMC_READ (0x50) command and a block number to start
        reading from. Response is a compressed chunk of blocks starting with the
        block number we requested.


        request format:
          offset:0     1            2             6
          <START>[0x50][  unused:1B][block num:4B]<END>
        response format:
          offset:0     1            2             6             A            E       F              10
          <START>[0x50][err code:1B][block num:4B][block num:4B][data len:4B][ukn:1B][comp. flag:1B][data:xxxB]<END>
        """
        
        if self.decomp.has_more_data() :
            d = self.decomp.decompress_data("")
            self._has_additional_internal_info = self.decomp.has_more_data()
            return d
        
        data = self.send_command(self.Commands.CMD_EMMC_READ, \
                self.Commands.CMD_EMMC_READ, tx=self.protocol_config.get_read_emmc_cmd(block_num)+'\x06\x00\x00\x00')




        is_compressed, comp_data = self.protocol_config.parse_data(data)        
        if is_compressed:
            d = self.decomp.decompress_data(comp_data)
            self._has_additional_internal_info = self.decomp.has_more_data()
            return d
        else:
            self._has_additional_internal_info = False
            return comp_data




    def dload_switch(self):
        """
        switch to download mode (send 0x3a, try with and without 7E header)
        """
        try:
            self.send_command(self.Commands.CMD_DLOAD_SWITCH, \
                    self.Commands.CMD_DLOAD_SWITCH)
        except:
            self.send_command(self.Commands.CMD_DLOAD_SWITCH, \
                    self.Commands.CMD_DLOAD_SWITCH, empty_header = True)




    def ping(self):
        return self.send_command(self.Commands.CMD_NOP)




    def parse_debug(self, debug):
        a = ord(debug[0])
        b = unpack16B(debug[1:3])
        c = unpack32B(debug[3:7])
        d = unpack32B(debug[7:11])
        name1 = debug[11:debug.find("\x00", 11)]
        name2 = debug[11+len(name1)+1:debug.find("\x00", 11+len(name1)+1)]
        return a,b,c,d, name1,name2,  11+len(name1)+1+len(name2)+1


    
    def debug_info(self):
        response = self.send_command(self.Commands.CMD_MEM_DEBUG_QUERY, \
                                       self.Commands.CMD_MEM_DEBUG_INFO)
        results = []
        pos = 0
        flag1 = 1
        while ((pos < len(response)) and (1 == flag1)):
            flag1, var1, var2, var3, name1, name2, record_length = self.parse_debug(response[pos:])
            results.append((var1, var2, var3, name1, name2))
            pos += record_length
        return results




    def read(self, addr, length):
        response = self.send_command(self.Commands.CMD_MEM_READ_REQ, \
                                       self.Commands.CMD_MEM_READ_RESP, \
                                       pack32B(addr) + pack16B(length))
        read_addr   = unpack32B(response[:4])
        read_length = unpack16B(response[4:6])
        data = response[6:6+length]
        return data
    


    def write_addr24bit(self, addr,data):
        response = self.send_command(self.Commands.CMD_WRITE, \
                                       tx = pack32B(addr)[1:] + pack16B(len(data)) + data )
        return response
    
    def write_old(self, addr,data):
        pad = "\x00" * 2
        response = self.send_command(self.Commands.CMD_WRITE_32BIT, \
                                       tx = pack32B(addr) + pack16B(len(data)) + pad+ data )
        return response


    def write(self, addr, data):
        response = self.send_command(self.Commands.CMD_WRITE_32BIT, \
                                       tx = pack32B(addr) + pack16B(len(data)) + data )
        return response




    def go(self, addr):
        return self.send_command(self.Commands.CMD_GO, tx = pack32B(addr))


    
    def shut(self):
        self.send_command(self.Commands.CMD_PWROFF)




    def reset(self):
        self.send_command(self.Commands.CMD_RESET)




    def get_implementation(self):
        result = self.send_command(self.Commands.CMD_PREQ, \
                                  self.Commands.CMD_PARAMS)
        data_len = ord(result[0])
        return result[1:1+data_len]
        


    def get_version(self):
        ver = self.send_command(self.Commands.CMD_VERREQ, \
                                  self.Commands.CMD_VERRSP)
        txt_len = ord(ver[0])
        txt = ver[1:1 + txt_len]
        return txt


    def get_model(self):
        return self.get_version().replace("/", "_")  




    def send_init_cmd(self):
        return self.send_command(self.Commands.CMD_NAND_IMAGE_INIT, \
                                  self.Commands.CMD_NAND_IMAGE_INIT)
        
    def internal_init(self):
        data = self.identify_configuration()
        # skip 5 bytes: err_code (1 byte) and addr (4 bytes)
        values = self.protocol_config.parse_internal_init(data)
        (self.max_block_cnt_info, self.max_block_size_info, self.max_page_size_info, self.max_page_cnt) = values


        print "header_len: ", len(data)    
        print "max_block_cnt_info:      %08X"%self.max_block_cnt_info
        print "max_block_size_info:     %08X"%self.max_block_size_info
        print "max_page_size_info:      %08X"%self.max_page_size_info
        if (None != self.max_page_cnt):
            print "max_page_cnt:            %08X"%self.max_page_cnt
            
    def internal_read(self, page, ecc_state = 1):            
        addr = page * self.max_page_size_info        
        txdata = pack32L(addr) + pack16L(ecc_state) + struct.pack("<" + "I"*3, self.max_block_cnt_info, self.max_block_size_info, self.max_page_size_info) 
        txdata += "\x00" * (self.header_len - len(txdata))
        
        data = self.send_command(self.Commands.CMD_NAND_IMAGE_READ_PAGE, \
                                  self.Commands.CMD_NAND_IMAGE_READ_PAGE, txdata)
        page_data = data[self.header_len:]
        return page_data
                                 
        
    # Unified Ram Reading interface
    def read_ram(self, addr, size):
        return self.read(addr,size)
    
    def set_high_permissions(self, code = HIGH_PERM_CODE):
        data = self.send_command(self.Commands.CMD_UNLOCK, \
                                  self.Commands.CMD_ACK, code)
        return data


    # PACKET_ORDER = [CMD_PRE_FIRMWARE_UPGRADE,
    #                 CMD_UPLOAD_PARTITION,
    #                 (CMD_FIRMWARE_STUFF, CMD_FIRST),
    #                 (CMD_FIRMWARE_STUFF, CMD_OEMSBL_HEADER),
    #                 (CMD_FIRMWARE_STUFF, CMD_FIRST),
    #                 (CMD_FIRMWARE_STUFF, CMD_SECOND),
    #                 CMD_LETS_UPLOAD,


    #                ]
    def start_firmware_update(self):
        self.send_command(self.Commands.CMD_PRE_FIRMWARE_UPGRADE, tx='\0')


    def start_qcsbl_cfg(self):
        self.send_command(self.Commands.CMD_QCSBL_CFGDATA)


    def start_qcsbl(self):
        self.send_command(self.Commands.CMD_QCSBL)


    def send_oemsbl_hd(self, oemsbl_data):
        start_address = 0x240000
        data_len = len(oemsbl_data)
        end_address = start_address + data_len
        oemsbl_hd_data = struct.pack("<LLLLLLLLLL", 1, 3, 0, start_address, data_len, data_len, end_address, 0, end_address, 0)
        padded_data = oemsbl_hd_data + ('\0' * (0x200 - len(oemsbl_hd_data)))
        self.send_command(self.Commands.CMD_OEMSBL_HD, tx=struct.pack(">H", 0x200) + padded_data)


    def send_partition_table(self, partition_data):
        self.send_command(self.Commands.CMD_UPLOAD_PARTITION, tx=(struct.pack(">HB", 0x200, 0x35) + partition_data[:0x200]))


    def do_firmware_stuff(self, oemsbl_data):
        self.send_firmware_stuff_cmd(self.Cmds0x50.CMD_FIRST)
        self.send_firmware_stuff_cmd(self.Cmds0x50.CMD_OEMSBL_HEADER, tx=('\0' * 6) + oemsbl_data[:0x80])
        self.send_firmware_stuff_cmd(self.Cmds0x50.CMD_FIRST, 0)
        self.send_firmware_stuff_cmd(self.Cmds0x50.CMD_SECOND, 2)


    def send_chunk(self, offset, data):
        padded_data = data + ('\0' * (0x800 - len(data)))
        self.send_command(self.Commands.CMD_WRITE, tx='\0' + struct.pack(">HH", offset, 0x800) + padded_data)


    def send_big_chunk_header(self, offset, size):
        # don't ask me why is this +1 here... sniffed that way :)
        self.send_command(self.Commands.CMD_SELECT_OFFSET, tx=struct.pack(">LL", offset + 1, size))


    def finish_section(self):
        self.send_command(self.Commands.CMD_FINISH_SECTION)




    










class ProtocolLgDload0x30(object):
    """
    we use FramerQC_HDLC only to send packets, because of the request must be a valid HDLC packets
    the response though is non framed raw data, it must not be recieved as a standard HDLC packet
    because the response is only raw data we will recieve it as raw data, with base.recv
    
    the size of base.recv must be exactly 2048 for the response packet to 0x30 and 4097 for 0x33
    we recv 4097 and not 4096 because the device will send empty packet to "end" the transaction
    
    GET_PARTITIONS_COMMAND will fetch the storage size of the device in big endian, example : 008, in a const offset ( hexResponse[72:78] )
    it will also fetch the partition list without their sizes
    
    READ_MMC_COMMAND will read 4k per iteration, the packet looks like this :
         33 00 00 00 00 00 00 10 00 00 00 08 00 00 00 00 00 00 00 00 B7 00 7E 
        where "33" is our READ_MMC_COMMAND command, 
        big endian "10" is the block number ( third iteration ), 
        and "08" is our STEP_SIZE ( how much blocks ),
        HDLC framed packet will have crc, for our packet it will be "B7 00"
        HDLC postfix must be 7E
    
    """
    def __init__(self, framer):
        self.framer = framer
        self.cmd1 = True
        
    name = "ProtocolLgDload0x30"
    GET_PARTITIONS_COMMAND = "\x30"
    READ_MMC_COMMAND = 0x33    
    
    def getPartitions(self):
        data = self.GET_PARTITIONS_COMMAND
        self.framer.send(data)
        raw = self.framer.recv(2048)
        g_loc = 0        
        while True :
            g_loc = raw.find('G', g_loc)
            if g_loc == -1 or g_loc > 0x100 :
                raise RuntimeError("Failed to find MMC size")            
            size_ = raw[g_loc - 2] + raw[g_loc - 1]
            try :
                size_ = int(size_)
            except ValueError :
                continue
            break
        print "Found MMC size %dGB" % (size_)
        return size_




    def read_mem(self, block_num, blocks, expected_bytes):
        tries = 10
        packet = struct.pack(">BBHIIII", self.READ_MMC_COMMAND, 0, 0, block_num, blocks, 0, 0)
        self.framer.send(packet)
        raw = ''
        for i in xrange(tries) :
            raw += self.framer.recv(expected_bytes - len(raw))
            if len(raw) ==  expected_bytes :
                return raw
        return raw
