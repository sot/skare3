Release {{ version }} includes these PRs:

{% for line in package.merge_info %}- {{ line }}
{% endfor %}
{{ comments }}

