# Copyright 2016 Dell Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#

"""
Core backend volume driver interface.

All backend drivers should support this interface as a bare minimum.
"""

import re

from cinder.volume.drivers.ssp import pvm as pvmlib
from cinder import exception

from cinder.interface import base
#from cinder.volume import driver
#from cinder import interface

#from cinder import objects
#from cinder import utils
#from cinder.volume import driver


from oslo_concurrency import processutils
from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import excutils
from oslo_utils import importutils
from oslo_utils import units

from cinder.i18n import _


import paramiko


from sqlalchemy import create_engine, Date, Column, Integer, String

from sqlalchemy.orm import sessionmaker

from sqlalchemy.ext.declarative import declarative_base



volume_opts = [
    cfg.StrOpt('filter_function',
               help='String representation for an equation that will be '
                    'used to filter hosts. Only used when the driver '
                    'filter is set to be used by the Cinder scheduler.'),

    cfg.StrOpt('volume_backend_name',
                                default='ABC_123',
                                help='default cluster name to create volumes'),

    cfg.StrOpt('goodness_function',
               help='Similar to filter_function, but used to weigh multiple volume'
                        'backends. Example: '
                        'capabilities.capacity_utilization < 0.6 ? 100 : 25'),


    cfg.StrOpt('hmc_ip',
                                default='1.1.2.1',
                                help='IP address of LPARs  managing HMC '),

    cfg.StrOpt('hmc_user',
                                default='hscroot',
                                help='user of  managing HMC '),


    cfg.StrOpt('hmc_pass',
                                default='abc123',
                                help='pass of managing HMC '),

   cfg.StrOpt('vios_serial_nums',
                                default='000000',
                                help='List of VIOS(Machine) serial nums')

]


sbt_opts =  [
	cfg.StrOpt('vios_cluster',
               help='Similar to filter_function, but used to weigh multiple volume'),

]

CONF = cfg.CONF
CONF.register_opts(sbt_opts, 'sbt_driver')

volume_backend_name =  CONF.sbt_driver.vios_cluster

CONF.register_opts(volume_opts, volume_backend_name)

### Perpetum: Section to convert uniq backend_nae to common name 
# in order to get backend_data properties

cinder_driver_section = eval('CONF.'+ volume_backend_name )


LOG = logging.getLogger(__name__)



POWER_MACHINE = pvmlib.get_machine_data()
SSP_VIOS_WRITE = pvmlib.set_vios_data()
SSP_VIOS_READ = pvmlib.get_vios_data()

ssh=paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())


Base = declarative_base()

class ssp_volume_metadata(Base):

	__tablename__ = 'volume_metadata'
        id = Column(Integer, primary_key=True)
        updated_at =  Column(Date)
        deleted_at =  Column(Date)
        deleted = Column(Integer)
        volume_id = Column(String(36))
	key = Column(String(255))
	value = Column(String(255))




class VolumeDriverCore(base.CinderInterface):
    """Core backend driver required interface."""
    """Executes commands relating to Volumes."""
    SUPPORTED = True

    def __init__(self,  *args, **kwargs):
	self.configuration = kwargs.get('configuration', None)
	self.configuration.append_config_values(volume_opts)
	self.configuration.enable_unsupported_driver = True
	self.supported = kwargs.get('supported')
	self.supported = True
	self.capabilities = {}
	self.database_connection = CONF.database.connection

	self.engine = create_engine(self.database_connection, echo=False)

	



    def get_version(self):
	version = '0.2'
	return version

    def _set_property(self, properties, entry, title, description,
                      type, **kwargs):
        prop = dict(title=title, description=description, type=type)
        allowed_keys = ('enum', 'default', 'minimum', 'maximum')
        for key in kwargs:
            if key in allowed_keys:
                prop[key] = kwargs[key]
        properties[entry] = prop

    def _get_backend_name(self):
#	volume_backend_name = CONF.emc_cluster1.volume_backend_name
	return volume_backend_name

