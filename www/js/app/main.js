    // redirect to mobile version
    /*
    function detectMobile() { 
         if( navigator.userAgent.match(/Android/i)
         || navigator.userAgent.match(/webOS/i)
         || navigator.userAgent.match(/iPhone/i)
         || navigator.userAgent.match(/iPad/i)
         || navigator.userAgent.match(/iPod/i)
         || navigator.userAgent.match(/BlackBerry/i)
         || navigator.userAgent.match(/Windows Phone/i)
         )
         {
            return true;
         }
         else
         {
            return false;
         }
    }

    if (detectMobile()) {
        var mobileVersion = getCookie("mobileVersion");
        if (mobileVersion == "1")
            window.location.href = "mobile.html";
    }
    */
    //----------------------------------------

//Sentry.init({dsn: 'https://db964094b5ca4939b671097b3aae1829@sentry.io/1322018'});

//=========================================
// 
//=========================================

var searcheWidth_interval = null;

var viewCenter = [47,8.5];
var viewZoom   = 6;

var showHideColorsVal = 1;
var showHideSpotsVal  = 1;

var g_mode = 'main';

var g_arrColorBlindAngles = [0, 110, 280];
var colorBlindValue = 0;

//=========================================
// inputs
//=========================================

var inputLat  = getQueryVariable("lat");
var inputLon  = getQueryVariable("lon");
var inputZoom = getQueryVariable("zoom");
var inputDay  = getQueryVariable("day");

if (!inputLat || !inputLon || !inputZoom)
{
    var strView = getCookie("view");

    if (strView != "") {
        arView = strView.split(",");
        viewCenter = [parseFloat(arView[0]), parseFloat(arView[1])];
        viewZoom   = parseInt(arView[2]);
    }
}
else
{
    viewCenter = [parseFloat(inputLat), parseFloat(inputLon)];
    viewZoom   = parseInt(inputZoom);
}

//=========================================
// map creation
//=========================================

var map = L.map('map', {attributionControl: false, zoomControl: false, minZoom: 4}).setView(viewCenter, viewZoom);
var vignettesMaps = [];

var g_spotsLayer = null;
var g_flightsLayer = null;

//=========================================
// map events/actions
//=========================================

function setPosition(lat, lon, drawTarget, zoomIn=true)
{
    var zoom = zoomIn ? Math.max(map.getZoom(), 7) : map.getZoom();
    map.setView([lat, lon], zoom);

    if (drawTarget) {
        moveMarker(lat, lon, map);
    }
}

var g_apiMarkers = {};
var g_apiMarkerId = 0;



function removeApiMarker(apiMarkerId)
{
    if (g_apiMarkers.hasOwnProperty(apiMarkerId))
    {
        map.removeLayer(g_apiMarkers[apiMarkerId]['marker']);
        delete g_apiMarkers[apiMarkerId];
    }
}

function removeAllApiMarkers()
{
    for (var apiMarkerId in g_apiMarkers) {
        removeApiMarker(apiMarkerId);
    }
}

function generateKey()
{
    var nb = Object.keys(g_apiMarkers).length;
    if (nb == 0)
        return;

    $("#apiEmailSpinner").css("display", "inline-block");
    $("#apiEmailOK"     ).css("display", "none");
    $("#apiEmailErr"    ).css("display", "none");

    var urlParams = "?email="+encodeURI($('#apiEmail').val());
    var i = 0;
    for (var key in g_apiMarkers)
    {
        if (g_apiMarkers.hasOwnProperty(key))
        {
            var latlon = g_apiMarkers[key]['marker'].getLatLng();
            var name   = g_apiMarkers[key]['name'];
            var spotId = g_apiMarkers[key]['spotId'];
            var stri   = i.toString();

            urlParams += "&lat_"+    stri +"="+ latlon.lat.toFixed(5).toString() +
                         "&lon_"+    stri +"="+ latlon.lng.toFixed(5).toString() +
                         "&spotId_"+ stri +"="+ spotId.toString() +
                         "&name_"+   stri +"="+ encodeURI(name);
            i++;
        }
    }

    $.ajax({
        type:     "GET",
        url:      "/apps/api/generateApiKey.php"+ urlParams,
        dataType: "text",
        success: function(data)    {
                                        $("#apiEmailSpinner").css("display", "none");
                                        $("#apiEmailOK"     ).css("display", "inline-block");
                                        $("#apiEmailErr"    ).css("display", "none");
                                   },
        error:   function (result) {
                                        $("#apiEmailSpinner").css("display", "none");
                                        $("#apiEmailOK"     ).css("display", "none");
                                        $("#apiEmailErr"    ).css("display", "inline-block");
                                   }
    });

}

