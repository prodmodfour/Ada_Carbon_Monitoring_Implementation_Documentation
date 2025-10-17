---
layout: page
title: Table of Contents  
nav_order: 1
nav_exclude: false
permalink: /
---

# [Green Computing Basics]({{ site.baseurl }}{% link pages/0_green_computing_basics.md %})

# [Software Used]({{ site.baseurl }}{% link pages/1_software_used.md %})

# [Backend]({{ site.baseurl }}{% link pages/2_backend.md %})
## [Database Structure]({{ site.baseurl }}{% link pages/2_backend.md %}#database-structure)
## [Database Classes]({{ site.baseurl }}{% link pages/2_backend.md %}#database-classes)
### [Prometheus Request Class]({{ site.baseurl }}{% link pages/2_backend.md %}#prometheus-request-class)
### [MongoDB Request Class]({{ site.baseurl }}{% link pages/2_backend.md %}#mongodb-request-class)
### [Carbon Intensity API Request Class]({{ site.baseurl }}{% link pages/2_backend.md %}#carbon-intensity-api-request-class)
### [ SQLite Class ]({{ site.baseurl }}{% link pages/2_backend.md %}#sqlite-class)
## [Estimating Usage]({{ site.baseurl }}{% link pages/2_backend.md %}#estimating-usage)
### [Electricity]({{ site.baseurl }}{% link pages/2_backend.md %}#electricity)
### [Carbon Footprint]({{ site.baseurl }}{% link pages/2_backend.md %}#carbon-footprint)
## [Workspace Tracking]({{ site.baseurl }}{% link pages/2_backend.md %}#workspace-tracking)
## [Machine Averages]({{ site.baseurl }}{% link pages/2_backend.md %}#machine-averages)
## [Group Attribution]({{ site.baseurl }}{% link pages/2_backend.md %}#group-attribution)
## [User Attribution]({{ site.baseurl }}{% link pages/2_backend.md %}#user-attribution)

# [Frontend]({{ site.baseurl }}{% link pages/3_frontend.md %})
## [Carbon Intensity Forecast]({{ site.baseurl }}{% link pages/3_frontend.md %}#carbon-intensity-forecast)
## [Estimated Usage Graph]({{ site.baseurl }}{% link pages/3_frontend.md %}#estimated-usage-graph)
## [Github Commit History Style Heatmap]({{ site.baseurl }}{% link pages/3_frontend.md %}#github-commit-history-style-heatmap)
## [Workspace Card]({{ site.baseurl }}{% link pages/3_frontend.md %}#workspace-card)
## [Machine Sizes]({{ site.baseurl }}{% link pages/3_frontend.md %}#machine-sizes)
## [Carbon Equivalents]({{ site.baseurl }}{% link pages/3_frontend.md %}#carbon-equivalents)


<h1>{{ page.title }}</h1>

<ul class="toc-root">
  {%- assign toc_pages = site.pages
      | where_exp: "p", "p.path contains 'pages/'"
      | sort: "nav_order" -%}

  {%- for p in toc_pages -%}
    {%- if p.title and p.url != page.url -%}
      <li>
        <a href="{{ p.url | relative_url }}">{{ p.title }}</a>

        {%- comment -%}
        Build the page-relative subheadings list, then prefix each anchor
        with the page URL so links become /pages/2_backend/#section, etc.
        {%- endcomment -%}
        {%- capture subheads -%}{{ p.content | markdownify | toc_only }}{%- endcapture -%}
        {%- capture href_prefix -%}href="{{ p.url | relative_url }}#{%- endcapture -%}

        {%- if subheads contains '<li>' -%}
          <ul class="subheadings">
            {{ subheads | replace: 'href="#', href_prefix }}
          </ul>
        {%- endif -%}
      </li>
    {%- endif -%}
  {%- endfor -%}
</ul>
