<!DOCTYPE html>
<html>
<head>
    <title>Ska Packages</title>
    <script src="https://ajax.googleapis.com/ajax/libs/jquery/1.11.2/jquery.js" type="text/javascript"></script>
    <script src="https://netdna.bootstrapcdn.com/bootstrap/3.3.1/js/bootstrap.min.js" type="text/javascript"></script>
    <script src="watable/jquery.watable.js" type="text/javascript" charset="utf-8"></script>
    <link rel='stylesheet' href="https://netdna.bootstrapcdn.com/bootstrap/3.3.1/css/bootstrap.min.css" />
    <link rel='stylesheet' href='watable/watable.css'/>
    <style type="text/css">
        body { padding: 30px; font-size: 12px }
    </style>
</head>
<body>
    <h2>Ska Packages</h2>
    <p></p>

    <div id="ska_packages_table" style="width:auto"></div>

    <script type="text/javascript">
        $(document).ready( function() {
          var waTable = $('#ska_packages_table').WATable({
            data: getData(),
            debug:false,                //Prints some debug info to console
            dataBind: true,             //Auto-updates table when changing data row values. See example below. (Note. You need a column with the 'unique' property)
            pageSize: 1000,                //Initial pagesize
            pageSizePadding: false,      //Pads with empty rows when pagesize is not met
            //transition: 'slide',       //Type of transition when paging (bounce, fade, flip, rotate, scroll, slide).Requires https://github.com/daneden/animate.css.
            //transitionDuration: 0.2,    //Duration of transition in seconds.
            filter: true,               //Show filter fields
            sorting: true,              //Enable sorting
            sortEmptyLast:false,         //Empty values will be shown last
            columnPicker: true,         //Show the columnPicker button
            pageSizes: [1,5,8,12,200],  //Set custom pageSizes. Leave empty array to hide button.
            hidePagerOnEmpty: true,     //Removes the pager if data is empty.
            checkboxes: false,           //Make rows checkable. (Note. You need a column with the 'unique' property)
            checkAllToggle:true,        //Show the check-all toggle
            preFill: false,              //Initially fills the table with empty rows (as many as the pagesize).
            types: {                    //If you want, you can supply some properties that will be applied for specific data types.
              string: {
                //filterTooltip: "Giggedi...",    //What to say in tooltip when hoovering filter fields. Set false to remove.
                placeHolder: "Type here..."    //What to say in placeholder filter fields. Set false for empty.
              },
              number: {
                decimals: 1   //Sets decimal precision for float types
              },
              bool: {
                //filterTooltip: false
              },
              date: {
                utc: true,            //Show time as universal time, ie without timezones.
                //format: 'yyyy-MM-dd hh:mm:ss',   //The format. See all possible formats here http://arshaw.com/xdate/#Formatting.
                format: 'MMM dd yyyy, hh:mm:ss',   //The format. See all possible formats here http://arshaw.com/xdate/#Formatting.
                datePicker: true      //Requires "Datepicker for Bootstrap" plugin (http://www.eyecon.ro/bootstrap-datepicker).
              }
            },
            tableCreated: function (data) {
              $('tfoot p, tfoot .pagesize, tfoot .pagelinks', this).hide();
              //$('tfoot p, li:not(:first):not(:last)', this).hide();
            }
          }).data('WATable');  //This step reaches into the html data property to get the actual WATable object. Important if you want a reference to it as we want here.
        });


        function getData() {

          var cols = {
            pkg: {
              index: 1,
              type: "string",
              friendly: "Package",
              unique: true,
              placeHolder: "pkg name", // place holder in the filter entry
              //filter: false, // would remove filtering
              sortOrder: "asc", //Data will initially be sorted by this column. Possible are "asc" or "desc"
              //format: "<a href='https://github.com/sot/{0}'>{0}</a>",
            },
            owner: {
              index: 1,
              type: "string",
              friendly: "Owner",
              hidden: true
            },
            branches: {
              index: 2,
              type: "number",
              friendly: "Branches",
              tooltip: "Number of branches",
              hidden: true
            },
            issues: {
              index: 3,
              type: "number",
              friendly: "Issues",
              tooltip: "Number of open issues"
            },
            pr: {
              index: 4,
              type: "number",
              friendly: "PRs",
              tooltip: "Number of open pull requests"
            },
            tag: {
              index: 5,
              type: "string",
              friendly: "Tag",
              placeHolder: "0.0.0",
              filterTooltip: "filter the tags",
              tooltip: "Latest release"
            },
            date: {
              index: 6,
              type: "string",
              friendly: "Date",
              filterTooltip: "filter the dates",
              tooltip: "Date of the latest release",

            },
            commits: {
              index: 7,
              type: "number",
              friendly: "commits",
              tooltip: "Commits since last release"
            },
            merge_info: {
              index: 8,
              type: "string",
              friendly: "Merges",
              tooltip: "Merges since last release",
            }
          };

          var rows = [
            {% for pkg in packages %}
            { pkg: "<a href='https://github.com/{{ pkg.owner }}/{{ pkg.name }}'> {{ pkg.name }} </a>",
              owner: "{{ pkg.owner }}",
              branches: {{ pkg.branches }},
              branchesFormat: "<a href='https://github.com/{{ pkg.owner }}/{{ pkg.name }}/branches'> {{ pkg.branches }} </a>",
              issues: {{ pkg.issues }},
              issuesFormat: "<a href='https://github.com/{{ pkg.owner }}/{{ pkg.name }}/issues'> {{ pkg.issues }} </a>",
              pr: {{ pkg.pull_requests }},
              prFormat: "<a href='https://github.com/{{ pkg.owner }}/{{ pkg.name }}/pulls'> {{ pkg.pull_requests }} </a>",
              tag: "{{ pkg.last_tag }}",
              tagFormat: "<a href='https://github.com/{{ pkg.owner }}/{{ pkg.name }}/releases/tag/{{ pkg.last_tag }}'> {{ pkg.last_tag }} </a>",
              date: "{{ pkg.last_tag_date }}",
              commits: {{ pkg.commits }},
              merges: {{ pkg.merges }},
              merge_info: "{% for msg in pkg.merge_info %} {{ msg }} <br/> {% endfor %}"
            },
            {% endfor %}
          ];

          var data = {
            cols: cols,
            rows: rows,
            extra: {} // optional
            };
          return data;
        }

</script>
</body>
</html>