function apiSpotNameChange(id)
{
    g_apiMarkers[id]['name'] = $("#apiSpotName-"+ id).val();
}

function clearUntitled(id)
{
    if ($("#apiSpotName-"+ id).val() == "untitled")
        $("#apiSpotName-"+ id).val("");
}

function apiMarkerPopupContent(id, spotId=-1, value="")
{
    if (id in g_apiMarkers) {
        value  = g_apiMarkers[id]['name'];
        spotId = g_apiMarkers[id]['spotId'];
    }
    var nameId = "apiSpotName-"+ id.toString();
    var customPopup = '<div style="margin:20px 20px 13px 5px">';
    if (spotId >= 0)
        customPopup += '<span style="font-size:smaller"><span style="font-weight:bold">Startplatz:</span> Die Startplatz-Wahrscheinlichkeit<br>wird den Vorhersagen hinzugefügt<br><br></span>';
    customPopup += 'Name: <input id="'+ nameId +'" class="apiMarkerNameInputText" onclick="clearUntitled('+ id.toString() +')" onkeyup="apiSpotNameChange('+id.toString()+')" onchange="apiSpotNameChange('+ id.toString() +')" type="text" value="'+ value +'"><br/><br/>\
                        <span style="cursor:pointer;position:absolute;right:4px;bottom:4px;" onclick="removeApiMarker('+ id.toString() +')"><img src="imgs/icons/remove.svg" width="16"></span></div>';
    return customPopup;
}

function onApiMarkerClick(e)
{
    var popup = e.target.getPopup();
    popup.setContent( apiMarkerPopupContent(this.options.myCustomId) );
}

function addApiMarker(lat, lon, spotId=-1, name="")
{
    var nb = Object.keys(g_apiMarkers).length;
    if (nb >= 10)
        return;

    // create popup contents
    var customPopup = apiMarkerPopupContent(g_apiMarkerId, spotId, name);
    
    // specify popup options 
    var customOptions =
        {
        'maxWidth': '500',
        'className' : 'apiMarker'
        }
    
    // create marker object, pass custom icon as option, pass content and options to popup, add to map
    var newMarker = L.marker([lat, lon], {myCustomId: g_apiMarkerId}).bindPopup(customPopup,customOptions).addTo(map)

    newMarker.on('click', onApiMarkerClick);

    g_apiMarkers[g_apiMarkerId] = {'marker': newMarker, 'name': name, 'spotId': spotId};

    // open marker popup
    newMarker.openPopup();

    g_apiMarkerId++;
}

function mapClick(lat, lon)
{
    hideAllModals();

    if (g_mode == 'main')
    {
        setPosition(lat, lon, false);
    }
    else if (g_mode == 'api')
    {
        addApiMarker(lat, lon);
    }
    else if (g_mode == 'analysis')
    {
        setPosition(lat, lon, false, false);
    }
}

map.on('click', function(e) {mapClick(e.latlng.lat, e.latlng.lng);});

/*
map.on('contextmenu', function(e) {
    alert(e.latlng);
});
*/
//=========================================
// Legend
//=========================================

function setLegendCursor(legendValId, legendValTxtId, val)
{
    $('#'+legendValTxtId).html(Math.round(val*100.0) +"%");
    $('#'+legendValId).css   ('margin-left', val*(parseInt($('.legendImg').css('width'), 10)-1)-1);

    if (val <= 0.5) {
        $('#'+legendValTxtId).css('text-align',   'left');
        $('#'+legendValTxtId).css('margin-left', val*(parseInt($('.legendImg').css('width'), 10)-1));
    } else {
        $('#'+legendValTxtId).css('text-align',   'right');
        $('#'+legendValTxtId).css('margin-left', val*(parseInt($('.legendImg').css('width'), 10)-1) - parseInt($('.legendValTxt').css('width'), 10) - parseInt($('.legendValTxt').css('padding-left'), 10) - parseInt($('.legendValTxt').css('padding-right'), 10));
    }
}

function warningLegendVal(predictionVal)
{
    if (predictionVal != null) {
        return 1.0 - 3.0/2.0*predictionVal;
    } else {
        return -1.0;
    }
}

