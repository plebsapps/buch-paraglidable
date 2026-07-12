    function switchNavigationBar(id)
    {
        if ($("#"+id).css('visibility') == "hidden")
        {
            $(".navigationBar").css('visibility', 'hidden');
            $("#"+id).css('visibility', 'visible');
            return true;
        }
        else
        {
            return false;
        }
    }

    function hideShowLegend(show, showFlights=false, disabled=false)
    {
        if (show)
        {
            $("#legend").css("visibility", "visible");

            if (showFlights)
                $("#legendFlights").css("display", "");
            else
                $("#legendFlights").css("display", "none");

            if (disabled)
            {
                hideLegendValues();
                hideKeywords();
            }
        }
        else
        {
            $("#legend").css("visibility", "hidden");
            hideLegendValues();
            hideKeywords();
        }
    }

    function applyShowHideMapColors(show)
    {
        if (show)
        {
            $(".basetiles").css("-webkit-filter", "grayscale(100%)");
            $(".basetiles").css("filter", "grayscale(100%)");

            // my tiles
            $(".mytiles-main").css("visibility", "visible");
        }
        else
        {
            $(".basetiles").css("-webkit-filter", "grayscale(0%)");
            $(".basetiles").css("filter", "grayscale(0%)");

            // my tiles
            $(".mytiles-main").css("visibility", "hidden");
        }
    }

    function applyShowHideSpots(show)
    {
        if (g_spotsLayer != null)
        {
            if (!show)
            {
                if (map.hasLayer(g_spotsLayer))
                    map.removeLayer(g_spotsLayer);
            }
            else
            {
                if (!map.hasLayer(g_spotsLayer))
                    g_spotsLayer.addTo(map);
            }
        }
    }

    function switchMode(strMode)
    {
        idsNavigationBar = { 'main':     'mainNavigationBar',
                             'api':      'apiNavigationBar',
                             'analysis': 'analysisNavigationBar' };

		oldMode = g_mode;
		
        if (strMode == 'main' || strMode == 'api' || strMode == 'analysis')
        {
            if ( (strMode != 'main' && switchNavigationBar(idsNavigationBar[strMode])) )
            {
                g_mode = strMode;
            }
            else
            {
                switchNavigationBar(idsNavigationBar['main']);
                g_mode = 'main';
            }

            // tiles

            if (g_mode == 'api' || showHideColorsVal == 0)
            {
                applyShowHideMapColors(false);
            }
            else
            {
                applyShowHideMapColors(true);
            }

            // legend

            hideShowLegend(g_mode=='main' || g_mode=='analysis', g_mode=='analysis', g_mode=='analysis');

            // maxNativeZoom

            if (g_mode == 'analysis')
            {
                var maxAnlLevel = 6;
                paraglidableTiles.options.maxNativeZoom = L.Browser.retina ? maxAnlLevel-1 : maxAnlLevel;
                map.setZoom(L.Browser.retina ? maxAnlLevel-1 : maxAnlLevel);
            }
            else
            {
                paraglidableTiles.options.maxNativeZoom = Math.min(g_switchZoom-1, g_maxTileZoom);
            }

            // prevNextDayContainer

            if (g_mode == 'main' || g_mode == 'analysis')
            {
                $("#prevNextDayContainer").css("visibility", "visible");
                updatePrevNextButtons();
            }
            else
            {
                $("#prevNextDayContainer").css("visibility", "hidden");
            }

            // API markers

            if (g_mode != 'api')
                removeAllApiMarkers();

			if (g_mode != 'analysis')
			{
				if (g_flightsLayer != null)
				{
        			if (map.hasLayer(g_flightsLayer))
            			map.removeLayer(g_flightsLayer);
				}
			}

            // Calendar

            if (g_mode == 'analysis')
                fillAnlDatepickerIfNeeded();

            // date

            if (g_mode == 'analysis')
            {
                changeDate('2013-05-13');
            }
            else if (oldMode=='analysis')
            {
                changeDate(moment().format("YYYY-MM-DD"));
            }
        }
    }
