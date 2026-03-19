# ExaData

# Plugins
Each plugin is described, including metadata about its metrics and its specific columns.

Plugins:
- [Ganglia](plugins/ganglia.md)
- [IPMI](plugins/ipmi.md)
- [Job table](plugins/job_table.md)
- [Logics](plugins/logics.md)
- [Nagios](plugins/nagios.md)
- [SLURM](plugins/slurm.md)
- [Schneider](plugins/schneider.md)
- [Vertiv](plugins/vertiv.md)
- [Weather](plugins/weather.md)

# Ganglia
The Ganglia plugin connects to the Ganglia server (gmond), collects and translates the data payload (XML) to the ExaMon data model.

NOTE: the sampling period of the metrics has high variability, patterns are different across nodes. **The reported values are an approximation**.

## Plugin-specific columns

|Column|Description|
|------|-----------|
|node|The hostname of the server|

## Metrics
|Metric|Description|Group|Unit|Value type|Sampling period|
|------|-----------|-----|----|----------|---------------|
|GpuX_boar	int	~20s (per node)
GpuX_ecc_dbe_volatile_total	Total double bit volatile ECC errors	gpu	d_limit_violation|Board violation limit (X=0,..,3)|gpu|_|int|~20s (per node)|
|GpuX_current_clock_throttle_reasons|Current clock throttle reasons (bitmask of DCGM_CLOCKS_THROTTLE_REASON_*)|gpu|_|int|~20s (per node)|
|GpuX_ecc_dbe_aggregate_total|Total double bit aggregate (persistent) ECC errors Note: monotonically increasing|gpu|_|int|~20s (per node)|
|GpuX_ecc_dbe_volatile_total|Total double bit volatile ECC errors|gpu|_|int|~20s (per node)|
|GpuX_ecc_sbe_aggregate_total|Total single bit aggregate (persistent) ECC errors Note: monotonically increasing|gpu|_|int|~20s (per node)|
|GpuX_ecc_sbe_volatile_total|Total single bit volatile ECC errors|gpu|_|int|~20s (per node)|
|GpuX_fb_free|Free Frame Buffer in MB|gpu|mb|int|~20s (per node)|
|GpuX_fb_total|Total Frame Buffer of the GPU in MB|gpu|mb|int|~20s (per node)|
|GpuX_fb_used|Used Frame Buffer in MB|gpu|mb|int|~20s (per node)|
|GpuX_gpu_temp|Current temperature readings for the device, in degrees C|gpu|celsius|int|~20s (per node)|
|GpuX_gpu_util_samples|GPU Utilization samples|gpu|_|int|~20s (per node)|
|GpuX_gpu_utilization|GPU Utilization|gpu|%|int|~20s (per node)|
|GpuX_low_util_violation|Low utilisation violation limit|gpu|_|int|~20s (per node)|
|GpuX_mem_app_clock|Memory Application clocks|gpu|_|int|~20s (per node)|
|GpuX_mem_copy_utilization|Memory Utilization|gpu|%|int|~20s (per node)|
|GpuX_memory_clock|Memory clock for the device|gpu|megahertz|int|~20s (per node)|
|GpuX_memory_temp|Memory temperature for the device|gpu|celsius|int|~20s (per node)|
|GpuX_nvlink_bandwidth_total|NVlink total bandwidth|gpu|_|int|~20s (per node)|
|GpuX_nvlink_data_crc_error_count_total|NvLink data CRC Error Counter total for all Lanes.|gpu|_|int|~20s (per node)|
|GpuX_nvlink_flit_crc_error_count_total|NVLink flow control CRC Error Counter total for all Lanes|gpu|_|int|~20s (per node)|
|GpuX_nvlink_recovery_error_count_total|NVLink Recovery Error Counter total for all Lanes.|gpu|_|int|~20s (per node)|
|GpuX_nvlink_replay_error_count_total|NVLink Replay Error Counter total for all Lanes.|gpu|_|int|~20s (per node)|
|GpuX_power_management_limit|Current Power limit for the device|gpu|watts|int|~20s (per node)|
|GpuX_power_usage|Power usage for the device in Watts|gpu|watts|float|~20s (per node)|
|GpuX_power_violation|Power Violation time in usec|gpu|usec|int|~20s (per node)|
|GpuX_pstate|Performance state (P-State) 0-15. 0=highest|gpu|_|int|~20s (per node)|
|GpuX_reliability_violation|Reliability violation limit.|gpu|_|int|~20s (per node)|
|GpuX_retired_pages_dbe|Number of retired pages because of double bit errors Note: monotonically increasing|gpu|_|int|~20s (per node)|
|GpuX_retired_pages_pending|Number of pages pending retirement|gpu|_|int|~20s (per node)|
|GpuX_retired_pages_sbe|Number of retired pages because of single bit errors Note: monotonically increasing|gpu|_|int|~20s (per node)|
|GpuX_sm_app_clock|SM Application clocks|gpu|_|int|~20s (per node)|
|GpuX_sm_clock|SM clock for the device|gpu|megahertz|int|~20s (per node)|
|GpuX_sync_boost_violation|Sync Boost Violation time in usec|gpu|usec|int|~20s (per node)|
|GpuX_thermal_violation|Thermal Violation time in usec|gpu|usec|int, float (Gpu0)|~20s (per node)|
|GpuX_total_energy_consumption|Total energy consumption for the GPU in mJ since the driver was last reloaded|gpu|mj|float|~20s (per node)|
|GpuX_xid_errors|XID errors. The value is the specific XID error. (https://docs.nvidia.com/deploy/xid-errors/index.html#topic_4)|gpu|_|int|~20s (per node)|
|boottime|The last time that the system was started|system|s|float|1m (per node)|
|bytes_in|Number of bytes in per second|network|bytes/sec|float|5m or 40s (per node)|
|bytes_out|Number of bytes out per second|network|bytes/sec|float|5m or 40s (per node)|
|cpu_aidle|Percent of time since boot idle CPU|cpu|%|float|1m 30s (per node)|
|cpu_idle|Percentage of time that the CPU or CPUs were idle and the system did not have an outstanding disk I/O request|cpu|%|float|1m 30s (per node)|
|cpu_nice|Percentage of CPU utilization that occurred while executing at the user level with nice priority|cpu|%|float|1m 30s (per node)|
|cpu_num|The number of cpu present|cpu|cpus|int|1m (per node)|
|cpu_speed|CPU Speed in terms of MHz|cpu|mhz|int|1m (per node)|
|cpu_steal|Percentage of CPU steal that occurred while executing at the system level|cpu|%|int|1m 30s (per node)|
|cpu_system|Percentage of CPU utilization that occurred while executing at the system level|cpu|%|float|1m 30s (per node)|
|cpu_user|Percentage of CPU utilization that occurred while executing at the user level|cpu|%|float|1m 30s (per node)|
|cpu_wio|Percentage of time that the CPU or CPUs were idle during which the system had an outstanding disk I/O request|cpu|%|float|1m 30s (per node)|
|disk_free|Total free disk space|disk|gb|float|3m (per node)|
|disk_total|Total available disk space|disk|gb|float|1h (per node)|
|gexec|gexec available|core|_|string|5m (per node)|
|load_fifteen|Fifteen minute load average|load|_|float|1m 30s (per node)|
|load_five|Five minute load average|load|_|float|1m 30s (per node)|
|load_one|One minute load average|load|_|float|1m 30s (per node)|
|machine_type|System architecture|system|_|string|1m (per node)|
|mem_buffers|Amount of buffered memory|memory|kb|int|40s (per node)|
|mem_cached|Amount of cached memory|memory|kb|float|40s (per node)|
|mem_free|Amount of available memory|memory|kb|float|40s (per node)|
|mem_shared|Amount of shared memory|memory|kb|int|40s (per node)|
|mem_total|Total amount of memory displayed in KBs|memory|kb|float|1m (per node)|
|os_name|Operating system name|system|_|string|1m (per node)|
|os_release|Operating system release date|system|_|string|1m (per node)|
|part_max_used|Maximum percent used for all partitions|disk|%|float|3m (per node)|
|pkts_in|Packets in per second|network|packets/sec|float|5m or 40s (per node)|
|pkts_out|Packets out per second|network|packets/sec|float|5m or 40s (per node)|
|proc_run|Total number of running processes|process|_|int|1m 20s (per node)|
|proc_total|Total number of processes|process|_|int|1m 20s (per node)|
|swap_free|Amount of available swap memory|memory|kb|int|40s (per node)|
|swap_total|Total amount of swap space displayed in KBs|memory|kb|int|1m (per node)|



# IPMI
The IPMI plugin collects all the sensor data provided by the OOB management interface (BMC) of cluster nodes.

## Plugin-specific columns

|Column|Description|
|------|-----------|
|node|The hostname of the server|

## Metrics
|Metric|Description|Unit (ExaMon)|Unit (doc)|Value type|Sampling period|
|------|-----------|-------------|----------|----------|---------------|
|ambient|Temperature at the node inlet|degreesC|°C|float|20s (per node)|
|dimmX_temp|Temperature of DIMM module n. X. X=0..15|degreesC|°C|int|20s (per node)|
|fanX_Y|Speed of the Fan Y in module X. X=0..3, Y=0,1|revolutions|RPM|int|20s (per node)|
|fan_disk_power|Power consumption of the disk fan|Watts|W|int|20s (per node)|
|gpuX_core_temp|Temperature of the core for the GPU id X. X=0,1,3,4|degreesC|°C|int|20s (per node)|
|gpuX_mem_temp|Temperature of the memory for the GPU id X. X=0,1,3,4|degreesC|°C|int|20s (per node)|
|gv100cardX|X=0..3|unspecified||int|20s (per node)|
|pX_coreY_temp|Temperature of core n. Y in the CPU socket n. X. X=0..1, Y=0..23|degreesC|°C|int|20s (per node)|
|pX_io_power|Power consumption for the I/O subsystem for the CPU socket n. X. X=0..1|Watts|W|int|20s (per node)|
|pX_mem_power|Power consumption for the memory subsystem for the CPU socket n. X. X=0..1|Watts|W|int|20s (per node)|
|pX_power|Power consumption for the CPU socket n. X. X=0..1|Watts|W|int|20s (per node)|
|pX_vdd_temp|Temperature of the voltage regulator for the CPU socket n. X. X=0..1|degreesC|°C|int|20s (per node)|
|pcie|Temperature at the PCIExpress slots|degreesC|°C|float|20s (per node)|
|psX_input_power|Power consumption at the input of power supply n. X. X=0..1|Watts|W|int|20s (per node)|
|psX_input_voltag|Voltage at the input of power supply n. X. X=0..1|Volts|V|int|20s (per node)|
|psX_output_curre|Current at the output of power supply n. X. X=0..1|Amps|A|int|20s (per node)|
|psX_output_volta|Voltage at the output of power supply n. X. X=0..1|Volts|V|float|20s (per node)|
|total_power|Total node power consumption|Watts|W|int|20s (per node)|



# Job table
Collects information regarding the jobs executed on the cluster (and store in the SLURM database);
the information collected are those provided by users at submission time.

Only one metric is present: `job_info_marconi100`.

## Plugin-specific columns

|Column|Description|Type|
|------|-----------|----|
|accrue_time|Accrue time associated with the job|timestamp|
|alloc_node|Nodes allocated to the job|string|
|alloc_sid|Local session ID used to submit the job|int|
|array_job_id|Job ID of a job array or 0 if N/A (anonymized)|int|
|array_max_tasks|Maximum number of running tasks|int|
|array_task_id|Task ID of a job array|int|
|array_task_str|String expression of task IDs in this record|string|
|array_task_throttle|The maximum number of tasks in a job array that can execute at the same time|int|
|assoc_id|ID of the job association|int|
|batch_flag|Batch flag set (1 yes, 0 otherwise)|int|
|batch_host|Name of host running batch script|string|
|billable_tres|Billable Trackable Resource (TRES) cache; updated upon resize|int|
|bitflags|Various job flags|int|
|boards_per_node|Boards per node required by job|int|
|contiguous|1 if job requires contiguous nodes|bool|
|cores_per_socket|Cores per socket required by job|int|
|cpus_alloc_layout|Map: list of cpu allocated per node|string|
|cpus_allocated|Map: number of cpu allocated per node|string|
|cpus_per_task|Number of processors required for each task|int|
|cpus_per_tres|Semicolon-delimited list of TRES=# values|string|
|dependency|Synchronize job execution with other jobs; a job can start only after its dependencies have completed (anonymized)|string|
|derived_ec|Highest exit code of all job steps|string|
|eligible_time|Time job is eligible for running|timestamp|
|end_time|Time of termination, actual or expected|timestamp|
|exc_nodes|Comma-separated list of excluded nodes|string|
|exit_code|Exit code for job (status from wait call)|string|
|features|Comma-separated list of required features|string|
|group_id|Group job submitted as|int|
|job_id|Job ID (anonymized)|int|
|job_state|State of the job, see enum job_states for possible values|string|
|last_sched_eval|Last time the job was evaluated for scheduling|timestamp|
|max_cpus|Maximum number of cpus usable by job|int|
|max_nodes|Maximum number of nodes usable by job|int|
|mem_per_cpu|1 if the job has exceeded the amount of per-CPU memory allowed, 0 otherwise|bool|
|mem_per_node|1 if the job has exceeded the amount of per-node memory allowed, 0 otherwise|bool|
|metric|Partitioning column|string|
|min_memory_cpu|Minimum real memory required per allocated CPU|int|
|min_memory_node|Minimum real memory required per node|int|
|nice|Nice value (adjustment to a job's scheduling priority)|int|
|nodes|List of nodes allocated to job|string|
|ntasks_per_board|Number of tasks to invoke on each board|int|
|ntasks_per_core|Number of tasks to invoke on each core|int|
|ntasks_per_core_str|Number of tasks to invoke on each core as string|string|
|ntasks_per_node|Number of tasks to invoke on each node|int|
|ntasks_per_socket|Number of tasks to invoke on each socket|int|
|ntasks_per_socket_str|Number of tasks to invoke on each socket as string|string|
|num_cpus|Number of CPUs (processors) requested by the job or allocated to it if already running|int|
|num_nodes|Number of nodes allocated to the job or the minimum number of nodes required by a pending job|int|
|num_tasks|Number of tasks requested by a job or job step|int|
|partition|Name of assigned partition (anonymized)|string|
|plugin|Partitioning column|string|
|pn_min_cpus|Minimum # CPUs per node, default=0|int|
|pn_min_memory|Minimum real memory per node, default=0|int|
|pn_min_tmp_disk|Minimum temporary disk per node, default=0|int|
|power_flags|Power management flags, see SLURM_POWERFLAGS|int|
|priority|Relative priority of the job, 0=held, 1=required nodes DOWN/DRAINED|int|
|profile|Level of acct_gather_profile {all / none}|int|
|qos|Quality of Service (anonymized, categorical)|string|
|reboot|Node reboot requested before start|int|
|req_nodes|Comma-separated list of required nodes|string|
|req_switch|Minimum number of switches|int|
|requeue|Enable or disable job requeue option|bool|
|resize_time|Time of latest size change|timestamp|
|restart_cnt|Count of job restarts|int|
|resv_name|Reservation name|string|
|run_time|Job run time (seconds)|int|
|run_time_str|Job run time (seconds) as string|string|
|sched_nodes|For pending jobs, a list of the nodes expected to be used when the job is started|string|
|shared|1 if job can share nodes with other jobs, 0 otherwise|string|
|show_flags|Determine the level of details requested|int|
|sockets_per_board|Sockets per board allocated to the job|int|
|sockets_per_node|Sockets per node required by job|int|
|start_time|Time execution begins (actual or expected)|timestamp|
|state_reason|Reason job still pending or failed,see slurm.h:enum job_state_reason|string|
|submit_time|Time of job submission|timestamp|
|suspend_time|Time job last suspended or resumed|timestamp|
|threads_per_core|Threads per core required by job|int|
|time_limit|Maximum run time in minutes or INFINITE|int|
|time_limit_str|Maximum run time in minutes or INFINITE as string|string|
|time_min|Minimum run time in minutes or INFINITE|int|
|tres_alloc_str|Trackable resources allocated to the job|string|
|tres_bind|Trackable resources task binding requested by the job or job step|string|
|tres_freq|Trackable resources frequencies requested by the job or job step|string|
|tres_per_job|Trackable resources requested by the job|string|
|tres_per_node|Trackable resources per node requested by the job or job step|string|
|tres_per_socket|Trackable resources per socket requested by the job or job step|string|
|tres_per_task|Trackable resources per task requested by the job or job step|string|
|tres_req_str|TRES requested by the job as string|string|
|user_id|User ID for a job or job step (anonymized)|int|
|wait4switch|Maximum time to wait for minimum switches|int|
|wckey|Workload Characterization Key of a job|string|
|year_month|Partitioning column ("YY-MM")|string|




# Logics
Logics is a data collection system already installed at Cineca. It is specialized for collecting power consumption data from equipment in the different rooms, typically using multimeters that communicate via Modbus protocol. The ExaMon plugin dedicated to collecting this data interfaces to the Logics database (RDBMS) via its REST API.

NOTE: Since the translation process is fully automated, the same inconsistencies present in the original db may result in the ExaMon database: e.g., metric names in the Italian language, units of measure as metric name, etc.

## Plugin-specific columns

|Column|Description|
|------|-----------|
|panel|The name of the electrical panel within the computer rooms|
|device|The name of the device, connected to the panel, of which the multimeter measures the parameters|

## Metrics

|Metric|Description|Unit|Value type|
|------|-----------|----|----------|
|Bad_values|Status flag indicating that the metric reported for the specified panel/device could be unreliable|_|int|
|Comlost|Status flag indicating issue in the sensor communication link|_|float|
|Corrente|Current|A|float|
|Corrente_L1|Three-phase current Line 1|A|float|
|Corrente_L2|Three-phase current Line 2|A|float|
|Corrente_L3|Three-phase current Line 3|A|float|
|Dcie|Data Center Infrastructure Efficiency|_|float|
|Energia|Energy|kWh|float|
|Fattore_di_potenza|Power Factor|COS|float|
|Frequenza|AC Frequency|Hz|float|
|Gateway|Modbus gateway|_|string|
|ID_Modbus|Modbus device id|_|int|
|Mvar|Reactive Power|MVAR|float|
|Mvarh|Reactive Energy|MVARh|float|
|Mw|Power|MW|float|
|Mwh|Energy|MWh|float|
|Potenza|Power|kW|float|
|Potenza_attiva|Power|kW|float|
|Prototype|Sensor Type|_|string|
|Pue|Power Usage Effectiveness|_|float|
|Stato|Global status of the data center|_|int|
|Status|Global status flag for the specified panel/device metric|_|int|
|Tensione|Voltage|V|int|
|Tot|Total Power consumed by the data center|kW|float|
|Tot_cdz|Total Power consumed by the CRACs units|kW|float|
|Tot_chiller|Total Power consumed by the Chillers|kW|float|
|Tot_ict|Total Power consumed by the IT devices|kW|float|
|Tot_qpompe|Total Power consumed by the liquid cooling devices|kW|float|
|Tot_servizi|Total Power consumed by the auxiliary services|kW|float|
|Volt1|Three-phase voltage Line 1|V|int|
|Volt2|Three-phase voltage Line 2|V|float|
|Volt3|Three-phase voltage Line 3|V|int|
|address|Modbus ip address|_|string|
|deviceid|Modbus device id|_|int|
|pit|Total Power consumed by the IT devices|W|int|
|pt|Total Power consumed by the data center|W|int|
|pue|Power Usage Effectiveness|_|float|


# Nagios
This plugin interfaces with a Nagios extension developed by CINECA called "Hnagios", collects and translates the data payload to the ExaMon data model.

## Plugin-specific columns

|Column|Description|
|------|-----------|
|description|Name of the entity (HW/SW) monitored by Nagios|
|host_group|Label defining groups of nodes sharing the same function|
|nagiosdrained|Flag indicating that the node on which the specific alarm occurred was drained (placed offline) manually by an operator|
|node|The hostname of the server|
|state_type|Number indicating the state type of the host or service when the event handler was run. 0 = SOFT state; 1 = HARD state|

### Description (tag)

|Value|Description|
|-----|-----------|
|alive::ping|The node is network reachable via ICMP|
|backup::local::status|The status of the backup of management node is current|
|batchs::client|The batch system client daemon in compute nodes is up & run|
|batchs::client::serverrespond|The batch scheduler server is responding to queries|
|batchs::client::state|The compute node batch client is in a good shape able to schedule jobs (in the view of the batch scheduler server)|
|batchs::manager::state|The batch scheduler server is available|
|bmc::events|The node’s bmc processor has reported critical events|
|cluster::status::availability|The status summary related to the availability (available nodes/total nodes) of the entire platform|
|cluster::status::criticality|The status summary related to the critical nodes (nodes not properly working not yet under repair/total nodes) of the entire platform|
|cluster::status::internal|Checks the above values are properly calculated|
|cluster::status::wattage|The total IT energy power absorbed is in a given range|
|cluster::us::availability|The status summary related to the availability (available nodes/total nodes) of the entire platform at the end of a maintenance. Another view of the cluster::status::* not useful|
|cluster::us::criticality|The status summary related to the critical nodes (nodes not properly working not yet under repair/total nodes) of the entire platform. Another view of the cluster::status::* not useful|
|container::check::health|The status of the “general services” provided via containers|
|container::check::internal||
|container::check::mounts|The availability of the shared mount points binded to the containers runtime.|
|crm::resources::m100|Status of the resources managed via Pacemaker/Corosync HA cluster management system|
|crm::status::m100|Status of the cluster managed via Pacemaker/Corosync HA cluster management system|
|dev::raid::status|Status of the storage raid controller/resources|
|dev::swc::confcheck|Status of the current configuration of the network switches (unwanted/unmanaged changes)|
|dev::swc::confcheckself|Status of completeness of the previous one|
|dev::swc::cumulusensors|Sensor readings and related thresholds checks for Cumulus OS based network switches|
|dev::swc::cumulushealth|Healthiness of the Cumuls OS based network switches|
|dev::swc::cumulussensors|The same as dev::swc::cumulusensors|
|dev::swc::hwcheck|Healthiness of network switches (hw failures)|
|dev::swc::isl|Status of the network inter switch links/ports|
|dev::swc::mlxhealth|Healthiness of the Mellanox OS based network switches|
|dev::swc::mlxsensors|Sensor readings and related thresholds checks for Mellanox OS based network switches|
|file::integrity|Local file system data coherency|
|filesys::dres::mount|Shared file system mount availability|
|filesys::eurofusion::mount|Shared file system mount availability|
|filesys::local::avail|Local filesystem capability|
|filesys::local::mount|Local filesystem mount availability|
|filesys::shared::mount|Shared file system mount availability|
|firewalld::status|Firewalld daemon readiness and effectiveness|
|galera::status::Integrity|Galera cluster Integrity|
|galera::status::NodeStatus|Galera cluster nodes availability|
|galera::status::ReplicaStatus|Galera cluster replica effectiveness|
|globus::gridftp|Globus gridftp daemon status|
|globus::gsissh|Globus gsissh daemon status|
|memory::phys::total|Physical memory availability|
|monitoring::health|Coherency in monitored/under maintenance/under repair nodes|
|net::ib::status|Infiniband HCA readiness and effectiveness|
|nfs::rpc::status|Remote NFS export source readiness|
|nvidia::configuration|Nvidia GPGPU configuration status|
|nvidia::memory::replace|Nvidia GPGPU memory degraded to be replaced|
|nvidia::memory::retirement|Nvidia GPGPU memory degraded status|
|service::cert|Validity of TLS certificates|
|service::galera|Galera cluster integrity and replica status|
|service::galera:arbiter|Galera cluster arbiter status|
|service::galera:mysql|Mysql daemon readiness|
|ssh::daemon|SSH service is responding to connections|
|sys::corosync::rings|Status of the corosync rings in a cluster managed via Pacemaker/Corosync HA cluster management system|
|sys::gpfs::status|Status of the GPFS daemon services in a node|
|sys::pacemaker::crm|Status of the resources managed via Pacemaker/Corosync HA cluster management system|
|sys::rvitals|Status of the BMC controller sensors and related thresholds|
|sys::sssd::events|Status of the System Security Service Daemon|
|sys::xcatpod::sync|Synchronization status of the management system|
|unicore::tsi|Unicore TSI service is up & running|
|unicore::uftpd|Unicore UFTPD service is up & running|
|vm::virsh::state|Virtual Machine status as seen by hypervisor|

## Metrics

|Metric|Description|Value type|Sampling period|
|------|-----------|----------|---------------|
|state|Current status of the monitored service/resource. Follows the Nagios state encoding. For host event handlers: 0 = UP 1 = DOWN 2 = UNREACHABLE; for service event handlers: 0 = OK 1 = WARNING 2 = CRITICAL 3 = UNKNOWN|int|15m (per node and description)|

# Schneider
The Schneider plugin is a dedicated data collector designed to acquire data from an industrial PLC by accessing its HMI module (from Schneider Electric).The PLC controls the valves and pumps of the liquid cooling circuit (RDHx) of Marconi 100. It consists of two (redundant) twin systems controllable by two identical HMI panels, Q101 and Q102.The examon plugin extracts and stores all the metrics available on both panels.

## Plugin-specific columns

|Column|Description|
|------|-----------|
|panel|Name of the panel|

## Metrics
|Metric|Description|Unit|Value type|Sampling period|
|------|-----------|----|----------|---------------|
|Alm_TY141|Three-way valve TY141 Alarm |pure number|int|20s (per panel)|
|PLC_PLC_Q101.Abilita_inverter|Inverter enabled|pure number|int|20s (per panel)|
|PLC_PLC_Q101.Abilita_valvola1|Valve 1 enabled|pure number|int|20s (per panel)|
|PLC_PLC_Q101.Abilita_valvola2|Valve 2 enabled|pure number|int|20s (per panel)|
|PLC_PLC_Q101.Allarme_on|Alarm on|pure number|int|20s (per panel)|
|PLC_PLC_Q101.Allarme_presente|Alarm enabled||int|20s (per panel)|
|PLC_PLC_Q101.Alm_inverter_p101|Alarm for the inverter of pump p101||int|20s (per panel)|
|PLC_PLC_Q101.Alm_inverter_p102|Alarm for the inverter of pump p102||int|20s (per panel)|
|PLC_PLC_Q101.Alm_inverter_p103|Alarm for the inverter of pump p103||int|20s (per panel)|
|PLC_PLC_Q101.Alm_inverter_p104|Alarm for the inverter of pump p104||int|20s (per panel)|
|PLC_PLC_Q101.Alm_max_portata|Maximum flow rate alarm||int|20s (per panel)|
|PLC_PLC_Q101.Alm_max_t_mandata|Supply flow maximum temperature alarm||int|20s (per panel)|
|PLC_PLC_Q101.Alm_max_t_ritorno|Return flow maximum temperature alarm||int|20s (per panel)|
|PLC_PLC_Q101.Alm_min_portata|Minimum flow rate alarm||int|20s (per panel)|
|PLC_PLC_Q101.Alm_min_t_mandata|Supply flow minimum temperature alarm||int|20s (per panel)|
|PLC_PLC_Q101.Alm_nostart_p101|Alarm of pump  p101 not started||int|20s (per panel)|
|PLC_PLC_Q101.Alm_nostart_p102|Alarm of pump  p102 not started||int|20s (per panel)|
|PLC_PLC_Q101.Alm_nostart_p103|Alarm of pump  p103 not started||int|20s (per panel)|
|PLC_PLC_Q101.Alm_nostart_p104|Alarm of pump  p104 not started||int|20s (per panel)|
|PLC_PLC_Q101.Alm_w1|||int|20s (per panel)|
|PLC_PLC_Q101.Cmd_valvola_1|Valve 1 command||int|20s (per panel)|
|PLC_PLC_Q101.Cmd_valvola_2|Valve 2 command||int|20s (per panel)|
|PLC_PLC_Q101.Delta_temp|Temperature delta |°C (x10)|int|20s (per panel)|
|PLC_PLC_Q101.Diff_minuti_cavedio|Time difference w.r.t. air shaft|minutes|int|20s (per panel)|
|PLC_PLC_Q101.Diff_minuti_quadro|Time difference w.r.t. panel|minutes|int|20s (per panel)|
|PLC_PLC_Q101.Diff_minuti_sala|Time difference w.r.t. room|minutes|int|20s (per panel)|
|PLC_PLC_Q101.In_marcia_p101|Running status of pump p101||int|20s (per panel)|
|PLC_PLC_Q101.In_marcia_p102|Running status of pump p102||int|20s (per panel)|
|PLC_PLC_Q101.In_marcia_p103|Running status of pump p103||int|20s (per panel)|
|PLC_PLC_Q101.In_marcia_p104|Running status of pump p104||int|20s (per panel)|
|PLC_PLC_Q101.Kp_pid_pompe|Proportional gain of the pump's PID||int|20s (per panel)|
|PLC_PLC_Q101.Kp_pid_valvole|Proportional gain of the valve's PID||int|20s (per panel)|
|PLC_PLC_Q101.Manuale_p101|Manual control for pump p101||int|20s (per panel)|
|PLC_PLC_Q101.Manuale_p102|Manual control for pump p102||int|20s (per panel)|
|PLC_PLC_Q101.Manuale_p103|Manual control for pump p103||int|20s (per panel)|
|PLC_PLC_Q101.Manuale_p104|Manual control for pump p104||int|20s (per panel)|
|PLC_PLC_Q101.Manuale_ty141|Manual control for valve ty141||int|20s (per panel)|
|PLC_PLC_Q101.Manuale_ty142|Manual control for valve ty142||int|20s (per panel)|
|PLC_PLC_Q101.Max_ana_out_ty141|Maximum analogical output value for valve ty141||int|20s (per panel)|
|PLC_PLC_Q101.Max_ana_out_ty142|Maximum analogical output value for valve ty142||int|20s (per panel)|
|PLC_PLC_Q101.Max_ana_portata1|Maximum analogical output value for Supply flow 1||int|20s (per panel)|
|PLC_PLC_Q101.Max_ana_portata2|Maximum analogical output value for Supply flow 2||int|20s (per panel)|
|PLC_PLC_Q101.Max_ana_pos_ty141|Maximum analogical position for valve ty141||int|20s (per panel)|
|PLC_PLC_Q101.Max_ana_pos_ty142|Maximum analogical position for valve ty142||int|20s (per panel)|
|PLC_PLC_Q101.Max_portata|Maximum Supply flow rate|m3/h (x10)|int|20s (per panel)|
|PLC_PLC_Q101.Max_t_mandata|Maximum temperature for the Supply flow|°C (x10)|int|20s (per panel)|
|PLC_PLC_Q101.Max_t_ritorno|Maximum temperature for the return flow|°C (x10)|int|20s (per panel)|
|PLC_PLC_Q101.Max_visi_portata2|||int|20s (per panel)|
|PLC_PLC_Q101.Max_visu_portata1|||int|20s (per panel)|
|PLC_PLC_Q101.Min_ana_out_ty141|Minimum analogical output value for valve ty141||int|20s (per panel)|
|PLC_PLC_Q101.Min_ana_out_ty142|Minimum analogical output value for valve ty142||int|20s (per panel)|
|PLC_PLC_Q101.Min_ana_portata1|Minimum analogical output value for Supply flow 1||int|20s (per panel)|
|PLC_PLC_Q101.Min_ana_portata2|Minimum analogical output value for Supply flow 2||int|20s (per panel)|
|PLC_PLC_Q101.Min_ana_pos_ty141|Minimum analogical valve position ty141||int|20s (per panel)|
|PLC_PLC_Q101.Min_ana_pos_ty142|Minimum analogical valve position ty142||int|20s (per panel)|
|PLC_PLC_Q101.Min_lavoro_p101|Working minutes for pump  p101|minutes|int|20s (per panel)|
|PLC_PLC_Q101.Min_lavoro_p102|Working minutes for pump p102|minutes|int|20s (per panel)|
|PLC_PLC_Q101.Min_lavoro_p103|Working minutes for pump p103|minutes|int|20s (per panel)|
|PLC_PLC_Q101.Min_lavoro_p104|Working minutes for pump p104|minutes|int|20s (per panel)|
|PLC_PLC_Q101.Min_lavoro_quadro|Working minutes for panel|minutes|int|20s (per panel)|
|PLC_PLC_Q101.Min_out_pid_pompe|Working minutes for the pump's output PID|minutes|int|20s (per panel)|
|PLC_PLC_Q101.Min_out_pid_valv|Working minutes for the valve's output PID|minutes|int|20s (per panel)|
|PLC_PLC_Q101.Min_parz_p101|Partial minutes for pump p101|minutes|int|20s (per panel)|
|PLC_PLC_Q101.Min_parz_p102|Partial minutes for pump p102|minutes|int|20s (per panel)|
|PLC_PLC_Q101.Min_parz_p103|Partial minutes for pump p103|minutes|int|20s (per panel)|
|PLC_PLC_Q101.Min_parz_p104|Partial minutes for pump p104|minutes|int|20s (per panel)|
|PLC_PLC_Q101.Min_parziali_p101|Partial minutes for pump p101|minutes|int|20s (per panel)|
|PLC_PLC_Q101.Min_parziali_p102|Partial minutes for pump p102|minutes|int|20s (per panel)|
|PLC_PLC_Q101.Min_parziali_p103|Partial minutes for pump p103|minutes|int|20s (per panel)|
|PLC_PLC_Q101.Min_parziali_p104|Partial minutes for pump p104|minutes|int|20s (per panel)|
|PLC_PLC_Q101.Min_parziali_quadro|Partial minutes for panel|minutes|int|20s (per panel)|
|PLC_PLC_Q101.Min_portata|Minimum flow rate|m3/h (x10)|int|20s (per panel)|
|PLC_PLC_Q101.Min_t_mandata|Minimum temperature for the Supply flow|°C (x10)|int|20s (per panel)|
|PLC_PLC_Q101.Min_vel_pompe|Minimum temperature for the return flow|°C (x10)|int|20s (per panel)|
|PLC_PLC_Q101.Min_visu_portata1|||int|20s (per panel)|
|PLC_PLC_Q101.Min_visu_portata2|||int|20s (per panel)|
|PLC_PLC_Q101.Ore_lavoro_p101|Working hours for pump p101|hours|int|20s (per panel)|
|PLC_PLC_Q101.Ore_lavoro_p102|Working hours for pump p102|hours|int|20s (per panel)|
|PLC_PLC_Q101.Ore_lavoro_p103|Working hours for pump p103|hours|int|20s (per panel)|
|PLC_PLC_Q101.Ore_lavoro_p104|Working hours for pump p104|hours|int|20s (per panel)|
|PLC_PLC_Q101.Ore_parziali_p101|Partial hours for pump p101|hours|int|20s (per panel)|
|PLC_PLC_Q101.Ore_parziali_p102|Partial hours for pump p102|hours|int|20s (per panel)|
|PLC_PLC_Q101.Ore_parziali_p103|Partial hours for pump p103|hours|int|20s (per panel)|
|PLC_PLC_Q101.Ore_parziali_p104|Partial hours for pump p104|hours|int|20s (per panel)|
|PLC_PLC_Q101.Out_pid_pompe|Pump's PID output||int|20s (per panel)|
|PLC_PLC_Q101.Out_pid_val|Valve's PID output||int|20s (per panel)|
|PLC_PLC_Q101.P101_fault|Fault status for pump p101||int|20s (per panel)|
|PLC_PLC_Q101.P101_in_marcia|Running status for pump p101||int|20s (per panel)|
|PLC_PLC_Q101.P102_fault|Fault status for pump p102||int|20s (per panel)|
|PLC_PLC_Q101.P102_in_marcia|Running status for pump p102||int|20s (per panel)|
|PLC_PLC_Q101.P103_fault|Fault status for pump p103||int|20s (per panel)|
|PLC_PLC_Q101.P103_in_marcia|Running status for pump p103||int|20s (per panel)|
|PLC_PLC_Q101.P104_fault|Fault status for pump p104||int|20s (per panel)|
|PLC_PLC_Q101.P104_in_marcia|Running status for pump p104||int|20s (per panel)|
|PLC_PLC_Q101.Pb_arresto_p101|||int|20s (per panel)|
|PLC_PLC_Q101.Pb_arresto_p102|||int|20s (per panel)|
|PLC_PLC_Q101.Pb_arresto_p103|||int|20s (per panel)|
|PLC_PLC_Q101.Pb_arresto_p104|||int|20s (per panel)|
|PLC_PLC_Q101.Pb_marcia_p101|||int|20s (per panel)|
|PLC_PLC_Q101.Pb_marcia_p102|||int|20s (per panel)|
|PLC_PLC_Q101.Pb_marcia_p103|||int|20s (per panel)|
|PLC_PLC_Q101.Pb_marcia_p104|||int|20s (per panel)|
|PLC_PLC_Q101.Portata_1|Flow rate sensor 1|m3/h (x50)|int|20s (per panel)|
|PLC_PLC_Q101.Portata_1_hmi|Flow rate (HMI panel) sensor 1|m3/h (x10)|int|20s (per panel)|
|PLC_PLC_Q101.Portata_2|Flow rate sensor 2|m3/h (x50)|int|20s (per panel)|
|PLC_PLC_Q101.Portata_2_hmi|Flow rate (HMI panel) sensor 2|m3/h (x10)|int|20s (per panel)|
|PLC_PLC_Q101.Portata_attiva|Active flow rate |m3/h (x10)|int|20s (per panel)|
|PLC_PLC_Q101.Pos_valvola1|Valve 1 position|% (x100)|int|20s (per panel)|
|PLC_PLC_Q101.Pos_valvola_2|Valve 2 position|% (x100)|int|20s (per panel)|
|PLC_PLC_Q101.Posizione_ty141|Valve ty141 position|% |int|20s (per panel)|
|PLC_PLC_Q101.Posizione_ty142|Valve ty142 position|%|int|20s (per panel)|
|PLC_PLC_Q101.Rif_auto_attivo|Automatic active reference |%|int|20s (per panel)|
|PLC_PLC_Q101.Rif_auto_p101|Automatic reference for pump p101|%|int|20s (per panel)|
|PLC_PLC_Q101.Rif_auto_p102|Automatic reference for pump p102|%|int|20s (per panel)|
|PLC_PLC_Q101.Rif_auto_ty141|Automatic reference for valve ty141|%|int|20s (per panel)|
|PLC_PLC_Q101.Rif_auto_ty142|Automatic reference for valve ty142|%|int|20s (per panel)|
|PLC_PLC_Q101.Rif_inverter|Inverter reference|% (x100)|int|20s (per panel)|
|PLC_PLC_Q101.Rif_man_p101|Manual reference for pump p101|%|int|20s (per panel)|
|PLC_PLC_Q101.Rif_man_p102|Manual reference for pump p102|%|int|20s (per panel)|
|PLC_PLC_Q101.Rif_man_ty141|Manual reference for valve ty141|%|int|20s (per panel)|
|PLC_PLC_Q101.Rif_man_ty142|Manual reference for valve ty142|%|int|20s (per panel)|
|PLC_PLC_Q101.Sel_misuratore|Probe selector||int|20s (per panel)|
|PLC_PLC_Q101.Set_man_pid_pompe|Manual set point for the pump's PID|% (x100)|int|20s (per panel)|
|PLC_PLC_Q101.Set_man_pid_valv|Manual set point for the valve's PID|% (x100)|int|20s (per panel)|
|PLC_PLC_Q101.Set_temperatura|Temperature set point|°C (x10)|int|20s (per panel)|
|PLC_PLC_Q101.Start_impianto|Plant start status||int|20s (per panel)|
|PLC_PLC_Q101.Start_p101|Start status for pump p101||int|20s (per panel)|
|PLC_PLC_Q101.Start_p102|Start status for pump p102||int|20s (per panel)|
|PLC_PLC_Q101.Start_p103|Start status for pump p103||int|20s (per panel)|
|PLC_PLC_Q101.Start_p104|Start status for pump p104||int|20s (per panel)|
|PLC_PLC_Q101.Stato_p101|Status for pump p101||int|20s (per panel)|
|PLC_PLC_Q101.Stato_p102|Status for pump p102||int|20s (per panel)|
|PLC_PLC_Q101.Stato_p103|Status for pump p103||int|20s (per panel)|
|PLC_PLC_Q101.Stato_p104|Status for pump p104||int|20s (per panel)|
|PLC_PLC_Q101.Stato_quadro|Panel status||int|20s (per panel)|
|PLC_PLC_Q101.Status_w1|||int|20s (per panel)|
|PLC_PLC_Q101.Status_w2|||int|20s (per panel)|
|PLC_PLC_Q101.T_mandata_hmi|Supply flow temperature (HMI panel)|°C (x10)|int|20s (per panel)|
|PLC_PLC_Q101.T_ritorno_hmi|Return flow temperature (HMI panel)|°C (x10)|int|20s (per panel)|
|PLC_PLC_Q101.T_scambio_cavedio|Exchange temperature air shaft|°C|int|20s (per panel)|
|PLC_PLC_Q101.T_scambio_quadri|Exchange temperature panels|°C|int|20s (per panel)|
|PLC_PLC_Q101.T_scambio_sala|Exchange temperature room|°C|int|20s (per panel)|
|PLC_PLC_Q101.Td_pid_pompe|Derivative gain of the pump's PID||int|20s (per panel)|
|PLC_PLC_Q101.Td_pid_valvole|Derivative gain of the valve's PID||int|20s (per panel)|
|PLC_PLC_Q101.Temp_mandata|Supply flow temperature|°C (x10)|int|20s (per panel)|
|PLC_PLC_Q101.Temp_ritorno|Return flow temperature |°C (x10)|int|20s (per panel)|
|PLC_PLC_Q101.Ti_pid_pompe|Integral gain of the pump's PID||int|20s (per panel)|
|PLC_PLC_Q101.Ti_pid_valvole|Integral gain of the valve's PID||int|20s (per panel)|
|PLC_PLC_Q101.V_min_rem_cavedio|Remaining minutes air shaft|minutes|int|20s (per panel)|
|PLC_PLC_Q101.V_min_rem_quadro|Remaining minutes panel|minutes|int|20s (per panel)|
|PLC_PLC_Q101.V_min_rem_sala|Remaining minutes room|minutes|int|20s (per panel)|
|PLC_PLC_Q101.V_ore_parz_p101|Partial hours for pump p101|Hours|int|20s (per panel)|
|PLC_PLC_Q101.V_ore_parz_p102|Partial hours for pump p102|Hours|int|20s (per panel)|
|PLC_PLC_Q101.V_ore_parz_p103|Partial hours for pump p103|Hours|int|20s (per panel)|
|PLC_PLC_Q101.V_ore_parz_p104|Partial hours for pump p104|Hours|int|20s (per panel)|
|PLC_PLC_Q101.V_ore_parz_quadro|Partial hours panel|Hours|int|20s (per panel)|
|PLC_PLC_Q101.V_ore_rem_cavedio|Remaining hours air shaft|Hours|int|20s (per panel)|
|PLC_PLC_Q101.V_ore_rem_quadro|Remaining hours panel|Hours|int|20s (per panel)|
|PLC_PLC_Q101.V_ore_rem_sala|Remaining hours room|Hours|int|20s (per panel)|
|PLC_PLC_Q101.V_ore_tot_p101|Total running hours for pump p101|Hours|int|20s (per panel)|
|PLC_PLC_Q101.V_ore_tot_p102|Total running hours for pump p102|Hours|int|20s (per panel)|
|PLC_PLC_Q101.V_ore_tot_p103|Total running hours for pump p103|Hours|int|20s (per panel)|
|PLC_PLC_Q101.V_ore_tot_p104|Total running hours for pump p104|Hours|int|20s (per panel)|
|PLC_PLC_Q101.V_ore_tot_quadro|Total running hours panel|Hours|int|20s (per panel)|





# Plugin
The Slurm plugin (time series data) collects some aggragated data from the Slurm Workload Manager server of the Cineca clusters. NOTE: it is a work in progress and may have some inconsistencies.

## Plugin-specific columns

|Column|Description|
|------|-----------|
|partition|Name of assigned partition (anonymized)|
|qos|Quality of Service (anonymized, categorical)|
|job_state|State of the job, see enum job_states for possible values|
|user_id|User ID for a job or job step (anonymized)|

## Metrics
|Metric|Description|Value type|Sampling period|
|------|-----------|----------|---------------|
|cluster_cpu_util|Total number of CPU used in the cluster in percent|int|5s|
|cluster_memory_util|Total RAM used in the cluster in percent|int|5s|
|job_id|Per Job status (anonymized)|int|None (based on jobs)|
|num_nodes|Per Job number of nodes|int|None (based on jobs)|
|s21.cluster_cpu_util|Total number of CPU used in the cluster in percent|float|10s (per partition and qos)|
|s21.cluster_gpu_util|Total number of GPU used in the cluster in percent|float|10s (per partition and qos)|
|s21.cluster_mem_util|Total RAM used in the cluster in percent|float|10s (per partition and qos)|
|s21.jobs.avg_waiting_hour|The average time (hours) the running jobs stayed in the PENDING status|float|10s (per partition and qos)|
|s21.jobs.eligible|The number of pending jobs already eligible for execution and waiting only for resources|int|10s (per partition and qos)|
|s21.jobs.eligible_v2|The number of pending jobs already eligible for execution and waiting only for resources|int|10s (per partition and qos)|
|s21.jobs.nodes_eligible|The number of node requested by the eligible jobs|int|10s (per partition and qos)|
|s21.jobs.nodes_eligible_v2|The number of node requested by the eligible jobs|int|10s (per partition and qos)|
|s21.jobs.p95_waiting_hour|95th percentile of the jobs' waiting time |float|10s (per partition and qos)|
|s21.jobs.tot_gpus|Total number of GPUs requested by the jobs|int|10s (per partition and qos)|
|s21.jobs.tot_jobs|Total number of jobs|int|10s (per partition and qos)|
|s21.jobs.tot_node_hour|The product of the waiting time (hours) and the number of nodes for the jobs in the PENDING state.|float|10s (per partition and qos)|
|s21.jobs.tot_nodes|Total number of nodes requested by the jobs|int|10s (per partition and qos)|
|s21.totals.cpus_alloc|Total number of CPUs allocated to a job|int|10s (per partition and qos)|
|s21.totals.cpus_config|Total number of CPUs configured in the batch scheduler|int|10s (per partition and qos)|
|s21.totals.cpus_down|Total number of CPUs not usable|int|10s (per partition and qos)|
|s21.totals.cpus_eligible|Total number of CPUs usable|int|10s (per partition and qos)|
|s21.totals.cpus_idle|Total number of CPUs not allocated to a job|int|10s (per partition and qos)|
|s21.totals.gpus_alloc|Total number of GPUs allocated to a job|int|10s (per partition and qos)|
|s21.totals.gpus_config|Total number of GPUs configured in the batch scheduler|int|10s (per partition and qos)|
|s21.totals.gpus_down|Total number of GPUs not usable|int|10s (per partition and qos)|
|s21.totals.gpus_eligible|Total number of GPUs usable|int|10s (per partition and qos)|
|s21.totals.gpus_idle|Total number of GPUs not allocated to a job|int|10s (per partition and qos)|
|s21.totals.memory_alloc|Total RAM allocated (MB)|int|10s (per partition and qos)|
|s21.totals.memory_config|Total RAM configured in the batch scheduler (MB)|int|10s (per partition and qos)|
|s21.totals.memory_down|Total RAM not usable (MB)|int|10s (per partition and qos)|
|s21.totals.memory_eligible|Total RAM usable (MB)|int|10s (per partition and qos)|
|s21.totals.memory_idle|Total RAM not allocated to a job (MB)|int|10s (per partition and qos)|
|s21.totals.total_nodes_alloc|Total number of nodes allocated to a job|int|10s (per partition and qos)|
|s21.totals.total_nodes_config|Total number of nodes configured in the batch scheduler|int|10s (per partition and qos)|
|s21.totals.total_nodes_down|Total number of nodes not usable|int|10s (per partition and qos)|
|s21.totals.total_nodes_eligible|Total number of nodes usable|int|10s (per partition and qos)|
|s21.totals.total_nodes_idle|Total number of nodes not allocated to a job|int|10s (per partition and qos)|
|s21.totals.total_nodes_mixed|Total number of nodes in the MIXED state|int|10s (per partition and qos)|
|total_cpus_alloc|Total number of CPUs allocated to a job|int|5s|
|total_cpus_config|Total number of CPUs configured in the batch scheduler|int|5s|
|total_cpus_down|Total number of CPUs not usable|int|5s|
|total_cpus_eligible|Total number of CPUs usable|int|5s|
|total_cpus_idle|Total number of CPUs not allocated to a job|int|5s|
|total_memory_alloc|Total RAM allocated (MB)|int|5s|
|total_memory_config|Total RAM configured in the batch scheduler (MB)|int|5s|
|total_memory_down|Total RAM not usable (MB)|int|5s|
|total_memory_eligible|Total RAM usable (MB)|int|5s|
|total_memory_idle|Total RAM not allocated to a job (MB)|int|5s|
|total_nodes_alloc|Total number of nodes allocated to a job|int|5s|
|total_nodes_config|Total number of nodes configured in the batch scheduler|int|5s|
|total_nodes_down|Total number of nodes not usable|int|5s|
|total_nodes_eligible|Total number of nodes usable|int|5s|
|total_nodes_idle|Total number of nodes not allocated to a job|int|5s|
|total_nodes_mixed|Total number of nodes in the MIXED state|int|5s|



# Vertiv
The Vertiv plugin mainly collects data from the air-conditioning units (CDZ) located in room F (Marconi 100) of Cineca.The plugin uses the RESTful API interface available on the individual devices to extract the most interesting metrics.

## Plugin-specific columns

|Column|Description|
|------|-----------|
|device|Name of the device| 

## Metrics
|Metric|Description|Unit|Value type|Sampling period|
|------|-----------|----|----------|---------------|
|Actual_Return_Air_Temperature_Set_Point|Set Point of the air temperature at the device inlet|°C|float|10s (per device)|
|Actual_Return_Humidity_Set_Point|Set Point of the air humidity at the device inlet (when enabled)|%RH|float|10s (per device)|
|Adjusted_Humidity|Value of the adusted humidity|%|float|10s (per device)|
|Compressor_Utilization|Utilization level of the compressor in the cooling circuit|%|float|10s (per device)|
|Dehumidifier_Utilization|Utilization level of the dehumidifier (when enabled)|%|float|10s (per device)|
|Ext_Air_Sensor_A_Humidity|Exit air humidity retrieved by the external sensor A|%RH|float|10s (per device)|
|Ext_Air_Sensor_A_Temperature|Exit air temperature retrieved by the external sensor A|°C|float|10s (per device)|
|Ext_Air_Sensor_B_Humidity|Exit air humidity retrieved by the external sensor B|%RH|float|10s (per device)|
|Ext_Air_Sensor_B_Temperature|Exit air temperature retrieved by the external sensor B|°C|float|10s (per device)|
|Ext_Air_Sensor_C_Humidity|Exit air humidity retrieved by the external sensor C|%RH|float|10s (per device)|
|Ext_Air_Sensor_C_Temperature|Exit air temperature retrieved by the external sensor C|°C|float|10s (per device)|
|Fan_Speed|Cooling fan speed|%|float|10s (per device)|
|Filter_Pressure_Drop|Pressure drop at the inlet filter|Pa|float|10s (per device)|
|Free_Cooling_Fluid_Temperature|Temperature of the fluid in the free-cooling circuit|°C|float|10s (per device)|
|Free_Cooling_Status|Status of the free-cooling system|_|float|10s (per device)|
|Free_Cooling_Valve_Open_Position|Free-cooling three-way valve position |%|float|10s (per device)|
|Hot_Water___Hot_Gas_Valve_Open_Position|Status of the hot water/gas valve|%|float|10s (per device)|
|Humidifier_Utilization|Utilization level of the humidifier (when enabled)|%|float|10s (per device)|
|Humidity_Set_Point|Set Point of the air humidity|%RH|float|10s (per device)|
|Reheat_Utilization|Utilization level of the reheat unit (when enabled)|%|float|10s (per device)|
|Return_Air_Temperature|Temperature of the air at the device inlet|°C|float|10s (per device)|
|Return_Humidity|Humidity of the air at the device inlet|%RH|float|10s (per device)|
|Supply_Air_Temperature|Temperature of the air at the device outlet|°C|float|10s (per device)|
|Supply_Air_Temperature_Set_Point|Set Point of the air temperature at the device outlet|°C|float|10s (per device)|
|Underflow_Static_Pressure|Static pressure at the device outlet (when enabled)|Pa|float|10s (per device)|




# Weather
This plugin collects all the weather data related to the Cineca facility location (Casalecchio di Reno) using an online open weather service  (https://openweathermap.org). 

NOTE: In ExaMon forecasts are collected too, here we just keep the current values.

## Metrics
|Metric|Description|Unit|Value type|Sampling period|
|------|-----------|----|----------|---------------|
|clouds|Cloudiness|%|int|10m|
|dew_point|Atmospheric temperature (varying according to pressure and humidity) below which water droplets begin to condense and dew can form|°C|float|10m|
|feels_like|Temperature. This accounts for the human perception of weather.|°C|float|10m|
|humidity|Humidity|%|int|10m|
|pressure|Atmospheric pressure on the sea level|hPa|int|10m|
|temp|Temperature|°C|float|10m|
|uvi|UV index||float|10m|
|visibility|Average visibility, metres. The maximum value of the visibility is 10km|m|int|10m|
|wind_deg|Wind direction|deg|int|10m|
|wind_speed|Wind speed|m/s|float|10m|