function displayKeyWords(val_flyability,
                         val_wind, val_water,
                         val_windAngle)
{
    // keywords
    keywords = [];
    keywords.push(['Wind',         warningLegendVal(val_wind),  '#A00000']);
    keywords.push(['Feuchtigkeit', warningLegendVal(val_water), '#A00000']);

    //keywords.push(['Plaf élevé (WIP fake)', Math.max(0.0, Math.sin(1.5*lon)), '#00A000']);

    keywords.sort(function(x, y) {
        return y[1] - x[1];
    });

    if ($('#legendSectionKeywords').html() == '')
    {
        keywordsHtml = '';
        for (kw=0; kw<keywords.length; kw++)
        {
            keywordsHtml += '<div class="legendLineKeyWords" id="keywordLine'+ kw +'"> \
                                <div class="legendLineNameKeywords" id="keywordLineW'+ kw +'"></div> \
                                <div class="legendLineValueKeywords" id="keywordLineV'+ kw +'">\
                                    <div class="keywordVal" id="keyword'+ kw +'Val"></div>\
                                </div> \
                             </div>'
        }
        $('#legendSectionKeywords').html(keywordsHtml);
    }


    nbVisibleKeywords = 0;
    for (kw=0; kw<keywords.length; kw++)
    {
        if (keywords[kw][1] > 0.0) {
            $('#keywordLineW'+ kw).html(keywords[kw][0]);
            $('#keyword'+ kw +'Val').css("width", Math.round(keywords[kw][1]*150));
            $('#keyword'+ kw +'Val').css("background-color", keywords[kw][2]);
            $('#keywordLineW'+ kw).css("height", "14px");
            $('#keywordLineV'+ kw).css("height", "12px");
            $('#keywordLine' + kw).css("height", "14px");
            $('#keywordLine' + kw).css("padding-bottom", "2px");
            $('#keywordLineV'+ kw).css("visibility", "visible");

            if(keywords[kw][0] == 'Wind')
            {
                var angleDeg = 180 - val_windAngle/Math.PI*180;
                $('#keywordLineW'+ kw).append(' <img src="imgs/icons/wind_arrow.svg" style="width:9px;height:9px;transform:rotate('+ angleDeg.toString() +'deg)">');
            }
            nbVisibleKeywords++;
        }
        else
        {
            $('#keywordLineW'+ kw).css("height", "0px");
            $('#keywordLineV'+ kw).css("height", "0px");
            $('#keywordLine' + kw).css("height", "0px");
            $('#keywordLine' + kw).css("padding-bottom", "0px");
            $('#keywordLineV'+ kw).css("visibility", "hidden");
        }
    }

    if (nbVisibleKeywords==0) {
        $('#legendSectionKeywords').removeClass('active');
        $('#legendSectionPredictions').removeClass('active');
    }
    else {
        $('#legendSectionKeywords').addClass('active');
        $('#legendSectionPredictions').addClass('active');
        applyColorBlind("keywordVal");
    }
}

function displayPredictions(arValues)
{
    if (arValues.length == 0)
        return;

    //console.log(arValues);

    val_flyability     =  arValues[0];
    val_cross          =  arValues[1];
    val_wind           =  arValues[2];
    val_water          =  arValues[3];
    val_attractiveness =  arValues[4];
    val_windAngle      = (arValues[5]*4.0 - 2.0)*Math.PI;

    showLegendValues();
    setLegendCursor('legendVal1', 'legendValTxt1', val_flyability);
    setLegendCursor('legendVal2', 'legendValTxt2', val_cross);
    if (val_attractiveness != null) {
        //setLegendCursor('legendVal3', 'legendValTxt3', val_attractiveness);
    }

    displayKeyWords(val_flyability, val_wind, val_water, val_windAngle);
}

function displayElevation(strElev) {
    $("#legendTopAlt").html(strElev +"m");
}

//=========================================
// tiles
//=========================================

function createBaseTilesLayers(className)
{
    var options = {
                    attribution: '',
                    subdomains: 'abc',
                    minZoom: 0,
                    maxNativeZoom: 17,
                    ext: 'png',
                    detectRetina: true,
                    errorTileUrl: '/imgs/tileNotFound.png',
                    className: className
                  };

    // Etappe F: eigene Identität — topografische Basiskarte statt des
    // Original-Stils; Attribution steht dauerhaft im Footer (#derivativeNotice)
    var baseLayer = L.tileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', options);

    return baseLayer;
}