# TBD

    def get_filter_function(self):
        """Get filter_function string.

        Returns either the string from the driver instance or global section
        in cinder.conf. If nothing is specified in cinder.conf, then try to
        find the default filter_function. When None is returned the scheduler
        will always pass the driver instance.

        :returns: a filter_function string or None
        """
        ret_function = self.configuration.filter_function
        if not ret_function:
            ret_function = CONF.filter_function
        if not ret_function:
            ret_function = self.get_default_filter_function()
        return ret_function
# TBD
    def get_goodness_function(self):
        """Get good_function string.

        Returns either the string from the driver instance or global section
        in cinder.conf. If nothing is specified in cinder.conf, then try to
        find the default goodness_function. When None is returned the scheduler
        will give the lowest score to the driver instance.

        :returns: a goodness_function string or None
        """
        ret_function = self.configuration.goodness_function
        if not ret_function:
            ret_function = CONF.goodness_function
        if not ret_function:
            ret_function = self.get_default_goodness_function()
        return ret_function
# TBD
    def get_default_filter_function(self):
        """Get the default filter_function string.

        Each driver could overwrite the method to return a well-known
        default string if it is available.

        :returns: None
        """
        return None

# TBD
    def get_default_goodness_function(self):
        """Get the default goodness_function string.

        Each driver could overwrite the method to return a well-known
        default string if it is available.

        :returns: None
        """
        return None



    def init_capabilities(self):
	volume_backend_name = self._get_backend_name()
	self.capabilities = {'volume_backend_name': volume_backend_name } 


    def update_provider_info(self, volumes, snapshots):
        """Get provider info updates from driver.

        :param volumes: List of Cinder volumes to check for updates
        :param snapshots: List of Cinder snapshots to check for updates
        :returns: tuple (volume_updates, snapshot_updates)

        where volume updates {'id': uuid, provider_id: <provider-id>}
        and snapshot updates {'id': uuid, provider_id: <provider-id>}
        """
        return None, None


    def set_throttle(self):
	pass

    def set_initialized(self):
        self._initialized = True

