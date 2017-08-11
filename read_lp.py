import os

# location = 'Z:\\Mitarbeiter\\Q-Faelle\\Kundenreparaturen\\660.9077527\\'
location = 'C:\\Users\\florian.hofmaier\\Documents\\660.9077527\\'


LP_START = 0x5600       # ohne vorwerte!!
SIZE_CLUSTER = 0x200

SIZE_EEPROM_0 = 0x7FFF
SIZE_EEPROM_1 = 0xFFFF
SIZE_EEPROM_2 = 0xFFFF

DISFLG = 0x051B

ELPSMOD = 0x0789

DPLOCE = 0x04C1
DPLOCD = 0x04C2

DISFLG_EE = 0b11000000
DISFLG_DD = 0b00110000
DISFLG_CC = 0b00001100
DPLOCE_DDD = 0b00000011
DPLOCD_DDD = 0b00000011
ELPSMOD_LPREGS = 0b00100000
ELPSMOD_LPENER = 0b00010000


ELPCH = (0x0787,
         0x0788,
         0x078A,
         0x078B,
         0x078C,
         0x078D,
         0x0790,
         0x0791)

ELGINT = 0x078E     # LP interval

EUISIZE = 0x079A


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
                   0x40: '-P',
                   0x80: '+P'}

def file2List(fname, prefix):
    f = open(fname)
    l = [prefix + line[:53] for line in f.readlines()]
    return l

def list2file(l, fname):
    f = open(fname, 'w')
    for line in l:
        f.write("%s\n" % line)

def list2Map(l):
    m = dict()
    offs = 6
    for line in l:
        adr = int(line[:5], 16)
        for byte in range(16):
            idx = offs + byte * 3
            m[adr] = line[idx:idx + 2]
            adr += 1
    return m
            