function tilesUrl(date, transpa)
{
    if (g_mode == 'analysis')
    {
        tilesdir = 'data/tiles_anl/'+date.substring(0,4);
        transpa = true;
    }
    else
    {
        tilesdir = 'data/tiles';
    }

    if (transpa)
        return tilesdir +'/'+ date +'/256/{z}/{x}/{y}_transpa.{ext}';
    else
        return tilesdir +'/'+ date +'/256/{z}/{x}/{y}.{ext}';
}

var paraglidableTiles = null;

//=========================================
// change date
//=========================================

var g_nbDays = 10;
var g_modePast = false;
var g_strDate = "";
const g_switchZoom = L.Browser.retina ? 9 : 10;
const g_maxTileZoom = 8; // höchste erzeugte Kachel-Zoomstufe (forecast.py max_tiles_zoom im Docker-Zweig)

//========================================================
// actions
//========================================================

var g_lastZoom = {};

function createMyTilesLayers(date, className, zoom, isRetina)
{
    var layer = L.tileLayer(tilesUrl(date, zoom >= g_switchZoom), {
        attribution: '',
        minNativeZoom: isRetina ? 4 : 5,
        maxNativeZoom: Math.min(g_switchZoom-1, g_maxTileZoom),
        minZoom: 1,
        //maxZoom: 12,
        ext: 'png',
        detectRetina: true,
        className: className,
        bounds: g_latLngBoundingBox,
        errorTileUrl: '/imgs/tileNotFound.png' });

    return layer;
}

function updateTiles(theMap, myTiles, baseTiles, zoomIdx, date)
{
    if (date=="") // the case for the main map only
        date = g_strDate;

    var zoom = theMap.getZoom();

    if (zoom >= g_switchZoom && (!(zoomIdx in g_lastZoom) || !(g_lastZoom[zoomIdx] >= g_switchZoom)))
    {
        myTiles.setUrl(tilesUrl(date, true));
    }
    else if (zoom < g_switchZoom && (!(zoomIdx in g_lastZoom) || !(g_lastZoom[zoomIdx] < g_switchZoom)))
    {
        myTiles.setUrl(tilesUrl(date, false));
    }

    g_lastZoom[zoomIdx] = zoom;
}

function addTilesSwitcher(map, myTiles, baseTiles, zoomIdx, date)
{
    map.on('zoomend', 
        (function(theMap, myTiles, baseTiles, zoomIdx, date) { return function(e) {updateTiles(theMap, myTiles, baseTiles, zoomIdx, date);} })(map, myTiles, baseTiles, zoomIdx, date)
    );
}

function updateCurrentDateTitle()
{
    if (!g_strDate)
        return;

    var showYear = (g_mode == 'analysis');
    var showDow  = (g_mode != 'analysis');
    $('#currentDate').html(displayDate(moment(g_strDate, "YYYY-MM-DD"), true, true, showYear, showDow));
}




//========================================================================================
// spots
//========================================================================================

function myOpenPopup(feature, layer)
{
    //var color = flyabilityColor(feature.properties.flyability);
    //$('html > head').append($('<style>.leaflet-popup-content-wrapper, .leaflet-popup-tip { background:'+ color +'; }</style>'));

    layer.openPopup(); 
}

function loadSpots(date, decodedJson)
{
	if (g_strDate != date)
	{
		// json recieved already outdated (the date has changed since trigger)
		return;
	}

    if (g_spotsLayer != null) {
        if (map.hasLayer(g_spotsLayer))
            map.removeLayer(g_spotsLayer);
    }

    g_spotsLayer = L.geoJson(decodedJson, {
                style : function(feature) {
                    return feature.properties && feature.properties.style;
                },

                pointToLayer : function(feature, latlng) {
                    return L.circleMarker(latlng, {
                        radius : 4.4, // + Math.sqrt(feature.properties.nbFlights/800.0)
                        fillColor : flyabilityColor_with_colorblind(feature.properties.flyability),
                        color : "#000",
                        weight : 1,
                        opacity : 1,
                        fillOpacity : 1.0
                    });
                },

                onEachFeature: function(feature, layer) {
                    if (feature.properties && feature.properties.name) {
                        layer.bindPopup(popupContent(feature.properties.name, 
                                                     feature.properties.flyability,
                                                     feature.properties.id,
                                                     feature.properties.nbFlights), {closeButton: false, offset: L.point(0, -10)});
                        layer.on('mouseover', function() { myOpenPopup(feature, layer);});
                        layer.on('mouseout', function() { layer.closePopup(); });
                        layer.on('click', function() { if (g_mode == 'api') {
                                                            addApiMarker(feature['geometry']['coordinates'][1],
                                                                         feature['geometry']['coordinates'][0],
                                                                         feature.properties.id,
                                                                         feature.properties.name.split(/,,,/g)[0]);
                                                        }
                                                      }
                                );
                    }
                }
            }
                                );
    
    if (showHideSpotsVal==1)
    {
        if (!map.hasLayer(g_spotsLayer))
            g_spotsLayer.addTo(map);
    }
}



