import time

from GPUInfoUpdater import GPUInfoUpdater, ZabbixLoader


def main(gap=60):
    zabbix_url = '172.16.5.242'
    zabbix_loader = ZabbixLoader(zabbix_url)
    gpu_info_updater = GPUInfoUpdater()

    while True:
        print('----- timestemp', time.time())
        gpu_info = gpu_info_updater.get_nv_info()
        zabbix_loader.send2zabbix(gpu_info)
        time.sleep(gap)


main()
