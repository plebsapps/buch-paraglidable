if (false)
{
    $.getJSON("cells.json", function(data){loadTmp(data)});

    function loadTmp(decodedJson)
    {
        cellsLayer = L.geoJson(decodedJson, {   style: function(feature)
                                                {
                                                    var minWindCoef = 0.7;
                                                    var maxWindCoef = 1.0;
                                                    var windCoefVal = (feature.properties.windCoef - minWindCoef) / (maxWindCoef - minWindCoef);
                                                    return {"fillOpacity": 0.5, fillColor: flyabilityColor(windCoefVal), color:'#000', weight:1};
                                                } });
        cellsLayer.addTo(map);
    }
}

// get current git comit
$.ajax({
	type:     "GET",
	url:      "data/commit.txt",
	dataType: "text",
	success: function(commit)   {
									$("div#version").html('<a target="_blank" href="https://github.com/plebsapps/buch-paraglidable/tree/'+ commit +'">commit '+ commit.substring(0,8) +"</a>");
								}
});
