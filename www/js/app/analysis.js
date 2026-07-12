function valToColorLst(val, vals, colors)
{
    if (val < vals[0])
        val = vals[0];
    if (val > vals[vals.length-1])
        val = vals[vals.length-1];

    for (v=0; v<vals.length-1; v++)
    {
        if (val <= vals[v+1])
        {
            var colorR = [parseInt(colors[v].substring(0,2), 16), parseInt(colors[v+1].substring(0,2), 16)];
            var colorG = [parseInt(colors[v].substring(2,4), 16), parseInt(colors[v+1].substring(2,4), 16)];
            var colorB = [parseInt(colors[v].substring(4,6), 16), parseInt(colors[v+1].substring(4,6), 16)];

            var interp = (val - vals[v])/(vals[v+1] - vals[v]);
            var colorRint = interp*(colorR[1]-colorR[0]) + colorR[0];
            var colorGint = interp*(colorG[1]-colorG[0]) + colorG[0];
            var colorBint = interp*(colorB[1]-colorB[0]) + colorB[0];

            return [ Math.floor(0.5+colorRint),
                     Math.floor(0.5+colorGint),
                     Math.floor(0.5+colorBint) ];
        }
    }

    return [0,0,0];
}

function flyabilityColor(val)
{
    color = valToColorLst(val, [0.0,0.5,1.0], ["A00000", "A07000", "00A000"]);
    return "#"+ ("00" + color[0].toString(16)).substr(-2) +
                ("00" + color[1].toString(16)).substr(-2) +
                ("00" + color[2].toString(16)).substr(-2);
}

function makeSvg(width, height, svg)
{
    let encapsulatedSvg = '<svg width="'+ width +'" height="'+ height +'" xmlns="http://www.w3.org/2000/svg"><metadata id="metadata1">image/svg+xml</metadata>'+ svg +'</svg>';
    let svgUrl = encodeURI("data:image/svg+xml," + encapsulatedSvg).replace('#','%23');
    return svgUrl;
}

function computeHistogram(vals, nbBins, minVal, maxVal)
{
    var histo = Array(nbBins);
    var maxNb = 0;
    histo.fill(0);

    // fill
    for (v=0; v<vals.length; v++)
    {
        var b = 0;
        if (vals[v] <= minVal) {
            b = 0;
        }
        else if (vals[v] >= maxVal) {
            b = nbBins-1;
        }
        else {
            b = Math.floor((vals[v]-minVal)/(maxVal-minVal) * nbBins);
        }
        histo[b]++;
        if (histo[b] > maxNb)
            maxNb = histo[b];
    }

    return histo;
}