#    @property
    def initialized(self):
        return self._initialized


    def do_setup(self, context):
        """Any initialization the volume driver needs to do while starting.

        Called once by the manager after the driver is loaded.
        Can be used to set up clients, check licenses, set up protocol
        specific helpers, etc.

        :param context: The admin context.
        """

    def check_for_setup_error(self):
        """Validate there are no issues with the driver configuration.

        Called after do_setup(). Driver initialization can occur there or in
        this call, but must be complete by the time this returns.

        If this method raises an exception, the driver will be left in an
        "uninitialized" state by the volume manager, which means that it will
        not be sent requests for volume operations.

        This method typically checks things like whether the configured
        credentials can be used to log in the storage backend, and whether any
        external dependencies are present and working.

        :raises: VolumeBackendAPIException in case of setup error.
        """

    def get_volume_stats(self, refresh=False):
        """Collects volume backend stats.

        The get_volume_stats method is used by the volume manager to collect
        information from the driver instance related to information about the
        driver, available and used space, and driver/backend capabilities.

        It returns a dict with the following required fields:

        * volume_backend_name
            This is an identifier for the backend taken from cinder.conf.
            Useful when using multi-backend.
        * vendor_name
            Vendor/author of the driver who serves as the contact for the
            driver's development and support.
        * driver_version
            The driver version is logged at cinder-volume startup and is useful
            for tying volume service logs to a specific release of the code.
            There are currently no rules for how or when this is updated, but
            it tends to follow typical major.minor.revision ideas.
        * storage_protocol
            The protocol used to connect to the storage, this should be a short
            string such as: "iSCSI", "FC", "nfs", "ceph", etc.
        * total_capacity_gb
            The total capacity in gigabytes (GiB) of the storage backend being
            used to store Cinder volumes. Use keyword 'unknown' if the backend
            cannot report the value or 'infinite' if there is no upper limit.
            But, it is recommended to report real values as the Cinder
            scheduler assigns lowest weight to any storage backend reporting
            'unknown' or 'infinite'.

        * free_capacity_gb
            The free capacity in gigabytes (GiB). Use keyword 'unknown' if the
            backend cannot report the value or 'infinite' if there is no upper
            limit. But, it is recommended to report real values as the Cinder
            scheduler assigns lowest weight to any storage backend reporting
            'unknown' or 'infinite'.

        And the following optional fields:

        * reserved_percentage (integer)
            Percentage of backend capacity which is not used by the scheduler.
        * location_info (string)
            Driver-specific information used by the driver and storage backend
            to correlate Cinder volumes and backend LUNs/files.
        * QoS_support (Boolean)
            Whether the backend supports quality of service.
        * provisioned_capacity_gb
            The total provisioned capacity on the storage backend, in gigabytes
            (GiB), including space consumed by any user other than Cinder
            itself.
        * max_over_subscription_ratio
            The maximum amount a backend can be over subscribed.
        * thin_provisioning_support (Boolean)
            Whether the backend is capable of allocating thinly provisioned
            volumes.
        * thick_provisioning_support (Boolean)
            Whether the backend is capable of allocating thick provisioned
            volumes. (Typically True.)
        * total_volumes (integer)
            Total number of volumes on the storage backend. This can be used in
            custom driver filter functions.
        * filter_function (string)
            A custom function used by the scheduler to determine whether a
            volume should be allocated to this backend or not. Example:

              capabilities.total_volumes < 10

        * goodness_function (string)
            Similar to filter_function, but used to weigh multiple volume
            backends. Example:

              capabilities.capacity_utilization < 0.6 ? 100 : 25

        * multiattach (Boolean)
            Whether the backend supports multiattach or not. Defaults to False.
        * sparse_copy_volume (Boolean)
            Whether copies performed by the volume manager for operations such
            as migration should attempt to preserve sparseness.

        The returned dict may also contain a list, "pools", which has a similar
        dict for each pool being used with the backend.

        :param refresh: Whether to discard any cached values and force a full
                        refresh of stats.
        :returns: dict of appropriate values (see above).
        """
	volume_backend_name = self._get_backend_name()
	caps = {'volume_backend_name': volume_backend_name,
		'multiattach': True,
		'vendor_name': 'IBM',
		'storage_protocol':'VSCSI',
		'total_capacity_gb' : 90000,
		'free_capacity_gb' : 80000,
		'filter_function': True,
		'goodness_function' : True
		}
	return caps
		




    def create_volume(self, volume):
        """Create a new volume on the backend.

        This method is responsible only for storage allocation on the backend.
        It should not export a LUN or actually make this storage available for
        use, this is done in a later call.

        # TODO(smcginnis) - Add example data structure of volume object.
        :param volume: Volume object containing specifics to create.
        :returns: (Optional) dict of database updates for the new volume.
        :raises: VolumeBackendAPIException if creation failed.
        """
	

	size = volume.size
	display_name = volume.display_name
	volume_id = volume.id
	metadata = dict()
	vlun_name =  display_name
	metadata['type'] = 'thin'
	metadata['name'] = vlun_name
        machine_serial_list = cinder_driver_section.vios_serial_nums
	metadata['VIOS_SER'] = machine_serial_list

	vios_luudid,result = self.ssp_volume_create(connection_string=ssh, vlun_name=vlun_name, vlun_size_gb=str(size))
	if result :
		vios_luudid = str(vios_luudid)
		metadata['vios_luudid'] = vios_luudid.strip()

        	return {'metadata': metadata}
	else:
		exception_message = (_("Failed to create Shared Storage Pool LUN, message is %s") % str(vios_luudid))
		LOG.error(exception_message)
		raise exception.VolumeBackendAPIException(
                data=exception_message)

	


    def remove_export(self, context, volume):
	pass


    def delete_volume(self, volume):
        """Delete a volume from the backend.

        If the driver can talk to the backend and detects that the volume is no
        longer present, this call should succeed and allow Cinder to complete
        the process of deleting the volume.

        :param volume: The volume to delete.
        :raises: VolumeIsBusy if the volume is still attached or has snapshots.
                 VolumeBackendAPIException on error.
        """

        metadata = volume.metadata
	

        vlun_name =  metadata['name'] or volume.display_name
        vios_luudid = metadata['vios_luudid']

        vios_luudid,result = self.ssp_volume_delete(connection_string=ssh, vlun_name=vlun_name, vios_luudid=vios_luudid)
        if result :
                vios_luudid = str(vios_luudid)
                return result
        else:
                exception_message = (_("Failed to remove Shared Storage Pool LUN, message is %s") % str(vios_luudid))
                LOG.error(exception_message)
                raise exception.VolumeBackendAPIException(
                data=exception_message)



    def initialize_connection(self, volume, connector, initiator_data=None):
        """Allow connection to connector and return connection info.

        :param volume: The volume to be attached.
        :param connector: Dictionary containing information about what is being
                          connected to.
        :param initiator_data: (Optional) A dictionary of driver_initiator_data
                               objects with key-value pairs that have been
                               saved for this initiator by a driver in previous
                               initialize_connection calls.
        :returns: A dictionary of connection information. This can optionally
                  include a "initiator_updates" field.

        The "initiator_updates" field must be a dictionary containing a
        "set_values" and/or "remove_values" field. The "set_values" field must
        be a dictionary of key-value pairs to be set/updated in the db. The
        "remove_values" field must be a list of keys, previously set with
        "set_values", that will be deleted from the db.

        May be called multiple times to get connection information after a
        volume has already been attached.
        """
	data = dict()
	WPAR_NAME = connector['WPAR_NAME']
	LPAR_NAME = connector['LPAR_NAME']
	LPAR_ID = connector['LPAR_ID']
	LPAR_SERIAL = connector['LPAR_SERIAL']
	VIOS_LUUDID = volume.metadata['vios_luudid']
	data['WPAR_NAME'] = WPAR_NAME
	data['LPAR_ID'] = LPAR_ID
	data['LPAR_SERIAL'] = LPAR_SERIAL
	data['VIOS_LUUDID'] = VIOS_LUUDID
	data['LPAR_NAME'] = LPAR_NAME

	return {'driver_volume_type': 'VSCSI',
                'data': data}


    def attach_volume(self, context, volume, instance_uuid, host_name,
                      mountpoint):
        """Lets the driver know Nova has attached the volume to an instance.

        :param context: Security/policy info for the request.
        :param volume: Volume being attached.
        :param instance_uuid: ID of the instance being attached to.
        :param host_name: The host name.
        :param mountpoint: Device mount point on the instance.
        """
	pass	
	#instance.metadata[mountpoint] = mount_info
	

    def terminate_connection(self, volume, connector, force=False):
        """Remove access to a volume.

        :param volume: The volume to remove.
        :param connector: The Dictionary containing information about the
                          connection.
        """
	need_table = volume
        Session = sessionmaker(bind=self.engine)
        session = Session()

	LPAR_NAME = connector['LPAR_NAME']


	connection = self.engine.connect()

