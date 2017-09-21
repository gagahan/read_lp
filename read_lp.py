import argparse
import sys

from datetime import datetime
from datetime import timedelta



# constants --------------------------------------------------------------------
START_DATA_0 = 0x1E00       # ohne Vorwerte
START_DATA_1 = 0x5600       # mit Vorwerte
LP_END = 0x2FFDF
SIZE_CLUSTER = 0x200
SIZE_LPSNINT = 1
SIZE_TIME_STAMP = 3
SIZE_STATUS = 4
SIZE_DATE_STAMP = 3
SIZE_LPNRDAY = 1
SIZE_UNUSED_BYTE_EOC = 1

SIZE_EEPROM_0 = 0x7FFF + 1
SIZE_EEPROM_1 = 0xFFFF + 1
SIZE_EEPROM_2 = 0xFFFF + 1

N_CLUSTERS = 256
LAST_CLUSTER_EEPROM_0 = 0x07FE0

DISFLG = 0x051B

ELPSMOD = 0x0789

ELGINT = 0x078E             # LP interval

EUISIZE = 0x079A

PERSO = 0x04B0

DPLOCE = 0x04C1
DPLOCD = 0x04C2

DISFLG_EE = 0b11000000
DISFLG_DD = 0b00110000
DISFLG_CC = 0b00001100
DPLOCE_DDD = 0b00000011
DPLOCD_DDD = 0b00000011

ELPSMOD_LPRAPE = 0b10000000
ELPSMOD_LPREGS = 0b00100000
ELPSMOD_LPENER = 0b00010000
ELPSMOD_LPRVS = 0b00001000
ELPSMOD_LPVSET = 0b00000001

PERSO_MS = 0b00000001

ELPCH = (0x0787,
         0x0788,
         0x078A,
         0x078B,
         0x078C,
         0x078D,
         0x0790,
         0x0791)


N_DIGITS_EREGS = {0b00: 8,
                  0b01: 7,
                  0b10: 6,
                  0b11: 5}

N_DIGITS_PWR = {0b00: 4,
                0b01: 3,
                0b10: 6,
                0b11: 5}

N_DIGITS_ENER = {0b10: 6,
                 0b11: 5}

MESSGROESSE_MAP = {0x00: '--',
                   0x01: 'Q1',
                   0x02: 'Q2',
                   0x03: '+Q',
                   0x04: 'Q3',
                   0x05: 'Q1+Q3',
                   0x06: '-Q(Q2+Q3)',
                   0x07: 'Q1+Q2+Q3',
                   0x08: 'Q4',
                   0x09: '+Q(Q1+Q4',
                   0x0A: 'Q2+Q4',
                   0x0B: 'Q1+Q2+Q4',
                   0x0C: '-Q',
                   0x0D: 'Q1+Q3+Q4',
                   0x0E: 'Q2+Q3+Q4',
                   0x0F: 'Q1..Q4',
                   0x10: '-S',
                   0x20: '+S',
                   0x30: '+S,-S',
                   0x40: '-P[kW]',
                   0x80: '+P[kW]'}


DATE_FORMAT = '%y%m%d%H%M%S'
DATE_FORMAT_NO_TIME = '%Y-%m-%d'

log_file = 'read_lp.time.log'
output_file = 'serial.csv'


# file logger  -----------------------------------------------------------------
# prints to stdout and logfile at the same time
class Logger(object):
    def __init__(self, file_name, verbose=False):
        self.verbose = verbose
        self.terminal = sys.stdout
        now = datetime.now().strftime(DATE_FORMAT)
        self.log = open(file_name.replace('time', now), "w")

    def write(self, message):
        if self.verbose:
            self.terminal.write(message)
        self.log.write(message)

    def flush(self):
        pass


