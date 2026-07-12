function expandSearch()
{
    if (parseInt($("#searchInput").hasClass("active")))
    {
        tryRetractSarch();
    }
    else
    {
        clearInterval(searcheWidth_interval);
        searcheWidth_interval = setInterval(tryRetractSarch, 2000);
        $("#searchInput").addClass('active');
    }
}

function tryRetractSarch()
{
    if (!$("#searchInput").is(':focus'))
    {
        $("#searchInput").removeClass('active');
        $("#searchInput").val("");
        clearInterval(searcheWidth_interval);
    }
}

$("#searchInput").focus(expandSearch);
$("#searchInput").focusout(tryRetractSarch);

var autocomplete = new kt.OsmNamesAutocomplete('searchInput', 'apps/search.php?q=', '');
autocomplete.registerCallback(function(item) {
    setPosition(item['lat'], item['lon'], true);
});

//=========================================
// 
//=========================================

function gpsLocationFound(e)
{
    setPosition(e.latlng.lat, e.latlng.lng, true);
    $("#mapControlButtonGpsIcon").removeClass('searching');
    $("#mapControlButtonGpsIcon").attr('src','imgs/icons/gps.svg');
    $("#mapControlButtonGps").removeClass('disabled');
}
function gpsLocationError(e)
{
    $("#mapControlButtonGpsIcon").removeClass('searching');
    $("#mapControlButtonGpsIcon").attr('src','imgs/icons/gps-disabled.svg');
    $("#mapControlButtonGps").addClass('disabled');
}

map.on('locationfound', gpsLocationFound)
   .on('locationerror', gpsLocationError);

function mapZoom(direction)
{
    map.setZoom(Math.max(map.getZoom() + direction, 0));
}

function mapGps()
{
    $("#mapControlButtonGpsIcon").addClass('searching');

    map.locate({ enableHighAccuracy: true,
                 watch: false,
                 setView: false  }); 
}