function loadFlights(decodedJson)
{
	flights = decodedJson['flights'];

	if (g_flightsLayer != null) {
        if (map.hasLayer(g_flightsLayer))
            map.removeLayer(g_flightsLayer);
    }

	var area = L.rectangle([[42.5, 3.5], [49.5, 18.5]], {color: "#000000", weight: 1., fill: false, opacity:0.5});
	var flightsLayers = [area];

	for (f=0; f<flights.length; f++)
	{
		var circle = L.circleMarker([flights[f][0], flights[f][1]], {
			color: '#000000',
			fillColor: '#5050FF',
			fillOpacity: 0.5,
			opacity: 0.5,
			radius: (2.5 + flights[f][2]/40.),
			weight: 0.5
		});

		flightsLayers.push(circle);
	}

	g_flightsLayer = L.layerGroup(flightsLayers);

	if (!map.hasLayer(g_flightsLayer))
            g_flightsLayer.addTo(map);
}



//========================================================================================
//
//========================================================================================
function callBackSpots(date) {
  return function(data) {
    loadSpots(date, data);
  }
}

function downloadSpotsPredictions()
{
    if (g_spotsLayer != null) {
        if (map.hasLayer(g_spotsLayer))
            map.removeLayer(g_spotsLayer);
    }
	if (g_mode != 'analysis')
	{
		$.getJSON("data/tiles/"+ g_strDate +"/spots.json", callBackSpots(g_strDate));
	}
}

function downloadFlights()
{
	if (g_flightsLayer != null) {
        if (map.hasLayer(g_flightsLayer))
            map.removeLayer(g_flightsLayer);
    }
	if (g_mode == 'analysis')
	{
		$.getJSON("data/flights_anl/"+ g_strDate.substring(0,4) +"/"+ g_strDate +"/flights.json", function(data){loadFlights(data)});
	}
}

function changeDate(strDate)
{
    g_strDate = strDate;
    updateUrl();

    document.getElementById('loaderContainer').style.display = "block";

    changePastModeFromStrDate(strDate);
    updateSelectedVignetteDay();
    updateCurrentDateTitle();
    updateLastUpdateDate();
    updatePrevNextButtons();
    downloadSpotsPredictions();
    downloadFlights();

    //
    if (paraglidableTiles == null)
    {
        var baseTilesLayer = createBaseTilesLayers("basetiles");
        baseTilesLayer.addTo(map);

        paraglidableTiles = createMyTilesLayers(strDate, 'mytiles-main colorMap', map.getZoom(), L.Browser.retina);
        paraglidableTiles.on('load', function (event) {
            document.getElementById('loaderContainer').style.display = "none";
        });
        paraglidableTiles.addTo(map);

        updateTiles(map, paraglidableTiles, baseTilesLayer, 0, "");
        addTilesSwitcher(map, paraglidableTiles, baseTilesLayer, 0, "");
    }
    else
    {
        paraglidableTiles.setUrl(tilesUrl(strDate, map.getZoom() >= g_switchZoom));
    }
}

function moveDay(deltaDay)
{
    var newStrDate = moment(g_strDate, "YYYY-MM-DD").add(deltaDay, 'days').format("YYYY-MM-DD");

    if (isSelectableDate(newStrDate))
        changeDate(newStrDate);
}

function changePastMode(mode)
{
    if (g_modePast != mode)
    {
        g_modePast = mode;
        updateVignettes();
        updatePrevNextButtons();
    }
}

function moveForward(forward)
{
    if (g_mode == 'main')
    {
        var mode = !forward;
        if (g_modePast != mode)
        {
            g_modePast = mode;
            updateVignettes();
            updatePrevNextButtons();
        }
    }
    else if (g_mode == 'analysis')
    {
        moveDay(forward ? 7 : -7);
    }
}


function changePastModeFromStrDate(strDate)
{
    var diffDays = getStrDateDiffDays(strDate);

    if (diffDays < 0 && !g_modePast) {
        changePastMode(true);
    }
    else if (diffDays >= 0 && g_modePast) {
        changePastMode(false);
    }
}

//========================================================
// update display at loading or after action
//========================================================