class LP():

    def __init__(self, m):
        self.lp = []
        
        # read active channels
        print('check active lp channels..')
        elpch = []
        self.num_of_active_channels = 0
        for adr in ELPCH:
            elpch.append(int(m[adr], 16))
            print('    ', hex(adr), ' elpch', len(elpch), ': ', m[adr],
                  ' (\'', MESSGROESSE_MAP[int(m[adr], 16)], '\')', sep='')
            if elpch[-1]:
                self.num_of_active_channels += 1
        print('    ....found', self.num_of_active_channels, 'active channels')
        
        # check data format
        print('check data format...')
        param = int(m[DISFLG], 16)
        # anzahl stellen Energieregister
        self.disflg_ee = (param & DISFLG_EE) >> 6
        # anzahl stellen Leistungsregister
        self.disflg_dd = (param & DISFLG_DD) >> 4
        # anzahl stellen kumulativ register
        self.disflg_cc = (param & DISFLG_CC) >> 2
        
        # nachkommastellen energieregister
        self.dploce_ddd = int(m[DPLOCE], 16) & DPLOCE_DDD
        # nachkommastellen leistungsregister
        self.dplocd_ddd = int(m[DPLOCD], 16) & DPLOCD_DDD
        
        # read lp data type and define format
        self.elpsmod_lpregs = int(m[ELPSMOD], 16) & ELPSMOD_LPREGS
        self.elpsmod_lpener = int(m[ELPSMOD], 16) & ELPSMOD_LPENER
        if self.elpsmod_lpregs:
            self.lp_type = 'Energieregister'
            self.lp_entry_size = (N_DIGITS_EREGS[self.disflg_ee] + 2 // 2) // 2
            self.lp_decimal = self.dploce_ddd
            
        elif self.elpsmod_lpener:
            self.lp_type = 'Ernergievorschub'
            if self.disflg_cc < 0b10:
                self.lp_entry_size = (N_DIGITS_ENER[self.disflg_ee] + 2 // 2) // 2
            else:
                self.lp_entry_size = (N_DIGITS_ENER[self.disflg_cc] + 2 // 2) // 2
            self.lp_decimal = self.dploce_ddd
            
        else:
            self.lp_type = 'Leistungsmittelwerte'
            
            self.lp_entry_size = (N_DIGITS_PWR[self.disflg_dd] + 2 // 2) // 2
            self.lp_decimal = self.dplocd_ddd
            
            
        print('    type:', self.lp_type)
        print('    entry size:', self.lp_entry_size)
        print('    decimal point number:', self.lp_decimal)
                
        # check interval size
        self.elgint = int(m[ELGINT], 16)
        print('lp interval:', self.elgint, 'min')
        
        # check start adress for lp
        self.euisize = int(m[EUISIZE], 16)
        start_adr = LP_START + self.euisize * SIZE_CLUSTER
        
        # read clusters, add lp data
        if start_adr < SIZE_EEPROM_0:
            # lp starts in first eeprom
            print('start adress: ', hex(start_adr))
            for cluster_adr in range(start_adr, SIZE_EEPROM_0, SIZE_CLUSTER):
                self.add_data(m, cluster_adr)
            for cluster_adr in range(0x10000, 0x2FFFF, SIZE_CLUSTER):
                self.add_data(m, cluster_adr)
        else:
            start_adr += 0x8000
            print('start adress: ', hex(start_adr))
            for cluster_adr in range(start_adr, 0x2FFFF, SIZE_CLUSTER):
                self.add_data(m, cluster_adr)
            
        
        
    def calcTimeStamp(self, t_stamp, interval):
        hh = t_stamp[0]
        mm = t_stamp[1]
        ss = t_stamp[2]
        
        m = mm + interval
        h = hh
        if m > 59:
            h += m // 60
            m %= 60
        if h > 24:
            h -= 24
        timeStamp_new = {'hh': h, 'mm': m, 'ss': ss}
        return timeStamp_new
    
    
    def dateStamp2Str(self, stamp):
        s = ('' + str(stamp['yy']) + '/' + str(stamp['mm']) + '/' + 
             str(stamp['dd']))
        return s
    
    
    def add_data(self, m, adr):
        print('check cluster at: ', hex(adr))
        
        # read all date stamps in this cluster
        lpnrday = int(m[adr + SIZE_CLUSTER - 2], 16)
        if lpnrday == 0:
            lpnrday += 1
        list_of_dateStamps = []
        try:
            for i in range(lpnrday):
                stamp = dict()
                stamp['oo'] = int(m[adr + SIZE_CLUSTER - 2 - 4 * (i + 1)], 16)
                stamp['yy'] = int(m[adr + SIZE_CLUSTER - 2 - 4 * (i + 1) + 1])
                stamp['mm'] = int(m[adr + SIZE_CLUSTER - 2 - 4 * (i + 1) + 2])
                stamp['dd'] = int(m[adr + SIZE_CLUSTER - 2 - 4 * (i + 1) + 3])
                list_of_dateStamps.append(stamp)
        except ValueError:
            # illegal daystamp
            print('    ..!error: daystamp is not bcd !')
            return
        
        s = [self.dateStamp2Str(i) for i in list_of_dateStamps]
        print('    ..found ', lpnrday, ' date stamps: ', s)
        
        # for every day stamp in cluster do..
        for dateStamp in list_of_dateStamps:
            idx = adr + dateStamp['oo'] * 2
            lpsnint = int(m[idx], 16)
            
            if lpsnint & 128:
                entry = 'log'
            else:
                entry = 'lp'
                
                # read time stamp
                try:
                    idx += 1
                    hh = int(m[idx])
                    mm = int(m[idx + 1])
                    ss = int(m[idx + 2])
                except ValueError:
                    print('    ..!error: time stamp at', hex(idx),
                          'is not BCD! (', m[idx], m[idx + 1],
                          m[idx + 2], ')')
                    print('    ..skip cluster!')
                    continue
                # read status byte
                idx += 3
                status = int(m[idx], 16)
                
                # read all lp intervalls following this time stamp.
                # generate a data set for every intervall
                idx += 1
                for i in range(lpsnint):
                    dataSet = dict()
                    dataSet['status'] = status
                    dataSet['date'] = dateStamp
                    dataSet['adr'] = idx
                    # calc time stamp for every data set
                    dataSet['time'] = self.calcTimeStamp(
                        (hh, mm, ss), i * self.elgint)
                    
                    # read counter values
                    for ch in range(self.num_of_active_channels):
                        dataSet[ch] = []
                        for data in range(self.lp_entry_size):
                            dataSet[ch].append(m[idx])
                            idx += 1
                    # print(dataSet)
                    self.lp.append(dataSet)
        
        
    def writeCsv(self):
        pass

    def __str__(self):
        s = ''
        for d in self.lp:
            s += (str(hex(d['adr'])) + ': ' + str(d['date']['yy']) + 
                '/' + str(d['date']['mm']) + '/' + 
                str(d['date']['dd']) + ' ' + str(d['time']['hh']) + ':' + 
                str(d['time']['mm']) + ':' + str(d['time']['ss']) + ' ')
            for i in range(self.num_of_active_channels):
                s += str(d[i]) + ' '
            s += ' ' + 'status: ' + str(d['status']) + '\r'
                
        return s



if __name__ == '__main__':
    
    # read files line by line
    lines = [] + file2List(location + '0xA0.txt', '0')
    lines += (file2List(location + '0xA2.txt', '1'))
    lines += (file2List(location + '0xA4.txt', '2'))
    
    print(len(lines), ' lines and ', len(lines) * 16, ' adresses read..')
    
    # save all lines to file
    # list2file(lines, location + 'bkp.txt')
    
    # create adress-map
    m = list2Map(lines)
    
    # create lp
    lp = LP(m)
    print(lp)