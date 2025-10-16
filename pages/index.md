---
layout: page
title: Table of Contents  
nav_order: 1
nav_exclude: false     
---


# Under construction


# Contents


## Software used
### Databases
* Prometheus
* MongoDB
* SQLite
### Languages
* Python
* JavaScript
### Frontend
* Svelte
* Chart.js
### Backend
* Flask
### Documentation
* Jekyll
* Mermaid.js

## Building the database

## Implementations



<ul>
{% comment %}
  Collect top-level pages that have nav_order (like Just the Docs uses),
  exclude the index itself, and sort by nav_order.
{% endcomment %}
{% assign pages_ordered =
  site.pages
  | where_exp: "p", "p.nav_order"
  | sort: "nav_order"
%}
{% for p in pages_ordered %}
  {% unless p.url == page.url or p.permalink == "/" %}
    <li>
      <a href="{{ p.url | relative_url }}">{{ p.title | default: p.name }}</a>

      {%- comment -%}
      OPTIONAL: naïve H2 extractor. This tries to find lines starting with "## ".
      It then fabricates an ID the way kramdown usually would. This is brittle:
      duplicates/punctuation/non-ASCII may not match the real IDs.
      Remove this block if you don't want it.
      {%- endcomment -%}
      {% capture raw %}{{ p.content }}{% endcapture %}
      {% assign sections = raw | split: "\n## " %}
      {% if sections.size > 1 %}
        <ul>
        {% for s in sections offset:1 %}
          {% assign heading = s | split: "\n" | first | strip %}
          {% assign id = heading | downcase
                               | replace: " ", "-"
                               | replace: "(", "" | replace: ")", ""
                               | replace: ".", "" | replace: ",", ""
                               | replace: ":", "" | replace: ";", ""
                               | replace: "/", "" | replace: "\\", ""
                               | replace: "&", "and"
                               | replace: "'", "" | replace: "\"", "" %}
          <li><a href="{{ p.url | relative_url }}#{{ id }}">{{ heading }}</a></li>
        {% endfor %}
        </ul>
      {% endif %}
    </li>
  {% endunless %}
{% endfor %}
</ul>