# Perpetuum: something like: [("{u'SBT-PROMETEY-VIO06': 'VTD:vtscsi1, l_ad:4, machine_serial:103B257; ', u'SBT-PROMETEY-VIO05': 'VTD:vtscsi0, l_ad:3, machine_serial:103B257; '}"),]

	result = session.query(ssp_volume_metadata).filter_by(id=volume.id).first()
	result = session.query(ssp_volume_metadata.value)\
				.filter(ssp_volume_metadata.volume_id==volume.id)\
				.filter(ssp_volume_metadata.key==str('mappings_' + str(LPAR_NAME)))\
				.distinct().all()
	try :
		meta_values = result[0][0] 
	except Exception:
		meta_values = 'None'
	if meta_values != 'None' :
	
		meta_values = str(meta_values)
		meta_values = meta_values.split(';')
		for meta_value in meta_values:

			meta_value = meta_value.strip()
			if len( meta_value) > 1:
				meta_value = str(meta_value)
		
				meta_value = meta_value.split()

				vios_name = 'None'

				vios_vtd = 'None'
				machine_serial = 'None'
				for item in meta_value:
					item = item.split(':')
					if 'vios_name' in item:
						vios_name = item[1]
					if 'VTD' in item:
						vios_vtd = item[1]
					elif 'machine_serial' in item:
						machine_serial = item[1]
			
		
	
				result = self.ssp_volume_unmap(connection_string=ssh,  machine_serial=machine_serial, vios_name=vios_name, vios_vtd=vios_vtd )
				if not result:
					exception_message = (_("Failed to unmap LUN, message is %s") % str(vios_vtd))
                			LOG.error(exception_message)
                			raise exception.VolumeBackendAPIException(
                			data=exception_message)
		result = session.query(ssp_volume_metadata)\
                                .filter(ssp_volume_metadata.volume_id==volume.id)\
                                .filter(ssp_volume_metadata.key==str('mappings_' + str(LPAR_NAME)))\
                                .delete()
		session.commit()
		session.close()
	else:
		meta_values = 'None'
	




    def detach_volume(self, context, volume, attachment=None):
        """Detach volume from an instance.

        :param context: Security/policy info for the request.
        :param volume: Volume being detached.
        :param attachment: (Optional) Attachment information.
        """
	pass
        
        #vol_meta_new = vol_meta.values()


	

    def clone_image(self, volume, image_location, image_id, image_metadata,
                    image_service):
        """Clone an image to a volume.

        :param volume: The volume to create.
        :param image_location: Where to pull the image from.
        :param image_id: The image identifier.
        :param image_metadata: Information about the image.
        :param image_service: The image service to use.
        :returns: Model updates.
        """

	return image_metadata['properties'], False
	

    def copy_image_to_volume(self, context, volume, image_service, image_id):
        """Fetch the image from image_service and write it to the volume.

        :param context: Security/policy info for the request.
        :param volume: The volume to create.
        :param image_service: The image service to use.
        :param image_id: The image identifier.
        :returns: Model updates.
        """

    def copy_volume_to_image(self, context, volume, image_service, image_meta):
        """Copy the volume to the specified image.

        :param context: Security/policy info for the request.
        :param volume: The volume to copy.
        :param image_service: The image service to use.
        :param image_meta: Information about the image.
        :returns: Model updates.
        """

    def extend_volume(self, volume, new_size):
        """Extend the size of a volume.

        :param volume: The volume to extend.
        :param new_size: The new desired size of the volume.
        """
	metadata = volume.metadata


        vlun_name =  metadata['name'] or volume.display_name
        vios_luudid = metadata['vios_luudid']
	new_size = str(new_size)

        vios_luudid,result = self.ssp_volume_extend(connection_string=ssh, vlun_name=vlun_name, vios_luudid=vios_luudid, new_size=new_size)
        if result :
                vios_luudid = str(vios_luudid)
                return result
        else:
                exception_message = (_("Failed to extend Shared Storage Pool LUN, message is %s") % str(vios_luudid))
                LOG.error(exception_message)
                raise exception.VolumeBackendAPIException(
                data=exception_message)


    def validate_connector(self, connector):
        return True


    def create_export(self, context, volume, connector, vg=None):

	metadata = volume.metadata 

	LPAR_SERIAL = connector['LPAR_SERIAL']
	LPAR_ID = connector['LPAR_ID']
	VIOS_LUUDID = volume.metadata['vios_luudid']
	VIO_SERIAL = volume.metadata['VIOS_SER']
	LPAR_NAME = connector['LPAR_NAME']