function updatePrevNextButtons()
{
    if (g_mode=='main')
    {
        if (g_modePast) {
            $('#mapControlButtonForward').removeClass('disabled');
            $('#mapControlButtonBackward').addClass('disabled');
        } else {
            $('#mapControlButtonForward').addClass('disabled');
            $('#mapControlButtonBackward').removeClass('disabled');
        }


        if (isSelectableDate(getStrDatePrevDay(g_strDate))) {
            $('#mapControlButtonPrev').removeClass('disabled');
        } else {
            $('#mapControlButtonPrev').addClass('disabled');
        }
        if (isSelectableDate(getStrDateNextDay(g_strDate))) {
            $('#mapControlButtonNext').removeClass('disabled');
        } else {
            $('#mapControlButtonNext').addClass('disabled');
        }
    }
    else
    {
        $('#mapControlButtonForward').removeClass('disabled');
        $('#mapControlButtonBackward').removeClass('disabled');
        $('#mapControlButtonPrev').removeClass('disabled');
        $('#mapControlButtonNext').removeClass('disabled');
    }
}

function updateSelectedVignetteDay()
{
    if (g_mode == 'main')
    {
        const firstD = (g_modePast ? -g_nbDays : 0       );
        const lastD  = (g_modePast ?         0 : g_nbDays) - 1;

        for (d=firstD; d<=lastD; d++)
        {
            var strDate2 = moment().add(d, 'days').format("YYYY-MM-DD");

            if (strDate2 != g_strDate) {
                $('#newDayTxt-'    + strDate2).removeClass('active');
                $('#newDay-'    + strDate2).removeClass('active');
            } else {
                $('#newDayTxt-'    + strDate2).addClass('active');
                $('#newDay-'    + strDate2).addClass('active');
            }
        }
    }
    else if (g_mode == 'analysis')
    {
        $('.datepicker-day.selected').removeClass('selected');
        $('#datepicker_'+g_strDate).addClass('selected');
    }
}

function updateLastUpdateDate()
{
	if (g_mode != 'main')
		return;
	
    const strDate = g_strDate;

    var client = new XMLHttpRequest();
    client.open("GET", "data/tiles/"+ strDate +"/progress.txt", true);
    client.send();

    client.onreadystatechange = function() {
            if(this.readyState == this.HEADERS_RECEIVED) {
                var lastModified = this.getResponseHeader("Last-Modified");
                if (lastModified != null)
                {
                    if (moment(lastModified).format('YYYY-MM-DD') == moment().format('YYYY-MM-DD'))
                        $('#lastUpdateTime').html('Heute um '+moment(lastModified).format('HH:mm'));
                    else
                        $('#lastUpdateTime').html(moment(lastModified).format('YYYY-MM-DD HH:mm'));
                }
                else
                {
                    $('#lastUpdateTime').html("");
                }
            }
        }
}

function showLegendValues()
{
    $(".legendVal").css(   "visibility", "visible");
    $(".legendValTxt").css("visibility", "visible");
}

function hideLegendValues()
{
    $(".legendVal").css   ("visibility", "hidden");
    $(".legendValTxt").css("visibility", "hidden");
}

function hideKeywords()
{
    //$(".legendLineValueKeywords").css("visibility", "hidden");
    displayKeyWords(0.0, 1.0, 1.0, 0.0);
}


//============================================================================================
// 
//============================================================================================



const latlngToTilePixel = (latlng, crs, zoom, tileSize, pixelOrigin) => {
    const layerPoint = crs.latLngToPoint(latlng, zoom).floor();
    const tile = new L.Point(Math.floor(layerPoint.x/tileSize.x), Math.floor(layerPoint.y/tileSize.y));
    const tileCorner = new L.Point(tile.x * tileSize.x - pixelOrigin.x, tile.y * tileSize.y - pixelOrigin.y);
    const tilePixel = layerPoint.subtract(pixelOrigin).subtract(tileCorner);

    return [tile, tilePixel];
}



var lat, lng;
var rect = null;

var g_lastLatlng = null;
var g_lastTx = -1;
var g_lastTy = -1;
var g_lastX  = -1;
var g_lastY  = -1;
var g_timerRequestValues = null;