# argument parser --------------------------------------------------------------
class ArgParser(argparse.ArgumentParser):
    
    def __init__(self, **kwargs):
        argparse.ArgumentParser.__init__(self, **kwargs)
        self.prog = 'read_lp'
        self.description = 'Restore load profile from AS3000 EEPROM.'
        self.add_argument('file1', metavar='File1',
                        help='content from eeprom 1')
        self.add_argument('file2', metavar='File2',
                        help='content from eeprom 2')
        self.add_argument('file3', metavar='File3',
                        help='content from eeprom 3')
        self.add_argument('-i', '--ignore', action='store_true',
                          help='ignore invalid input data')
        self.add_argument('-v', '--verbose', action='store_true',
                        help='print log output to screen')
        self.add_argument('-o', '--output', metavar='Output',
                        help='output file (csv format)')
        
    def error(self, message):
        sys.stderr.write('error: %s\n\n' %message)
        self.print_help()
        sys.exit()


# address map with EEPROM content ----------------------------------------------

# addresses 0x8000 to 0xffff will be skipped in order to maintain similar
# addresses like in the data files.
# addresses from the 2nd eeprom have an offset of 0x10000
# addresses from the 3rd eeprom have an offset of 0x20000

class EepromData(dict):
    
    def __init__(self, args):
        dict.__init__(self)
        
        size_eeprom = [SIZE_EEPROM_0, SIZE_EEPROM_1, SIZE_EEPROM_2]
        
        # for every file do..
        for i, fname in enumerate([args.file1, args.file2, args.file3]):
            
            # read lines
            try:
                f = open(fname)
                lines = [str(i) + l[:53] for l in f.readlines()]
            except FileNotFoundError:
                sys.stderr.write('error: file "%s" not found!\n' %fname)
                sys.exit('abort program..')
            
            # validate input data..
            data_is_valid = True
            
            # ..check number of lines
            size = size_eeprom[i]
            n_lines = size_eeprom[i] // 16
            
            if len(lines) != n_lines:
                
                data_is_valid = False
                
                sys.stderr.write('\nfile "%s" has an invalid lenght %i lines\n' \
                                 %(fname, len(lines)))
                
                sys.stderr.write('but EEPROM%i size is %i bytes (%i lines)\n' \
                                 %(i+1, size, n_lines))
            
            # tbd: ..check addresses
            
            # tbd: ..check data pattern for every line            
            
            if data_is_valid or args.ignore:
                
                # add data to address map
                offs = 6
                for line in lines:
                    adr = int(line[:5], 16)
                    for byte in range(16):
                        idx = offs + byte * 3
                        self[adr] = line[idx:idx + 2]
                        adr += 1
                
            else:
                sys.exit('abort program..\n' +
                'use option "-i" to ignore invalid data.\n')


# converter for status byte  ---------------------------------------------------
class StatusByte():
    
    def __init__(self, status_byte, elpsmod):
        
        self.status = status_byte
        self.msg = {}
        self.msg[0] = 'fatale(r) Fehler'
        self.msg[1] = 'Uhrzeit verloren'
        self.msg[2] = 'Messperiode gestoert'
        self.msg[3] = 'Zeitumstellung Sommer/Winter'
        self.msg[4] = 'neues Intervall wegen Maximumrueckstellung'
        self.msg[5] = 'Datum/Uhrzeit geaendert'
        self.msg[6] = 'Spannungsrueckkehr'
        self.msg[7] = 'Spannungsausfall'

        if elpsmod & ELPSMOD_LPRVS:
            self.msg[3] += ' / Ruecklauferkennung'
        if elpsmod & ELPSMOD_LPRAPE:
            self.msg[4] += ' / Spannungsausfall in 1 oder 2 Phasen' 
        if elpsmod & ELPSMOD_LPVSET:
            self.msg[6] += ' / Konfigurationsaenderung'
        
        
    def __str__(self):
        s = ''
        for bit in range(8):
            bit_mask = 1 << bit
            if self.status & bit_mask:
                s += self.msg[bit] + ', '
        if s[-2:] == ', ':
            s = s[:-2]
        return s
     
        