#	if LPAR_SERIAL in VIO_SERIAL:
	map_result = self.ssp_volume_map(connection_string=ssh, vios_luudid=VIOS_LUUDID, machine_serial=LPAR_SERIAL, lpar_id=LPAR_ID)
#	result =  {'LPAR_SERIAL': LPAR_SERIAL,
#		'LPAR_ID': LPAR_ID,
#		'VIOS_LUUDID': VIOS_LUUDID
# 		}

	metadata['mappings_'+ str(LPAR_NAME) ] = map_result
	return {'metadata': metadata}






    def ssp_volume_create(self, connection_string, vlun_name, vlun_size_gb):
        machine_serial_list = cinder_driver_section.vios_serial_nums
	hmc_user = cinder_driver_section.hmc_user
	hmc_pass = cinder_driver_section.hmc_pass
	hmc_ip =  cinder_driver_section.hmc_ip
	

#### Perpetum TBD: replace code to choos the most suitable vios.
# Currently supported only first one
        machine_serial_num = machine_serial_list.split(',')
        machine_serial_num = machine_serial_num[0]

	machine_name = POWER_MACHINE.get_machine_name(machine_serial=machine_serial_num, target_hmc=hmc_ip, connection_string=connection_string, hmc_user=hmc_user, hmc_pass=hmc_pass)
	vios_list = POWER_MACHINE.get_vios_list(target_machine=machine_name, target_hmc=hmc_ip, hmc_pass=hmc_pass, hmc_user=hmc_user,  connection_string=connection_string)
	first_vio_name = vios_list[0].strip()

	created_vlun,result = SSP_VIOS_WRITE.create_vlun(target_machine=machine_name, \
							target_hmc=hmc_ip, \
							connection_string=connection_string, \
							hmc_user=hmc_user, \
							hmc_pass=hmc_pass, \
							vios_name=first_vio_name, \
							vlun_name=vlun_name, \
							vlun_size_gb=vlun_size_gb)
	

	return created_vlun,result
	


    def ssp_volume_delete(self, connection_string, vios_luudid, vlun_name):
        machine_serial_list = cinder_driver_section.vios_serial_nums
        hmc_user = cinder_driver_section.hmc_user
        hmc_pass = cinder_driver_section.hmc_pass
        hmc_ip =  cinder_driver_section.hmc_ip