function requestValues()
{
    if (g_mode != 'main') {
        hideLegendValues();
        return;
    }

    const dataTilesZoom = 7;


    $.ajax({
        type: "GET",
        url: 'apps/api/get.php?elev=1&tx='+ g_lastTx +'&ty='+ g_lastTy +'&x='+ g_lastX +'&y='+ g_lastY +'&zoom='+ dataTilesZoom +'&date='+ g_strDate,
        dataType: "text",
        success: function(data)    {
                                        //data = "0.75,0.25,0.2941,0.5333,0.7804,0.4078;833";

                                        if (g_lastLatlng != null) {
                                            $("#legendTopLat").html(g_lastLatlng.lat.toFixed(4) +"&deg;");
                                            $("#legendTopLon").html(g_lastLatlng.lng.toFixed(4) +"&deg;");
                                        }

                                        if (data.length > 0)
                                        {
                                            const predictions_elevation = data.split(';');

                                            // predictions
                                            const strVals = predictions_elevation[0].split(',');
                                            var arValues = [];
                                            for (v=0; v<strVals.length; v++) {
                                                arValues.push(parseFloat(strVals[v]));
                                            }
                                            displayPredictions(arValues);

                                            // elevation
                                            if (predictions_elevation.length > 1) {
                                                const strElev = predictions_elevation[1];
                                                displayElevation(strElev);
                                            }
                                        }
                                        else
                                        {
                                            hideLegendValues();
                                        }
                                   },
        error:   function (result) { }
    });
}

map.addEventListener('mousemove', function(ev) {

    const dataTilesZoom = 7;
    const tileSize = new L.Point(256, 256);
    const tileCoords = latlngToTilePixel(ev.latlng, map.options.crs, dataTilesZoom, tileSize, map.getPixelOrigin());

    const tx = tileCoords[0].x;
    const ty = tileCoords[0].y;
    const x  = tileCoords[1].x;
    const y  = tileCoords[1].y;

    if (tx != g_lastTx || ty != g_lastTy || x != g_lastX || y != g_lastY)
    {
        g_lastTx = tx;
        g_lastTy = ty;
        g_lastX  = x;
        g_lastY  = y;
        g_lastLatlng = ev.latlng;

        if (g_timerRequestValues != null)
            window.clearTimeout(g_timerRequestValues);

        g_timerRequestValues = setTimeout(function(){ requestValues(); }, 50); // prevent sending too much requests
    }
});

function updateUrl()
{
    newCenter = map.getCenter();
    newZoom   = map.getZoom();
    strDate   = g_strDate;

    window.history.replaceState('page2', 'Paraglidable', '/?lat='+ newCenter.lat.toFixed(3) +"&lon="+ newCenter.lng.toFixed(3) +"&zoom="+ newZoom);// +"&day="+ strDate);
}

function updateVignettesView()
{
    newCenter = map.getCenter();
    newZoom   = map.getZoom();

    for (v=0; v<vignettesMaps.length; v++) {
        vignettesMaps[v].setView(newCenter, Math.max(0, newZoom-3));
    }
}

function onUpdateView_()
{
    hideAllModals();
    newCenter = map.getCenter();
    newZoom   = map.getZoom();

    updateVignettesView();
    updateUrl();
    setCookie("view", newCenter.lat +","+ newCenter.lng +","+ newZoom, 30*6);
}

map.addEventListener('moveend', onUpdateView_);


$.getJSON("imgs/oceans.json", function(data){addOceans(data, [map])});


function addOceans(decodedJson, arMaps)
{
    for (m=0; m<arMaps.length; m++)
    {
        // can't share the same layer with all maps (https://stackoverflow.com/questions/18235075/leaflet-add-same-layer-to-two-different-maps)
        var oceansLayer = L.geoJson(decodedJson, {
                                                style: function(feature) {
                                                            return {"fillOpacity": 1.0, fillColor: '#0071cb', color:'#000', weight:1};
                                                       }
                                                 }
                                    );
        oceansLayer.addTo(arMaps[m]);
    }
}

