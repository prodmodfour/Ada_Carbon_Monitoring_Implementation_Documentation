# Implementation Review

This is a brief review of other implementations of carbon-awareness monitoring in other platforms.

## Google's Carbon-Aware Data Center Operations

### **Link:** https://arxiv.org/abs/2106.11750

 **Summary:** Google has developed a system that forecasts the hourly carbon intensity of the local electricity grid for the following day. It combines this with its own internal forecast for power usage to make decisions on when and where to run computing tasks. This allows Google to time-shift flexible workloads to periods of low carbon intensity and location-shift tasks to data centers in regions with cleaner energy grids. The key implementation detail they use for this is Virtual Capacity Curves (VCCs).

Virtual Capacity Curves (VCCs) are hour-by-hour “phantom” ceilings that Google places on each data-center cluster’s CPU pool for the next day. Behind the scenes, an optimisation pipeline ingests three inputs—(1) a grid-carbon forecast for every region, (2) a day-ahead demand forecast that splits workloads into flexible vs. inflexible, and (3) hard limits such as campus power contracts and machine capacity. It then solves a risk-aware objective that weighs carbon, peak-power costs and service-level guarantees, producing a 24-point curve for every cluster

**Key Takeaway:**
This isn't one to one applicable for our needs. We're limited to one site so the location shifting aspects aren't relevant. The service wouldn't be willing to enforce hard caps on its users, which is reasonable and not something that we'd push for.

But a simpler version of a Virtual Capacity Curve, one that is only interested in time based carbon intensity, could be useful. It wouldn't exist to programmatically stop usage past a certain point. 
It would help both the user and the service know what green usage looks like and how we're falling short (if we're falling short).


## Energy and Policy Considerations for Deep Learning in NLP

### **Link**: https://aclanthology.org/P19-1355/


**Summary:** This paper provides a methodology for quantifying the carbon emissions and financial costs associated with training large AI models. It famously calculated that training one specific AI model emitted as much carbon as five American cars in their lifetimes, including manufacturing. 

**Key Takeaway:**
This won't be relevant to any implementation for the Ada platform. AI training doesn't seem to be a common usage of the platform. 

Regardless, the high carbon cost of AI training means that it would be worth looking into this again when we get to Milestone 4 of the project (Guidelines for other organisations). 


## Microsoft's Carbon-Aware Updates for Windows & Xbox

### **Link**: https://support.microsoft.com/en-gb/windows/windows-update-is-now-carbon-aware-a53f39bc-5531-4bb1-9e78-db38d7a6df20

**Summary:** This is a practical, large-scale example of time-shifting. Microsoft has configured both its Windows Update service and Xbox consoles to schedule non-urgent tasks, like software updates and game downloads, during times when the local grid has a higher concentration of low-carbon electricity. For Xbox, this is often overnight. This approach demonstrates how to apply carbon-awareness directly to consumer-facing services to significantly reduce emissions

**Key Takeaway:**
This isn't relevant to Milestone 3 of the project (Software Implementations for Ada). 

It is however a very good example of demand shaping and is relevant to Milestone 4 of the project (Guidelines for other organisations). 

## AWS Carbon Footprint Tool

### **Link**: https://aws.amazon.com/aws-cost-management/aws-customer-carbon-footprint-tool/

**Summary:** The AWS Customer Carbon Footprint Tool is a feature available in the AWS Billing console that helps customers track, measure, review, and forecast the carbon emissions generated from their AWS usage. The tool provides data visualizations to show carbon emissions by AWS Region and by service, allowing users to understand their carbon footprint's primary drivers. The data is calculated based on the Greenhouse Gas (GHG) Protocol and is updated monthly with a three-month delay. The tool allows for data to be exported in CSV or Parquet formats, enabling easier integration with other reporting systems. The methodology has been updated to provide a more accurate picture of a customer's carbon footprint, now allocating emissions from unused server capacity proportionally to all customers.

**Key Takeaway:**
GHG Protocol is a good standard for calculating carbon emissions. We likely don't have the data needed to implement this ourselves but we can create an approximation and present it in our mockups to the users. If the mock values are deemeed to be useful to the users, it could be used to support an attempt to get more data.

## Software Carbon Intensity (SCI) Specification

### **Link**: https://github.com/Green-Software-Foundation/sci

**Summary:** The Software Carbon Intensity (SCI) Specification, developed by the Green Software Foundation, provides a standardized methodology for calculating the rate of carbon emissions from a software application. The SCI score is a rate, measuring carbon per unit of work (e.g., per API call, per user, or per minute). The calculation takes into account the energy consumed by the software, the carbon intensity of the energy source, and the embodied carbon of the hardware it runs on. The goal is to provide a consistent and comparable measure to help developers and organizations make informed decisions to reduce the carbon footprint of their software. It has been recognized as an ISO standard (ISO/IEC 21031:2024), which should encourage wider adoption.

**Key Takeaway:**
We want to use recognised, standardised metrics for our project. This is a good example of a standard that we could use. Again, we don't have the data we need, but a mock implementation is good enough to get the point across and receive feedback. If it's deemed useful, we could use it to support an attempt to get more data.


## Cloud Carbon Footprint

### **Link**: https://github.com/cloud-carbon-footprint/cloud-carbon-footprint

**Summary:** Cloud Carbon Footprint is an open-source tool originally created by Thoughtworks that provides visibility into the carbon emissions of cloud usage. It ingests billing and usage data from major cloud providers (AWS, Google Cloud, and Microsoft Azure) and estimates the associated energy consumption and carbon emissions. The tool presents this information through a dashboard, allowing users to filter by service, time period, and account. It aims to help organizations understand their cloud carbon footprint and identify areas for improvement.

**Key Takeaway:**
This is a great reference for what a practical implementation looks like. As an open-source tool, its methodologies for estimating emissions are transparent. We can't use the tool directly since we're not a typical cloud customer, but we can use its dashboard and data presentation as a model for our own mockups. 

## Green Algorithms Tool

### **Link**: https://github.com/GreenAlgorithms/green-algorithms-tool

**Summary:** The Green Algorithms tool is a free online calculator designed to estimate the carbon footprint of a computational task. It allows researchers and developers to input parameters about their computation—such as the type and number of processors (CPU or GPU), the amount of memory used, the running time, and the location of the data center—to get an estimate of the CO2 equivalent emissions. The key to its approach is that it doesn't require direct power measurement. Instead, it uses a model based on the manufacturer-provided Thermal Design Power (TDP) for hardware components, which represents the maximum heat a component is expected to generate. It combines this with the Power Usage Effectiveness (PUE) of the data center and the carbon intensity of the local energy grid to produce its estimate.

The tool provides fallbacks for when data is unavailable, allowing for users to do calculations when they're lacking data

**Key Takeaway:**
Their methodology for estimating emissions is likely more accurate than our own. If we can find out the PUE of the data centre and the specifics of the hardware, we could adopt it. It is valuable to use methodologies for estimation that are used by other implementations. 

If the data centre doesn't know it's own PUE (unlikely), this could be a push for them to find out. This itself would be a valuable outcome for the sake of improving sustainability.

We should also implement a system of fallback values for missing data.


