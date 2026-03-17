# 🧠 CINECA HPC Operational & Energy Analytics – User Questions

This document lists the questions proposed by **CINECA datacenter staff** regarding **energy, thermal, and operational analytics** for HPC systems.  
These queries can be used for benchmarking, agentic reasoning, and RAG-based question answering within the ODA (Operational Data Analysis) agent.

---

## ⚡ Energy & Power Consumption

**CinecaNo1:**  
> How much energy is consumed by the nodes, racks, and machine over a given period of time?

**CinecaNo2:**  
> How much energy is consumed by the cooling system (air and water) over a given period of time?

**CinecaNo2b:**  
> What is the PUE (Power Usage Effectiveness) of a machine or compute room over a given period of time?

---

## 🧩 Job & Resource Utilization

**CinecaNo3:**  
> How many jobs are running on a particular node over a given period of time?

**CinecaNo5:**  
> Provide the distribution over time of the usage of resources (CPUs, GPUs, Memory) before a node fails, over a given period of time.

**CinecaNo8:**  
> Give me the node’s resource utilization distribution when the PUE is higher than a given value.

**CinecaNo8b:**  
> Give me the node’s resource utilization distribution for a specific JobID whose job PUE is higher than a given value.

**CinecaNo9:**  
> Give me the node’s resource utilization distribution for a specific JobID whose job power is higher than a given value.

**CinecaNo10:**  
> Provide the node’s resource utilization (or users) distribution for all jobs whose node’s average job power is higher than a given value.

---

## 🌡️ Thermal Behavior & Anomaly Detection

**CinecaNo4:**  
> What are the min, max, and average temperatures when a node is in use, over a given period of time?

**CinecaNo4b:**  
> What are the min, max, and average of the **derivative of temperature** when a node is in use, over a given period of time?

**CinecaNo6:**  
> What is the distribution of the temperature of a node before it fails, over a given period of time (period before failure)?

---

## 💥 Failure & Reliability Analytics

**CinecaNo7:**  
> Provide the list of failing nodes over a given period of time.

**CinecaNo11:**  
> Give me the Job IDs whose node’s instantaneous (or average over time) power/temperature is higher than a given threshold.

---

## 📘 Notes

- These questions reflect **typical analytical needs** from HPC datacenter operators and researchers focusing on:
  - Energy efficiency and cooling optimization  
  - Fault prediction and reliability modeling  
  - Job–power correlation analysis  
  - Thermal–performance coupling studies  
- The queries can serve as a **benchmark dataset** for evaluating LLM-based ODA (Operational Data Analysis) agents.

---

**File:** `CINECA_Questions.md`  
**Author:** CINECA Datacenter Staff  
**Prepared by:** ExaAgent Project – ODA Subsystem  
**Last Updated:** 2025-10-31
