# ExaBench-QA — Query Set

Owner: Mohsen

This page contains a **curated subset** of the ExaBench-QA query set. It provides representative benchmark queries across personas and QCAT domains (for example: energy, facility, jobs, monitoring, performance) without loading the full, heavy list.

| # | Query | User Type | QCAT | Priority | Difficulty |
| --- | --- | --- | --- | --- | --- |
| 1 | How much energy is consumed by the nodes, racks, and machine over a given period of time? | HPC Researchers, Facility Admin, System Admin, System Designers | ENERGY | High | Medium |
| 2 | How much energy is consumed by the cooling system (air and water) over a given period of time? | Facility Admin, System Designers, HPC Researchers | FAC / ENERGY | High | Medium |
| 3 | What is the PUE (Power Usage Effectiveness) of a machine or compute room over a given period of time? | Facility Admin, System Designers, HPC Researchers | ENERGY | High | Medium |
| 4 | How many jobs are running on a particular node over a given period of time? | System Admin, Normal HPC User, HPC Researchers | JOB | High | Easy |
| 5 | Provide the distribution over time of the usage of resources (CPUs, GPUs, Memory) before a node fails, over a given period of time. | HPC Researchers, System Admin | PERF / MON / AIOPS | High | Hard |
| 6 | Give me the node’s resource utilization distribution when the PUE is higher than a given value. | HPC Researchers, System Designers | ENERGY / AIOPS | High | Hard |
| 7 | Give me the node’s resource utilization distribution for a specific JobID whose job PUE is higher than a given value. | HPC Researchers, System Admin | ENERGY / PERF / AIOPS | High | Hard |
| 8 | Give me the node’s resource utilization distribution for a specific JobID whose job power is higher than a given value. | HPC Researchers, System Admin | ENERGY / PERF | High | Medium |
| 9 | Provide the node’s resource utilization (or users) distribution for all jobs whose node’s average job power is higher than a given value. | HPC Researchers, System Admin | ENERGY / PERF / MON | High | Hard |
| 10 | What are the min, max, and average temperatures when a node is in use, over a given period of time? | Facility Admin, System Admin, HPC Researchers | MON / ENERGY | High | Medium |
| 11 | What are the min, max, and average of the derivative of temperature when a node is in use, over a given period of time? | HPC Researchers, Facility Admin | MON / ENERGY | High | Hard |
| 12 | What is the distribution of the temperature of a node before it fails, over a given period of time (period before failure)? | HPC Researchers, System Admin, Facility Admin | AIOPS / MON | High | Hard |
| 13 | Provide the list of failing nodes over a given period of time. | System Admin, Facility Admin, HPC Researchers | MON / AIOPS | High | Medium |
| 14 | Give me the Job IDs whose node’s instantaneous (or average over time) power/temperature is higher than a given threshold. | System Admin, HPC Researchers | ENERGY / MON / JOB | High | Medium |
| 15 | What is the position of node X? | Facility Admin, System Admin, System Designers | FAC / ARCH | Medium | Easy |
| 16 | How many racks are there in an HPC system X? | System Designers, Facility Admin, System Admin | ARCH / FAC | Medium | Easy |
| 17 | Which nodes are part of the rack X? | System Admin, Facility Admin, System Designers | FAC / ARCH | Medium | Easy |
| 18 | How many HPC systems do we have? | System Designers, System Admin | ARCH / FAC | Medium | Easy |
| 19 | Give me a list of users who submitted jobs in a specified time period. | System Admin, HPC Researchers | JOB / USER | High | Easy |
| 20 | Give me a list of jobs submitted by the user X in a specified time period. | System Admin, HPC Researchers, Normal HPC User | JOB | High | Easy |