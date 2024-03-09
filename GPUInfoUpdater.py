import socket
import pynvml
from pyzabbix import ZabbixMetric, ZabbixSender, ZabbixAPI


class ZabbixLoader(object):
    default_zabbix_groups = 'Linux servers'
    hostname = socket.gethostname()

    def __init__(self, zabbix_server):
        self.zabbix_api = ZabbixAPI(url=f'http://{zabbix_server}:8080/', user='Admin', password='zabbix', )
        self.zabbix_sender = ZabbixSender(zabbix_server=zabbix_server, zabbix_port=10051)
        self.zabbix_host_id = self._zabbix_host_id()

    def _zabbix_groupid(self):
        params = {
            "output": ["groupid"],
            "filter": {
                "name": [self.default_zabbix_groups]
            }
        }
        result = self.zabbix_api.do_request('item.get', params)
        if result['result']:
            return result['result'][0]['groupid']
        else:
            raise 'please create host group in web console.'

    def _zabbix_host_id(self):
        params = {
            "output": ["hostid", 'name'],
            'filter': {"name": self.hostname}
        }
        result = self.zabbix_api.do_request('host.get', params)
        if result['result']:
            return result['result'][0]['hostid']
        else:
            # 注册 host
            params = {
                "host": self.hostname,
                "groups": self._zabbix_groupid(),
            }
            self.zabbix_api.do_request('host.create', params)

    def _zabbix_host_key_exist(self, key):
        params = {
            "output": ["hostid", 'name', 'itemid'],
            'filter': {"key_": key, 'host': self.hostname}
        }
        result = self.zabbix_api.do_request('item.get', params)
        if result['result']:
            return True
        else:
            return False

    @staticmethod
    def _check_item_unit(key):
        unit = None
        if key.endswith('percent'):
            return ''
        elif 'mem' in key:
            return 'B'
        elif 'temperature' in key:
            return '℃'
        elif 'powerusage' in key:
            return 'W'
        else:
            return unit

    @staticmethod
    def _check_item_value_type(key):
        '''
        0 - 浮点型；
        1 - 字符；
        2 - 日志；
        3 - 无符号数字；
        4 - 文本。
        '''
        if 'name' in key:
            return 4
        if 'num' in key or 'count' in key:
            return 3
        elif key.endswith('percent') or 'mem' or 'temperature' or 'powerusage' in key:
            return 0
        else:
            return 4

    def _regist_key(self, key):
        params = {
            "name": key,
            "key_": key,
            "hostid": self.zabbix_host_id,
            "type": 2,
            "value_type": self._check_item_value_type(key),
            "units": self._check_item_unit(key),
            "delay": "30s"
        }
        self.zabbix_api.do_request('item.create', params)

    def send2zabbix(self, packet):
        for x in packet:
            if not self._zabbix_host_key_exist(x.key):
                self._regist_key(x.key)
        result = self.zabbix_sender.send(packet)
        print(result)


class GPUInfoUpdater(object):
    hostname = socket.gethostname()

    def get_nv_info(self):
        packet = []
        pynvml.nvmlInit()
        device_count = pynvml.nvmlDeviceGetCount()
        packet.append(
            ZabbixMetric(self.hostname, 'gpu.num', device_count)
        )
        for i in range(device_count):
            handle = pynvml.nvmlDeviceGetHandleByIndex(i)
            gpu_name = pynvml.nvmlDeviceGetName(handle)
            mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            temperature = pynvml.nvmlDeviceGetTemperature(handle, 0)
            powerusage = pynvml.nvmlDeviceGetPowerUsage(handle)
            packet.extend(
                [ZabbixMetric(self.hostname, f'gpu.{str(i)}.name', gpu_name.decode('utf-8')),
                 ZabbixMetric(self.hostname, f'gpu.{str(i)}.powerusage', powerusage / 1000),
                 ZabbixMetric(self.hostname, f'gpu.{str(i)}.temperature', temperature),
                 ZabbixMetric(self.hostname, f'gpu.{str(i)}.mem.total', mem_info.total),
                 ZabbixMetric(self.hostname, f'gpu.{str(i)}.mem.free', mem_info.free),
                 ZabbixMetric(self.hostname, f'gpu.{str(i)}.mem.used', mem_info.used),
                 ZabbixMetric(self.hostname, f'gpu.{str(i)}.mem.used.percent', mem_info.used / mem_info.total),
                 ])
        pynvml.nvmlShutdown()
        packet.extend(
            [ZabbixMetric(self.hostname, f'gpu.all.powerusage',
                          sum([float(x.value) for x in packet if 'powerusage' in x.key])),
             ZabbixMetric(self.hostname, f'gpu.all.temperature.max',
                          max([float(x.value) for x in packet if 'temperature' in x.key])),
             ZabbixMetric(self.hostname, f'gpu.all.mem.total',
                          sum([float(x.value) for x in packet if 'mem.total' in x.key])),
             ZabbixMetric(self.hostname, f'gpu.all.mem.free',
                          sum([float(x.value) for x in packet if 'mem.free' in x.key])),
             ZabbixMetric(self.hostname, f'gpu.all.mem.used',
                          sum([float(x.value) for x in packet if 'mem.used' in x.key])),
             ZabbixMetric(self.hostname, f'gpu.all.mem.used.percent',
                          sum([float(x.value) for x in packet if 'mem.used' in x.key]) / sum(
                              [float(x.value) for x in packet if 'mem.total' in x.key])),
             ])
        return packet
