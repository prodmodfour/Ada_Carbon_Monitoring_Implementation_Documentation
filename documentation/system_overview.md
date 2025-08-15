# Presentation

## Ada Platform Recreation in **Django**
* **Pages & Flow**

  * Instrument lists: `instruments_clf` and `instruments_isis`
  * New **Instrument Detail** route: `/analysis/<source>/instruments/<instrument>/`
  * “Create Workspace” posts to detail, then redirects back to **Analysis**

* **Instrument Detail UI**

  * Card header shows **{Chosen Instrument}**
  * Stable “random” specs per instrument (CPUs, RAM, GPUs) seeded by name
  * CPU/RAM icons left of spec text; full card centered
  * “Installed Software” dropdown is non-functional (visual only)

* **Workspaces**

  * Clicking **Create Workspace** adds a workspace to session storage
  * Owner fixed to **Ashraf Hussain**
  * Titles auto-increment: **Workspace 1**, **Workspace 2**, …
  * Workspaces rendered as cards on **Analysis** (desktop + Jupyter previews, disabled Start button)

* **Tech Notes**

  * Session-backed storage per source (`ISIS`, `CLF`); migrate sessions or use signed-cookie backend
  * Minimal CSS added for centering and workspace card layout
  * New/updated templates: `instrument_detail.html`, `analysis.html`, and instrument list links to detail


## Data Display Modules



* Virtual Capacity Curves (Electricity view and carbon view)
  * Needs more research on whether other facilities have used something simlar
* Carbon Intensity Forecast
* Estimated electricity usage of a project over x time period (Selectable data range or day, month, year). This uses TDP calculations.
    * Carbon footprint view
    * Carbon equivalency metrics
* SCI Score
* GHG Score
* Workspace figures
    * Idle Usage Counter per workspace
    * Best time in work hours (8 am to 5 PM) to use in terms of carbon intensity

* Instrument figure
    * Estimated average electricuty/ carbon usage of the instrument per hour


## Real time configuration changes
Uses Django Channels
We keep data loaded in various models
We change MVT relationships using admin panel
We push these relatioships using websockets





# Data 





## Carbon Intensity API Functions

## Prometheus Query Functions

## Electricity Calculation Functions

## Emissions Calculation Functions

## Fallback System





## Data Representation Classes 

### Virtual Capacity Curve

### GHG Protocol Score

### SCI Score

### Idle Carbon Usage Counter

### Carbon Equivalency 










# Future Features

## Simple / Advanced Toggle