#### Perpetum TBD: replace code to choos the most suitable vios.
# Currently supported only first one
        machine_serial_num = machine_serial_list.split(',')
        machine_serial_num = machine_serial_num[0]

        machine_name = POWER_MACHINE.get_machine_name(machine_serial=machine_serial_num, target_hmc=hmc_ip, connection_string=connection_string, hmc_user=hmc_user, hmc_pass=hmc_pass)
        vios_list = POWER_MACHINE.get_vios_list(target_machine=machine_name, target_hmc=hmc_ip, hmc_pass=hmc_pass, hmc_user=hmc_user,  connection_string=connection_string)
        first_vio_name = vios_list[0].strip()


        removed_vlun,result = SSP_VIOS_WRITE.remove_vlun(target_machine=machine_name, \
                                                        target_hmc=hmc_ip, \
                                                        connection_string=connection_string, \
                                                        hmc_user=hmc_user, \
                                                        hmc_pass=hmc_pass, \
                                                        vios_name=first_vio_name, \
                                                        vlun_name=vlun_name, \
                                                        vios_luudid=vios_luudid)


        return removed_vlun,result

    def ssp_volume_extend(self, connection_string, vios_luudid, vlun_name, new_size):
        machine_serial_list = cinder_driver_section.vios_serial_nums
        hmc_user = cinder_driver_section.hmc_user
        hmc_pass = cinder_driver_section.hmc_pass
        hmc_ip =  cinder_driver_section.hmc_ip


