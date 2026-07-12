        $.ajax({
            type:     "GET",
            url:      "/apps/api/get.php?key=be7b42f272ba686a&format=JSON&htmlentities=1",
            dataType: "text",
            success: function(data)    {
                                            $("#apiJsonExample").html('<pre><code class="language-json" id="code-JSON">'+ data +'</code></pre>');
                                            Prism.highlightElement($('#code-JSON')[0]);
                                       },
            error:   function (result) {}
        });
        $.ajax({
            type:     "GET",
            url:      "/apps/api/get.php?key=be7b42f272ba686a&format=XML&htmlentities=1",
            dataType: "text",
            success: function(data)    {
                                            $("#apiXmlExample").html('<pre><code class="language-markup" id="code-XML">'+ data +'</code></pre>');
                                            Prism.highlightElement($('#code-XML')[0]);
                                       },
            error:   function (result) {}
        });
