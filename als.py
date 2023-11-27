'''此文件是含寄存器的I2C设置类的标准写法，要点有枚举类型，命令码，掩码'''

from machine import SoftI2C,Pin
from collections import namedtuple
import time

class VEML7700: # 封装I2C所有通信的类
    '''

    '''
    # -----------枚举类型------------------------
    # 由于micropython暂无enum类型，使用显示定义namedtuple类型来代替
    # 参数合法判断可以由 value in namedtuple判断
    als_gain_t = namedtuple(
        "als_gain_t",
        [
            "ALS_GAIN_d8",
            "ALS_GAIN_d4",
            "ALS_GAIN_x1",
            "ALS_GAIN_x2",
            ]
        )(0x2,0x3,0x0,0x1)
    als_itime_t = namedtuple(
        "als_itime_t",
        [
            "ALS_INTEGRATION_25ms",
            "ALS_INTEGRATION_50ms",
            "ALS_INTEGRATION_100ms",
            "ALS_INTEGRATION_200ms",
            "ALS_INTEGRATION_400ms",
            "ALS_INTEGRATION_800ms",
         ]
    )(0xc,0x8,0x0,0x1,0x2,0x3)
    als_persist_t = namedtuple(
        "als_persist_t",
        [
             "ALS_PERSISTENCE_1",
             "ALS_PERSISTENCE_2",
             "ALS_PERSISTENCE_4",
             "ALS_PERSISTENCE_8",
        ]
    )(0x0,0x1,0x2,0x3)
    als_powmode_t = namedtuple(
        "als_powmod",
        [
            "ALS_POWER_MODE_1",
            "ALS_POWER_MODE_2",
            "ALS_POWER_MODE_3",
            "ALS_POWER_MODE_4",
        ]
    )(0x0,0x1,0x2,0x3)
    status = namedtuple(
        "status",
        [
            "STATUS_OK",
            "STATUS_ERROR"
        ]
    )(0x00,0xff)
    CMD = namedtuple("CMD",["cmd_index","mask","shift"])

    def __init__(self,i2c):
        self.i2c = i2c
        self.I2C_ADDRESS = 0x10
        self.CMD_ALS_GAIN = self.CMD(0x00,0x1800,11)
        self.CMD_ALS_IT = self.CMD(0x00,0x03c0,6)
        self.CMD_ALS_PERS = self.CMD(0x00,0x0030,4)
        self.CMD_ALS_INT_EN = self.CMD(0x00,0x0002,1)
        self.CMD_ALS_SD= self.CMD(0x00,0x0001,0)
        self.CMD_ALS_WH = 0x01
        self.CMD_ALS_WL = 0x02
        self.CMD_PSM = self.CMD(0x03,0x0006,1)
        self.CMD_PSM_EN = self.CMD(0x03,0x0001,0)
        self.CMD_ALS = 0x04
        self.CMD_WHITE = 0x05
        self.CMD_ALS_IF_L = self.CMD(0x06,0x8000,15)
        self.CMD_ALS_IF_H = self.CMD(0x06,0x4000,14)
        self.cmd_index = list(range(7))
        self.begin()

    def begin(self): # 共四个设置寄存器，且设备号由0到3，其中1，2为数值寄存器
        self.register_cache = [None,0x0000,0xffff,None] # regisster_cache用来储存设置寄存器信息
        self.register_cache[0] = \
            self.als_gain_t.ALS_GAIN_x2 << self.CMD_ALS_GAIN.shift \
            | self.als_itime_t.ALS_INTEGRATION_100ms << self.CMD_ALS_IT.shift \
            | self.als_persist_t.ALS_PERSISTENCE_1 << self.CMD_ALS_PERS.shift \
            | 0 << self.CMD_ALS_INT_EN.shift \
            | 0 << self.CMD_ALS_SD.shift # 设定初始值
        self.register_cache[3] = \
            self.als_powmode_t.ALS_POWER_MODE_3 << self.CMD_PSM.shift\
            | 0 << self.CMD_PSM_EN.shift
        for i in range(4):
            self.sendData(i,self.register_cache[i])
        # wait at least 2.5ms as per datasheet
        time.sleep(0.003)
    def __repr__(self):
        '''gain，IntegrationTime,resulotion'''
        ftmt = "VEML7700(on={},gain={},itime={},resulotion={},psmon={},powmod={},persist={},)"
        return ftmt.format(
            self.__getArg(self.CMD_ALS_SD) ^ 0x1,
            self.gain_str, 
            self.itime_str,
            self.getResolution(),
            self.getPowerSaving()[0],
            self.powmod_str,
            self.persist_str
            )
    @property
    def gain_str(self):
        return self.__attr_str(self.als_gain_t,self.getGain())
    @property
    def itime_str(self):
        return self.__attr_str(self.als_itime_t,self.getIntegrationTime())
    @property
    def powmod_str(self):
        return self.__attr_str(self.als_powmode_t,self.getPowerSaving()[1])
    @property
    def persist_str(self):
        return self.__attr_str(self.als_persist_t,self.getPersistence())
    
    def __attr_str(self,attr,attr_value):
        attr_strs = dir(attr)[1:]
        for a_str in attr_strs:
            if getattr(attr,a_str) == attr_value:
                return a_str
            raise RuntimeError(f"{attr_value} not exist in {attr}")
        
    def sendData(self,command,data):
        if command not in self.cmd_index[0:4]:
            raise ValueError("command")
        if not isinstance(data,int) or not (0x0000 <= data <= 0xffff):
            raise ValueError("data")
        return self.i2c.writeto_mem(self.I2C_ADDRESS,command,bytearray([data & 0xff,data >> 8]))
    def receiveData(self,command):
        if command not in self.cmd_index[4:]:
            raise ValueError("command")
        data = self.i2c.readfrom_mem(self.I2C_ADDRESS,command,2)
        data = data[0] + data[1] * 255
        return data
    def receiveData_into(self,command,data):
        if command not in self.cmd_index[0:4]:
            raise ValueError("command")
        if not isinstance(data,int) or not (0x0000 <= data <= 0xffff):
            raise ValueError("data")
        return self.i2c.readfrom_mem_into(self.I2C_ADDRESS,command,data)
    def __setArg(self,CMD,arg):
        reg = \
            (self.register_cache[CMD.cmd_index] & (CMD.mask^0xffff))\
            | ((arg << CMD.shift) & CMD.mask)
        self.register_cache[CMD.cmd_index] = reg
        return self.sendData(CMD.cmd_index,reg)
    def __getArg(self,CMD):
        return (self.register_cache[CMD.cmd_index] & CMD.mask) >> CMD.shift
    def setGain(self,gain):
        if gain not in self.als_gain_t:
            raise ValueError("gain")
        return self.__setArg(self.CMD_ALS_GAIN,gain)
    def getGain(self):
        return self.__getArg(self.CMD_ALS_GAIN)
    def setIntegrationTime(self,itime):
        if itime not in self.als_itime_t:
            raise ValueError("itime")
        return self.__setArg(self.CMD_ALS_IT,itime)
    def getIntegrationTime(self):
        return self.__getArg(self.CMD_ALS_IT)
    def setPersistence(self,persist):
        if persist not in self.als_persist_t:
            raise ValueError("persist")
        return self.__setArg(self.CMD_ALS_PERS,persist)
    def getPersistence(self):
        return self.__getArg(self.CMD_ALS_PERS)
    def setPowerSavingMode(self,powmode):
        if powmode not in self.als_powmode_t:
            raise ValueError("powmode")
        return self.__setArg(self.CMD_PSM,powmode)
    def setPowerSaving(self,enabled):
        if enabled not in [0,1]:
            raise ValueError("enable")
        return self.__setArg(self.CMD_PSM_EN,enabled)
    def getPowerSaving(self):
        powmod = self.__getArg(self.CMD_PSM)
        ison = self.__getArg(self.CMD_PSM_EN)
        return ison,powmod
    def setInterrupts(self,enabled):
        if enabled not in [0,1]:
            raise ValueError('enabled')
        return self.__setArg(self.CMD_ALS_INT_EN,enabled)
    def setPower(self,on):
        '''1 is on ,0 is down,不同于文档'''
        if on not in [0,1]:
            raise ValueError("on")
        self.__setArg(self.CMD_ALS_SD,on ^ 0x1)
        if on:
            time.sleep(0.003)
    def setALSHighThreshold(self,thresh):
        return self.sendData(self.CMD_ALS_WH,thresh)
    def setALSLowThreshold(self,thresh):
        return self.sendData(self.CMD_ALS_WL,thresh)
    def getALS(self):
        return self.receiveData(self.CMD_ALS)
    def getWhite(self):
        return self.receiveData(self.CMD_WHITE)
    def getHighThresholdEvent(self):
        reg = self.receiveData(self.CMD_ALS_IF_H)
        return reg & self.CMD_ALS_IF_H.mask >> self.CMD_ALS_IF_H.shift
    def getLowThresholdEvent(self):
        reg = self.receiveData(self.CMD_ALS_IF_L)
        return reg & self.CMD_ALS_IF_L.mask >> self.CMD_ALS_IF_L.shift
    def getResolution(self):
        gain = self.getGain() & 0x3
        itime = self.getIntegrationTime()
        if gain == self.als_gain_t.ALS_GAIN_x1:
            factor1 = 1.0
        elif gain == self.als_gain_t.ALS_GAIN_x2:
            factor1 = 0.5
        elif gain == self.als_gain_t.ALS_GAIN_d8:
            factor1 = 8.0
        elif gain == self.als_gain_t.ALS_GAIN_d4:
            factor1 = 4.0
        else:
            factor1 = 1.0
        if itime == self.als_itime_t.ALS_INTEGRATION_25ms:
            factor2 = 0.2304
        elif itime == self.als_itime_t.ALS_INTEGRATION_50ms:
            factor2 = 0.1152
        elif itime == self.als_itime_t.ALS_INTEGRATION_100ms:
            factor2 = 0.0576
        elif itime == self.als_itime_t.ALS_INTEGRATION_200ms:
            factor2 = 0.0288
        elif itime == self.als_itime_t.ALS_INTEGRATION_400ms:
            factor2 = 0.0144
        elif itime == self.als_itime_t.ALS_INTEGRATION_800ms:
            factor2 = 0.0072
        else:
            factor2 = 0.2304
        return factor1 * factor2
    def scaleLux(self,raw_counts):
        resolution = self.getResolution()
        lux = raw_counts * resolution

        lux = lux * (1.0023 + lux * (8.1488e-5 + lux * (-9.3924e-9 + lux * 6.0135e-13)))
        
        return lux
    def getALSLux(self):
        raw_counts = self.getALS()
        return self.scaleLux(raw_counts)
    def getWhiteLux(self):
        raw_counts = self.getWhite()
        return self.scaleLux(raw_counts)
    def getAutoXLux(self,counts_func):
        gains = self.als_gain_t
        itimes = self.als_itime_t
        counts_threshold = 200
        self.setPower(0)
        for itime_idx in range(2,6):
            self.setIntegrationTime(itime=itimes[itime_idx])
            for gain_idx in range(0,4):
                self.setGain(gains[gain_idx])
                self.setPower(1)
                self.sampleDelay()
                raw_counts = counts_func()
                if raw_counts > counts_threshold:
                    while(itime_idx > 0):
                        if raw_counts < 10000:
                            return self.scaleLux(raw_counts=raw_counts)
                        self.setPower(0)
                        itime_idx -= 1
                        self.setIntegrationTime(itimes[itime_idx])
                        self.setPower(1)
                        self.sampleDelay()
                        raw_counts = counts_func()
                    return self.scaleLux(raw_counts=raw_counts)
                
                self.setPower(0)
        return self.scaleLux(raw_counts)
    def getAutoALSLux(self):
        return self.getAutoXLux(counts_func=self.getALS)
    def getAutoWhiteLux(self):
        return self.getAutoXLux(counts_func=self.getWhite)
    def sampleDelay(self):
        '''根据itime值等待'''
        itime = self.getIntegrationTime()
        if itime == self.als_itime_t.ALS_INTEGRATION_25ms:
            time.sleep(2*0.025)
        elif itime == self.als_itime_t.ALS_INTEGRATION_50ms:
            time.sleep(2*0.050)
        elif itime == self.als_itime_t.ALS_INTEGRATION_100ms:
            time.sleep(2*0.100)
        elif itime == self.als_itime_t.ALS_INTEGRATION_200ms:
            time.sleep(2*0.200)
        elif itime == self.als_itime_t.ALS_INTEGRATION_400ms:
            time.sleep(2*0.400)
        elif itime == self.als_itime_t.ALS_INTEGRATION_800ms:
            time.sleep(2*0.800)
        else:
            time.sleep(2*0.100)



if __name__ == '__main__':
    #
    i2c = SoftI2C(scl = Pin(18),sda = Pin(19),freq = 400000)
    als = VEML7700(i2c)
    #
    while True:
        print(f"lux:{als.getAutoALSLux():10}")
        time.sleep(1)
    