#### Perpetum TBD: replace code to choos the most suitable vios.
# Currently supported only first one
        machine_serial_num = machine_serial_list.split(',')
        machine_serial_num = machine_serial_num[0]

        machine_name = POWER_MACHINE.get_machine_name(machine_serial=machine_serial_num, target_hmc=hmc_ip, connection_string=connection_string, hmc_user=hmc_user, hmc_pass=hmc_pass)
        vios_list = POWER_MACHINE.get_vios_list(target_machine=machine_name, target_hmc=hmc_ip, hmc_pass=hmc_pass, hmc_user=hmc_user,  connection_string=connection_string)
        first_vio_name = vios_list[0].strip()
	vios_luudid = vios_luudid.strip()
	new_size = new_size.strip()


        extended_vlun,result = SSP_VIOS_WRITE.extend_vlun(target_machine=machine_name, \
                                                        target_hmc=hmc_ip, \
                                                        connection_string=connection_string, \
                                                        hmc_user=hmc_user, \
                                                        hmc_pass=hmc_pass, \
                                                        vios_name=first_vio_name, \
                                                        vlun_name=vlun_name, \
                                                        vios_luudid=vios_luudid, \
							new_size=new_size)


        return extended_vlun,result



    def ssp_volume_map(self, connection_string, vios_luudid, machine_serial, lpar_id):
	hmc_user = cinder_driver_section.hmc_user
	hmc_pass = cinder_driver_section.hmc_pass
	hmc_ip =  cinder_driver_section.hmc_ip

	machine_name = POWER_MACHINE.get_machine_name(machine_serial=machine_serial, target_hmc=hmc_ip, connection_string=connection_string, hmc_user=hmc_user, hmc_pass=hmc_pass)
	vios_list = POWER_MACHINE.get_vios_list(target_machine=machine_name, target_hmc=hmc_ip, hmc_pass=hmc_pass, hmc_user=hmc_user,  connection_string=connection_string)
	data = ""

	for vios in vios_list :
		vios = vios.strip()
		smallest_adapter, lpar_adapter_num  = SSP_VIOS_READ.find_smallest_disk_adapter(target_machine=machine_name, target_hmc=hmc_ip, connection_string=connection_string, hmc_user=hmc_user, hmc_pass=hmc_pass, lpar_id=lpar_id, vios_name=vios )
		mapped_vlun =   SSP_VIOS_WRITE.map_vlun(target_machine=machine_name, \
                                                 target_hmc=hmc_ip, \
                                                 connection_string=connection_string, \
                                                 hmc_user=hmc_user, \
                                                hmc_pass=hmc_pass, \
                                                vios_name=vios, \
                                                vios_luudid=vios_luudid, \
                                                vios_vhost=smallest_adapter )
		data = data + 'vios_name:'+ str(vios) + ' '
		data = data + 'vhost:'+ str(smallest_adapter) + ' '
		data = data + str(mapped_vlun) + ' '
		data = data + 'lpar_adapter:'+ str(lpar_adapter_num) + ' '
		data = data + 'machine_serial:'+ str(machine_serial) + '; '
	return data
	


    def ssp_volume_unmap(self, connection_string, machine_serial, vios_name, vios_vtd ):
        hmc_user = cinder_driver_section.hmc_user
        hmc_pass = cinder_driver_section.hmc_pass
        hmc_ip =  cinder_driver_section.hmc_ip
	machine_name = POWER_MACHINE.get_machine_name(machine_serial=machine_serial, target_hmc=hmc_ip, connection_string=connection_string, hmc_user=hmc_user, hmc_pass=hmc_pass)

	unmapped_lun, status = SSP_VIOS_WRITE.unmap_vlun(target_machine=machine_name, \
							target_hmc=hmc_ip, \
							connection_string=connection_string, \
							hmc_user=hmc_user, \
							hmc_pass=hmc_pass, \
							vios_name=vios_name, \
							vios_vtd=vios_vtd)

	return status


    def ensure_export(self, context, volume):
        """Recreate exports for logical volumes."""

        # Restore saved configuration file if no target exists.