# load profile -----------------------------------------------------------------
class LP():
    
    def __init__(self, eeprom_data):
        self.eeprom_data = eeprom_data
        
        # read lp parameters from eeprom data
        self.read_lp_rarameters()
        
        # generate cluster information
        print('\ngenerate cluster info...')
        self.clusters = []
        
        # for first eeprom
        if self.lp_start <= LAST_CLUSTER_EEPROM_0:
            for adr in range(self.lp_start, LAST_CLUSTER_EEPROM_0, SIZE_CLUSTER):
                self.clusters += filter(None, [self.create_cluster(adr)])
        # for 2nd and 3rd eeprom
        for adr in range(self.lp_start, self.lp_stop, SIZE_CLUSTER):
            self.clusters += filter(None, [self.create_cluster(adr)])
        
        # link clusters
        self.clusters[-1]['next_cluster'] = self.clusters[0]
        for i in range(len(self.clusters) - 1):
            self.clusters[i]['next_cluster'] = self.clusters[i+1] 
            
        
        # read lp data
        self.add_lp_data()
            
            
    
    
    def read_lp_rarameters(self):
        
        # read active channels
        print('\ncheck active lp channels..')
        self.elpch = []
        self.num_of_active_channels = 0
        for adr in ELPCH:
            self.elpch.append(int(self.eeprom_data[adr], 16))
            print('    %s elpch %i:(\'%s\')' \
                  %(hex(adr), len(self.elpch), MESSGROESSE_MAP[self.elpch[-1]]))
            
            if self.elpch[-1]:
                self.num_of_active_channels += 1
        
        # check data format
        print('\ncheck data format...')
        param = int(self.eeprom_data[DISFLG], 16)
        # anzahl stellen Energieregister
        self.disflg_ee = (param & DISFLG_EE) >> 6
        # anzahl stellen Leistungsregister
        self.disflg_dd = (param & DISFLG_DD) >> 4
        # anzahl stellen kumulativ register
        self.disflg_cc = (param & DISFLG_CC) >> 2
        
        # nachkommastellen energieregister
        self.dploce_ddd = int(self.eeprom_data[DPLOCE], 16) & DPLOCE_DDD
        # nachkommastellen leistungsregister
        self.dplocd_ddd = int(self.eeprom_data[DPLOCD], 16) & DPLOCD_DDD
        
        # read elpsmod (byte3 class5)
        self.elpsmod = int(self.eeprom_data[ELPSMOD], 16)
        
        # read lp data type and define format
        self.elpsmod_lpregs = self.elpsmod & ELPSMOD_LPREGS
        self.elpsmod_lpener = self.elpsmod & ELPSMOD_LPENER
        if self.elpsmod_lpregs:
            self.lp_type = 'Energieregister'
            self.size_lp_channel = (N_DIGITS_EREGS[self.disflg_ee] + 2 // 2) // 2
            self.lp_decimal = self.dploce_ddd
            
        elif self.elpsmod_lpener:
            self.lp_type = 'Ernergievorschub'
            if self.disflg_cc < 0b10:
                self.size_lp_channel = (N_DIGITS_ENER[self.disflg_ee] + 2 // 2) // 2
            else:
                self.size_lp_channel = (N_DIGITS_ENER[self.disflg_cc] + 2 // 2) // 2
            self.lp_decimal = self.dploce_ddd
            
        else:
            self.lp_type = 'Leistungsmittelwerte'
            
            self.size_lp_channel = (N_DIGITS_PWR[self.disflg_dd] + 2 // 2) // 2
            self.lp_decimal = self.dplocd_ddd
        
        # calculate size of lp entry
        self.size_lp_entry = self.size_lp_channel * self.num_of_active_channels
    
        print('    type:', self.lp_type)
        print('    size per channel: %i bytes' %self.size_lp_channel)
        print('    decimal point number: %i' %self.lp_decimal)
        print('    size per entry: %i' %self.size_lp_entry)
        
        # check interval size
        print('\ncheck interval size..')
        self.elgint = int(self.eeprom_data[ELGINT], 16)
        print('    lp interval:', self.elgint, 'min')
        
        # check if vorwertebildung active
        self.perso_ms = int(self.eeprom_data[PERSO], 16) & PERSO_MS
        
        # calc start adress for lp
        print('\ncheck start address for load profile')
        if self.perso_ms:
            self.np_start = START_DATA_1
        else:
            self.np_start = START_DATA_0
        self.euisize = int(self.eeprom_data[EUISIZE], 16)
        self.lp_start = self.np_start + self.euisize * SIZE_CLUSTER
        # first eeprom is only 0x8000 bytes
        # for that reason add an offset if lp starts in 2nd or 3rd eeprom
        if self.lp_start >= SIZE_EEPROM_0:
            self.lp_start += SIZE_EEPROM_0
        print('    start address: %s' %hex(self.lp_start))
        
        # calc last adress for lp
        print('\ncheck last address')
        eeprom0 = SIZE_EEPROM_0 - self.np_start
        self.lp_stop  = ((N_CLUSTERS-1) * 512 - eeprom0 - SIZE_EEPROM_1) + \
                        0x20000 - 1
        print('    last address: %s' %hex(self.lp_stop))



    def create_cluster(self, adr_cluster):    
        print('check cluster at: ', hex(adr_cluster))
        cluster = {'first_adr': adr_cluster}
        
        # get num of date stamps
        lpnrday = int(self.eeprom_data[adr_cluster + SIZE_CLUSTER - 2], 16)
        
        # if lpnrday==0 indicates same stamp as in last cluster
        if lpnrday == 0:
            lpnrday += 1
        cluster['lpnrday'] = lpnrday
        
        # read all date stamps in this cluster
        cluster['dateStamps'] = []
        
        if lpnrday not in (0x55, 0xAA, 0xFF):
            
            for i in range(lpnrday):
                
                try:
                    date_stamp = {}
                    
                    adr_date_stamp = adr_cluster + SIZE_CLUSTER - 2 - 4 * (i + 1)
                    
                    offs = int(eeprom_data[adr_date_stamp], 16)
                    year = int('20' + eeprom_data[adr_date_stamp+1])
                    month = int(eeprom_data[adr_date_stamp+2])
                    day = int(eeprom_data[adr_date_stamp+3])
                    
                    date_stamp['offs'] = offs
                    date_stamp['date'] = datetime(year, month, day)
                    cluster['dateStamps'].append(date_stamp)
            
                except ValueError:
                    # illegal daystamp, return without value
                    print('    !error: daystamp is not bcd !')
                    print('    skip daystamp..')
            
        # calculate last usable address in this cluster
        size_date_stamps = (SIZE_UNUSED_BYTE_EOC + (SIZE_LPNRDAY +
                            SIZE_DATE_STAMP) * lpnrday)
        
        # for lp entries.. 
        last_adr = (adr_cluster + SIZE_CLUSTER - size_date_stamps -
                    SIZE_UNUSED_BYTE_EOC - self.size_lp_entry)

        cluster['last_adr'] = last_adr
        
        # and for time stamps to..
        last_adr_ts = (adr_cluster + SIZE_CLUSTER - size_date_stamps -
                       SIZE_UNUSED_BYTE_EOC - SIZE_TIME_STAMP - SIZE_STATUS -
                       SIZE_LPSNINT)
        
        cluster['last_adr_ts'] = last_adr_ts
        
        print('    lpnrday: %i' %cluster['lpnrday'])
        
        for ds in cluster['dateStamps']:
            print('    dateStamp: %s, offset: %s' %(ds['date'].date(),
                                                    hex(ds['offs'])))
        print('    last usable address for lp entries: %s' %hex(cluster['last_adr']))
        print('    last usable address for time stamps: %s' %hex(cluster['last_adr_ts']))
        
        return cluster
    
    
    
    def add_lp_data(self):
        print('\nread lp data..')
        self.lp = []
        
        # read lp data for every cluster with one or more date stamps
        for cluster in self.clusters:

            open_cluster = cluster  # this pointer is used to read over the
                                    # cluster end into next cluster..            
            
            print('read cluster at: %s..' %hex(cluster['first_adr']))
            for dateStamp in cluster['dateStamps']:
            
                # jump to start of entry
                idx = cluster['first_adr'] + dateStamp['offs'] * 2
                print('    datestamp: %s' 
                      %dateStamp['date'].strftime(DATE_FORMAT_NO_TIME))
                
                
                # jump to the start of the next cluster if not
                # enough space for one time stamp is left
                if idx > open_cluster['last_adr_ts']:
                    open_cluster = open_cluster['next_cluster']
                    if open_cluster:
                        idx = open_cluster['first_adr']
                    else:
                        # this was the last cluster
                        return               
                
                # read lpsnint
                lpsnint = int(self.eeprom_data[idx], 16)
                if lpsnint & 128:
                    # skip if entry is log
                    entry_type = 'log'
                    print('      %s is a logbook entry -> skip entry..'
                          %(hex(idx)))
                    continue
                
                entry_type = 'lp'
                
                # read time stamp
                idx += SIZE_LPSNINT
                try:
                    hh = int(self.eeprom_data[idx], 16) & 127
                    mm = int(self.eeprom_data[idx + 1])
                    ss = int(self.eeprom_data[idx + 2])

                    
                except ValueError:
                    # time stamp is invalid
                    print('      %s time stamp at is not BCD! (%s %s %s) -> skip entry..' 
                          %(hex(idx),
                            self.eeprom_data[idx],
                            self.eeprom_data[idx + 1],
                            self.eeprom_data[idx + 2]))
                    continue
                
                # generate time delta
                t_diff = timedelta(hours=hh, minutes=mm, seconds=ss)
                print('        timestamp: %s at adr: %s / %i entries'
                       %(t_diff, hex(idx), lpsnint))
                
                # read status byte
                idx += SIZE_TIME_STAMP
                status = int(self.eeprom_data[idx], 16)
                
                # read all lp intervalls following this time stamp.
                # generate a data set for every intervall
                idx += SIZE_STATUS
                
                for __ in range(lpsnint):
                    dataSet = {}
    
                    dataSet['status'] = str(StatusByte(status, self.elpsmod))
                    
                    dataSet['timeStamp'] = dateStamp['date'] + t_diff
                    t_diff += timedelta(minutes=self.elgint)
            
                    # jump to the start of the next cluster if not
                    # enough space for one entry left
                    if idx > open_cluster['last_adr']:
                        open_cluster = open_cluster['next_cluster']
                        if open_cluster:
                            idx = open_cluster['first_adr']
                        else:
                            # this was the last cluster
                            return
                        
                    dataSet['adr'] = idx
                
                    # read counter values
                    for ch in range(self.num_of_active_channels):
                        dataSet[ch] = ''
                        for __ in range(self.size_lp_channel):
                            dataSet[ch] += (self.eeprom_data[idx])
                            idx += 1
                        p = self.lp_decimal
                        dataSet[ch] = dataSet[ch][:p] + '.' + dataSet[ch][p:]
                    
                    self.lp.append(dataSet)
                    
    
    
    def __str__(self):
        s = 'adr;time;'
        for i in range(self.num_of_active_channels):
            s += MESSGROESSE_MAP[self.elpch[i]] + ';'
        s += 'status\n'
        for d in self.lp:
            s += (str(hex(d['adr'])) + ';' + str(d['timeStamp']) + ';')
            for i in range(self.num_of_active_channels):
                s += str(d[i]) + ';'
            s += str(d['status']) + '\n'
                
        return s           
    
# main -------------------------------------------------------------------------
if __name__ == '__main__':
    
    # parse arguments
    arg_parser = ArgParser()
    args = arg_parser.parse_args()
    
    sys.stdout = Logger(log_file, args.verbose)
    
    # read lines from input files
    print('read input data..')
    eeprom_data = EepromData(args)
    
    # create load profile from eeprom-data
    lp = LP(eeprom_data)


    # write csv
    if args.output:
        fname = args.output
    else:
        # read serial
        sn = (chr(int(eeprom_data[0x7A9], 16)) +
              chr(int(eeprom_data[0x7AA], 16)) +
              chr(int(eeprom_data[0x7AB], 16)) +
              chr(int(eeprom_data[0x7AC], 16)) +
              chr(int(eeprom_data[0x7AD], 16)) +
              chr(int(eeprom_data[0x7AE], 16)) +
              chr(int(eeprom_data[0x7AF], 16)) +
              chr(int(eeprom_data[0x7B0], 16)))
        
        fname = output_file.replace('serial', sn)
    
    try:
        f = open(fname, 'w')
        print('write lp to %s' %fname)
        f.write(str(lp))
    except PermissionError:
        sys.stderr.write('error: permission denied "%s"\n' %fname)
        sys.exit('abort program..')