function updateVignettes()
{
    var htmlContent  = '';
    
    const firstD = (g_modePast ? -g_nbDays : 0       );
    const lastD  = (g_modePast ?         0 : g_nbDays) - 1;

    arWeeks = [];
    for (d=firstD; d<=lastD; d++)
    {
        var momentDate = moment().add(d, 'days');
        var dow = momentDate.isoWeekday();

        if (dow==1 || (d == firstD))
            arWeeks.push([]);

        arWeeks[arWeeks.length-1].push(momentDate);
    }

    //==========================================================
    // fill #vignettesContainer
    //==========================================================

    for  (w=0; w<arWeeks.length; w++)
    {
        if (w > 0) {
            htmlContent  += '<div class="vignettesSpacerWeek"></div>';
        }

        htmlContent  += '<div id="newWeekContainer" style="flex:'+ arWeeks[w].length +'">';

        for (d=0; d<arWeeks[w].length; d++)
        {
            var momentDate = arWeeks[w][d];
            var strDate = momentDate.format("YYYY-MM-DD");

            //=================================================

            var firstLastClass = ''
            if (d==0) firstLastClass += ' first';
            if (d==arWeeks[w].length-1) firstLastClass += ' last';


            htmlContent  += '<div id="newDay-'+ strDate +'" class="newDay'+ firstLastClass +'" onclick="hideAllModals();changeDate(\''+ strDate +'\');"> \
                    <div class=\"newDayMap'+ firstLastClass +'\"><div class="newDayLeafletMap" id="map-'+ strDate +'"></div></div>\
                    <div id="newDayTxt-'+ strDate +'" class=\"newDayTxt\">'+ displayDate(momentDate) +'</div>\
            </div>';
        }

        htmlContent  += '</div>';
    }


    $('#vignettesContainer').html(htmlContent);

    //==========================================================
    // Hide days with no tiles
    //==========================================================

    for (d=firstD; d<=lastD; d++)
    {
        var strDate = moment().add(d, 'days').format("YYYY-MM-DD");

        var client = new XMLHttpRequest();
        client.open("GET", "data/tiles/"+ strDate +"/progress.txt", true);
        client.send();

        client.onreadystatechange = (function(strDate) {
            return function()
            {
                if(this.readyState == this.HEADERS_RECEIVED)
                {
                    if (this.getResponseHeader("Last-Modified") == null)
                    {
                        $("#map-"+ strDate).addClass("notAvailable");
                        $("#map-"+ strDate).html("<div style=\"padding-top:10px\">Noch<br>nicht<br>verfügbar</div>");
                    }
                }
            }
        })(strDate);
    }

    //==========================================================
    // Create maps
    //==========================================================

    vignettesMaps = [];

    for  (w=0; w<arWeeks.length; w++)
    {
        for (d=0; d<arWeeks[w].length; d++)
        {
            var momentDate = arWeeks[w][d];
            var strDate = momentDate.format("YYYY-MM-DD");

            vMap = L.map('map-'+strDate, {attributionControl: false, zoomControl: false, keyboard: false});

            vMap.dragging.disable();
            vMap.touchZoom.disable();
            vMap.doubleClickZoom.disable();
            vMap.scrollWheelZoom.disable();

            const baseTiles = createBaseTilesLayers("basetiles-vignette");
            const myTiles   = createMyTilesLayers(strDate, 'colorMap', map.getZoom()-3, L.Browser.retina);
            baseTiles.addTo(vMap);
            myTiles.addTo(vMap);


            updateTiles     (vMap, myTiles, baseTiles, vignettesMaps.length+1, strDate);
            addTilesSwitcher(vMap, myTiles, baseTiles, vignettesMaps.length+1, strDate);

            vignettesMaps.push(vMap);

        }
    }

    updateVignettesView();
    updateSelectedVignetteDay();
    updateCurrentDateTitle();

    $.getJSON("imgs/oceans.json", function(data){addOceans(data, vignettesMaps)});
}

updatePrevNextButtons();
updateVignettes();

//=========================================
// Select day
//=========================================

function getStrDatePrevDay(strDate)
{
    return moment(strDate, "YYYY-MM-DD").add(-1, 'days').format("YYYY-MM-DD");
}

function getStrDateNextDay(strDate)
{
    return moment(strDate, "YYYY-MM-DD").add(+1, 'days').format("YYYY-MM-DD");
}

function isSelectableDate(strDate)
{
    if (!strDate || !moment(strDate, "YYYY-MM-DD").isValid())
        return false;
    
    if (g_mode == 'analysis')
        return true;

    var diffDays = getStrDateDiffDays(strDate);
    return (diffDays > -g_nbDays-1 && diffDays < g_nbDays);
}

//=========================================
// Modals functions
//=========================================

function hideAllModals()
{
    $(".newModal").css("display", "none");
}

document.addEventListener('keyup', function(e) {
    if (e.keyCode == 27 && !$("#searchInput").is(":focus")) {
        hideAllModals();
        switchMode('main');
    }
});

function switchVisibility(id) {
    if ($('#'+id).css('display') == 'none') {
        hideAllModals();
        $('#'+id).css('display', 'inline');
    } else {
        $('#'+id).css('display', 'none');
    }
}

//=========================================
// Autocomplete
//=========================================
