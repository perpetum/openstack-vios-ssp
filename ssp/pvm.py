#import paramiko
#ssh=paramiko.SSHClient()
#ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())



class get_vios_data(object):

    def __init__(self):
        pass


    def calc_disks_on_adapter(self, target_machine, target_hmc, connection_string, hmc_user, hmc_pass, vios_id, vios_vhost):
	connection_string.connect(target_hmc, username=hmc_user, password=hmc_pass)
	stdin,stdout,stderr = connection_string.exec_command("viosvrcmd  -m " + target_machine + " --id " + vios_id + " -c 'lsmap -vadapter " + vios_vhost + " -field vtd -fmt ,'")
	data = stdout.readlines()
	connection_string.close()
	return data


    def get_mapping_list_for_vios(self, target_machine, target_hmc, connection_string, hmc_user, hmc_pass, lpar_id, vios_name ):
	
	connection_string.connect(target_hmc, username=hmc_user, password=hmc_pass)
        stdin,stdout,stderr = connection_string.exec_command("lshwres  --rsubtype scsi  -m " + target_machine + " -r virtualio --filter lpar_ids=" + lpar_id + " -F slot_num,remote_lpar_name,remote_slot_num,remote_lpar_id")
	data = stdout.readlines()
	connection_string.close()
	result = []
	for line in data:
		if vios_name in line:
			result.append(line)
	return result


    def find_smallest_disk_adapter(self, target_machine, target_hmc, connection_string, hmc_user, hmc_pass, lpar_id, vios_name ):
	
	adapter_list = self.get_mapping_list_for_vios(target_machine=target_machine, target_hmc=target_hmc, connection_string=connection_string, hmc_user=hmc_user, hmc_pass=hmc_pass, lpar_id=lpar_id, vios_name=vios_name )
	# perpetum: example [u'6,SBT-PROMETEY-VIO06,2062,2\n', u'4,SBT-PROMETEY-VIO06,2061,2\n']
	vios_adapters = dict()
	for item in adapter_list:
		item = item.strip()
		item = item.split(',')
		map_num = item[2]
		vios_id = item[3]
		lpar_adapter_num = item[0]
		adapter_name = self.get_vadapter_vhost(target_machine=target_machine, target_hmc=target_hmc, connection_string=connection_string, hmc_user=hmc_user, hmc_pass=hmc_pass, lpar_id=vios_id, map_num=map_num)
		disk_list = self.calc_disks_on_adapter(target_machine=target_machine, target_hmc=target_hmc, connection_string=connection_string, hmc_user=hmc_user, hmc_pass=hmc_pass, vios_id=vios_id, vios_vhost=adapter_name)
		disk_list = disk_list[0].split(',')
		num_of_disks = len(disk_list)
		vios_adapters.update({ adapter_name : num_of_disks })
	smallest = min(vios_adapters, key=vios_adapters.get)
	
	return smallest, lpar_adapter_num

	
    def get_vadapter_vhost(self, target_machine, target_hmc, connection_string, hmc_user, hmc_pass, lpar_id, map_num ):
	
        map_num = str(map_num)
        connection_string.connect(target_hmc, username=hmc_user, password=hmc_pass)
        stdin,stdout,stderr = connection_string.exec_command("lshwres  -m " + target_machine + " -r virtualio --rsubtype slot  --level slot  --filter lpar_ids="+lpar_id+", slots="+map_num+" -F drc_name")
        vio_plc = stdout.readlines()
        vio_plc = str(vio_plc[0].strip())
        stdin,stdout,stderr = connection_string.exec_command("viosvrcmd  -m " + target_machine + " --id " + lpar_id + " -c 'lsmap -plc " + vio_plc + " -field svsa -fmt :'")
        vios_vhost = stdout.readlines()
        vios_vhost = str(vios_vhost[0].strip())
        connection_string.close()
        return(vios_vhost)



class set_vios_data(object):

    def __init__(self):
        pass

    def create_vlun(self, target_machine, target_hmc, connection_string, hmc_user, hmc_pass, vios_name, vlun_name, vlun_size_gb, *args):
        connection_string.connect(target_hmc, username=hmc_user, password=hmc_pass)
	command = "viosvrcmd  -m " + target_machine + " -p " + vios_name + " -c \"lu -create -lu " + vlun_name + " -size " + vlun_size_gb + "G\""
        stdin,stdout,stderr = connection_string.exec_command(command)
	result = stdout.readlines()
        connection_string.close()
	try:
		for line in result:
			if 'Udid' in line:
				line = line.split(':')
				udid = line[-1]
	
		return udid, True
	except Exception:
		return result, False

    def map_vlun(self, target_machine, target_hmc, connection_string, hmc_user, hmc_pass, vios_name, vios_luudid, vios_vhost, *args):
        connection_string.connect(target_hmc, username=hmc_user, password=hmc_pass)
        stdin,stdout,stderr = connection_string.exec_command("viosvrcmd  -m " + target_machine + " -p " + vios_name + " -c \"lu -map -luudid " + vios_luudid + " -vadapter " + vios_vhost +  "\"" )
        result = stdout.readlines()
        connection_string.close()
	for line in result:
		if 'VTD' in line:
			result = line.strip()
	return result


    def unmap_vlun(self, target_machine, target_hmc, connection_string, hmc_user, hmc_pass, vios_name, vios_vtd, *args):
        connection_string.connect(target_hmc, username=hmc_user, password=hmc_pass)
        stdin,stdout,stderr = connection_string.exec_command("viosvrcmd  -m " + target_machine + " -p " + vios_name + " -c \"rmvdev -vtd " + vios_vtd + "\"" )
        result = stdout.readlines()
        connection_string.close()
	try:
        	for line in result:
                	if 'deleted' in line:
                        	result = line.strip()
        	return line, True
	except Exception:
                return result, False



    def remove_vlun(self, target_machine, target_hmc, connection_string, hmc_user, hmc_pass, vios_name, vlun_name, vios_luudid, *args):
