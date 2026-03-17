# 📊 ODA Agent – Query List

This document lists all the queries that the **Operational Data Analysis (ODA) Agent** can handle.  
These queries are related to **HPC system topology**, **job statistics**, **resource utilization**, and **environmental monitoring**.

---

## 🧩 System Topology & Structure

- What is the position of node **X**?  
- How many racks are there in an HPC system **X**?  
- Which nodes are part of the rack **X**?  
- How many HPC systems do we have?

---

## 👥 User & Job Management

- Give me a list of users who submitted jobs in a specified time period.  
- Give me a list of jobs submitted by the user **X** in a specified time period.  
- Give me a list of jobs submitted in a specified time period.  
- Which user submitted job **X**?  
- Give details of job **X**.  
- How many jobs were running in a specified time period?  
- How many jobs had a time duration above a certain value?  
- Which user submitted jobs during a specified period?  
- How many jobs did a user **U** submit on a compute node **N** in a specified period?  
- Which users belong to a group **G**?

---

## ⚡ Power & Energy Monitoring

- What is the power consumption of the node **X** in a specified time period?  
- What is the power consumption of the rack **X** in a specified time period?

---

## 🌡️ Environmental & Performance Metrics

- What is the max/min/avg recorded metric **X** for compute node **N** from **T1** to **T2**?  
- What is the max/min/avg recorded metric **X** for rack **R** today?  
- What is the max/min/avg recorded metric **X** for Job **J**?  
- Can you tell me the list of compute nodes that had temperatures higher than normal in a specified time period?  
- Please provide me the compute node **N** average temperature during May 2025.

---

## 🧠 Notes

These queries are handled by the **ODA Agent**, which accesses:  
- HPC telemetry and monitoring databases  
- Job scheduler and accounting logs  
- Facility and environmental monitoring systems (temperature, power, etc.)

---

**Filename:** `ODA_Agent_Queries.md`