function drawAnalysisData(content)
{
    const resolution = 1.0;
    //console.log(content);
    var arContent = content.split("\n");
    var obj = JSON.parse(arContent[0]);
    var flightsContent = arContent.slice(1);

    console.log(obj);
    console.log(flightsContent);

    for (f=0; f<flightsContent.length; f++)
    {
        arFlight = flightsContent[f].split(",");
        flightsContent[f] = [parseFloat(arFlight[0]), parseFloat(arFlight[1]), parseFloat(arFlight[2])];
    }

    console.log(flightsContent);

    dataListTxt = [];
    dataListBgC = [];
    dataListBg0 = [];

    arLvl = [1000, 900, 800, 700, 600];

    console.log("obj.analysis.length", obj.analysis.length);

    for (cell=0; cell<obj.analysis.length; cell++)
    {
        const kFlyability  = 5;
        const lvlOfBgColor = 1;
        const lat = obj.analysis[cell].coords.lat;
        const lon = obj.analysis[cell].coords.lon;

        if (lon < 5.0 || lon > 18.0 || lat < 43.0 || lat > 49.0)
            continue;


        flightsContentThisCell = [];
        for (f=0; f<flightsContent.length; f++)
        {
            if (Math.abs(lat-flightsContent[f][0]) < resolution/2.0 && Math.abs(lon-flightsContent[f][1]) < resolution/2.0)
                flightsContentThisCell.push(flightsContent[f]);
        }

        var textLineHeight = 7;
        var svg  = '';

        
        // https://gist.github.com/clhenrick/6791bb9040a174cd93573f85028e97af

        //-------------------------------------------------------------------------
        // FLIGHTS
        //-------------------------------------------------------------------------

        var flightsYPos = 10;
        svg += '<text x="10" y="'+ flightsYPos +'" fill="black" font-family="Verdana" font-size="5" font-weight="bold">Flights:</text>';
        svg += '<text x="32" y="'+ flightsYPos +'" fill="black" font-family="Verdana" font-size="5">'+ flightsContentThisCell.length +'</text>';

        // circles
        for (f=0; f<flightsContentThisCell.length; f++)
        {
            dataListBg0.push(L.circle([flightsContentThisCell[f][0], flightsContentThisCell[f][1]], {
                                                                        radius: 2500.0,
                                                                        fillColor: 'white',
                                                                        fillOpacity: 1.0,
                                                                        weight: 1}));
        }

        // histogram
        var maxBinHeight = 20;
        var histoYPos = flightsYPos + 8;
        var binWidth  = 5;
        var maxPts    = 80;
        var nbBinsPts = 10;
        var histoXPos = (70 - nbBinsPts*binWidth)*0.5;

        var pts = [];
        for (f=0; f<flightsContentThisCell.length; f++)
        {
            pts.push(flightsContentThisCell[f][2]);
        }

        console.log("pts", pts);

        var histo = computeHistogram(pts, nbBinsPts, 0, maxPts);
        var maxBinValue = 15.0;
        for (b=0; b<nbBinsPts; b++)
        {
            var x = histoXPos + b*binWidth;
            var height = Math.min(maxBinValue, histo[b])/maxBinValue*maxBinHeight
            svg += '<rect x="'+ x +'" y="'+ (histoYPos+maxBinHeight-height) +'" width="'+ binWidth +'" height="'+ height +'" style="fill:rgba(0,0,0);stroke:rgb(0,0,0);stroke-width:0.5;fill-opacity:0.5" />';
        }
        // arrows
        svg += '<line x1="'+ (histoXPos) +'" y1="'+ (histoYPos+maxBinHeight) +'" x2="'+ (histoXPos+(nbBinsPts+0.5)*binWidth) +'" y2="'+ (histoYPos+maxBinHeight) +'" style="stroke:rgb(0,0,0);stroke-width:1" />';
        svg += '<line x1="'+ (histoXPos) +'" y1="'+ (histoYPos+maxBinHeight) +'" x2="'+ (histoXPos) +'" y2="'+ (histoYPos-0.5*binWidth) +'" style="stroke:rgb(0,0,0);stroke-width:1" />';

        //-------------------------------------------------------------------------
        // PREDICTIONS
        //-------------------------------------------------------------------------

        var predictionYPos = 85;
        svg += '<text x="'+ 10  +'" y="'+ (predictionYPos-5*7) +'" font-weight="bold" fill="black" font-family="Verdana" font-size="5">Flyability:</text>';

        // flyability at each level
        for (lvl=0; lvl<arLvl.length; lvl++)
        {
            var xPos = 10;
            var xPos2 = xPos+23.5;

            if (arLvl[lvl] < 1000)
                xPos += 3.19;

            svg += '<text x="'+ xPos  +'" y="'+ (predictionYPos-lvl*7) +'" fill="black" font-family="Verdana" font-size="5">'+ arLvl[lvl] +' hPa</text>';
            svg += '<text x="'+ xPos2 +'" y="'+ (predictionYPos-lvl*7) +'" fill="black" font-family="Verdana" font-size="5">: '+ Math.round(100.0*obj.analysis[cell].predictions[kFlyability+lvl]) +'%</text>';
        }

        // crossability
        svg += '<text x="'+ 10 +'" y="'+ (predictionYPos+1*7) +'" fill="black" font-family="Verdana" font-size="5" font-weight="bold">Crossability:</text>';
        svg += '<text x="'+ 46 +'" y="'+ (predictionYPos+1*7) +'" fill="black" font-family="Verdana" font-size="5">'+ Math.round(100.0*obj.analysis[cell].predictions[kFlyability+6]) +'%</text>';

        var bounds = L.latLngBounds([   [obj.analysis[cell].coords.lat-resolution/2.0, obj.analysis[cell].coords.lon-resolution/2.0],
                                        [obj.analysis[cell].coords.lat+resolution/2.0, obj.analysis[cell].coords.lon+resolution/2.0]  ]);

        //console.log(obj.analysis[cell].coords.lat, obj.analysis[cell].coords.lon);

        dataListBgC.push(L.rectangle(bounds, {  fillColor: flyabilityColor(obj.analysis[cell].predictions[kFlyability+lvlOfBgColor]),
                                                fillOpacity: 0.63,
                                                weight: 1,
                                                color: 'black'}).on('mouseover', function (e) {

            // TODO
            // TODO
            // TODO
            // TODO

            // Dessiner les infos que sur le mouseover

            $(".toto").attr("display", "none");
            console.log('mouseover');

            // TODO
            // TODO
            // TODO
            // TODO
        }));

        //dataListTxt.push(L.imageOverlay('imgs/legend/fufuPattern.png', bounds, {}));

        var svgImg = L.imageOverlay(makeSvg(70, 100, svg),  bounds, {});
        //svgImg.getElement().classList.add('toto');
        dataListTxt.push(svgImg);
    }

    // add to map
    L.layerGroup(dataListBg0).addTo(map);
    L.layerGroup(dataListBgC).addTo(map);
    L.layerGroup(dataListTxt).addTo(map);

    // put text on top
    $('.leaflet-overlay-pane img').css('z-index', 300); // rectangle z-index is 200
}

function downloadAnalysisData(date)
{
        $.ajax({
            type:     "GET",
            url:      "/apps/api/getAnalysisData.php?date="+ date,
            dataType: "text",
            success: function(data)    {
                                            drawAnalysisData(data);
                                       },
            error:   function (result) {}
        });
}

//downloadAnalysisData("2018-01-01");

//switchMode('api');