# Perpetum TBD : lu and luudid are mutually exclusive. Need to modify code to reduce args
        connection_string.connect(target_hmc, username=hmc_user, password=hmc_pass)
        command = "viosvrcmd  -m " + target_machine + " -p " + vios_name + " -c \"lu -remove -luudid " + vios_luudid + "\""
        stdin,stdout,stderr = connection_string.exec_command(command)
        result = stdout.readlines()
        connection_string.close()
        try:
                for line in result:
                        if 'udid' in line:
                                line = line.split(':')
                                udid = line[-1]

                return udid, True
        except Exception:
                return result, False


    def extend_vlun(self, target_machine, target_hmc, connection_string, hmc_user, hmc_pass, vios_name, vlun_name, vios_luudid, new_size, *args):
# Perpetum TBD : lu and luudid are mutually exclusive. Need to modify code to reduce args
        connection_string.connect(target_hmc, username=hmc_user, password=hmc_pass)
        command = "viosvrcmd  -m " + target_machine + " -p " + vios_name + " -c \"lu -resize -luudid " + vios_luudid + " -size " + new_size + "G\""
        stdin,stdout,stderr = connection_string.exec_command(command)
        result = stdout.readlines()
        connection_string.close()
        try:
                for line in result:
                        if 'successfully' in line:
                                line = line.split(':')
                                udid = line[-1]

                return udid, True
        except Exception:
                return result, False




class get_machine_data(object):

    def __init__(self):
        pass

    def get_vios_list(self, target_machine, target_hmc, hmc_pass, hmc_user, connection_string):
        connection_string.connect(target_hmc, username=hmc_user, password=hmc_pass)
        stdin,stdout,stderr = connection_string.exec_command("lssyscfg -m "+ target_machine + " -r lpar -F lpar_env,name | grep vioserver | sed s/vioserver,//g | sort")
        vios_list = stdout.readlines()
        connection_string.close()
        return(vios_list)


    def get_machine_serial(self, target_machine, target_hmc, connection_string, hmc_user, hmc_pass ):
        connection_string.connect(target_hmc, username=hmc_user, password=hmc_pass)
        stdin,stdout,stderr = connection_string.exec_command("lssyscfg -m "+ target_machine + " -r sys  -F serial_num")
        machine_serial = stdout.readlines()
        machine_serial = str(machine_serial[0].strip())
        connection_string.close()
        return(machine_serial)


    def get_machine_type_model(self, target_machine, target_hmc, connection_string, hmc_user, hmc_pass  ):
        connection_string.connect(target_hmc, username=hmc_user, password=hmc_pass)
        stdin,stdout,stderr = connection_string.exec_command("lssyscfg -m "+ target_machine + " -r sys  -F type_model")
        machine_type_model = stdout.readlines()
        machine_type_model = str(machine_type_model[0].strip())
        connection_string.close()
        return(machine_type_model)


    def get_lpar_id(self,  target_machine, target_hmc, connection_string, lpar_name, hmc_user, hmc_pass ):
        connection_string.connect(target_hmc, username=hmc_user, password=hmc_pass)
        stdin,stdout,stderr = connection_string.exec_command("lssyscfg -m "+ target_machine + " -r lpar --filter lpar_names="+lpar_name + " -F lpar_id")
        lpar_id = stdout.readlines()
        lpar_id = str(lpar_id[0].strip())
        connection_string.close()
        return(lpar_id)

    def get_machine_name(self, machine_serial, target_hmc, connection_string, hmc_user, hmc_pass):
        connection_string.connect(target_hmc, username=hmc_user, password=hmc_pass)
        stdin,stdout,stderr = connection_string.exec_command("lssyscfg -r sys  -F name:serial_num:state")
        result = stdout.readlines()
        for item in result :
            item = item.split(':')
            if machine_serial == item[1].strip() and 'Operating' == item[2].strip():
                machine_name= item[0]
        return machine_name

